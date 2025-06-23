import streamlit as st
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt

from core.db import (
    get_all_projects, get_project_by_id,
    get_project_files, log_ai_query, delete_project_by_id,
    save_test_case_batch, get_test_case_batches_by_project, get_test_case_batch_by_id, delete_test_case_batch
)
from core.llm_interface import generate_sql_query, generate_data_insight, generate_test_cases, validate_and_fix_sql, generate_dynamic_validation_queries, query_llm, clean_sql_response, SQL_MODEL
from core.gx_dashboard import show_rule_compliance_section  



# --- MIGRATION GAUGE ---
def show_migration_gauge(success_rate):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=success_rate,
        number={'suffix': "%", 'font': {'size': 36}},
        title={'text': "Migration Success Rate", 'font': {'size': 18}},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "green"},
            'steps': [
                {'range': [0, 50], 'color': "red"},
                {'range': [50, 80], 'color': "orange"},
                {'range': [80, 100], 'color': "lightgreen"}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': success_rate
            }
        },
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    fig.update_layout(
        height=300,
        margin=dict(t=30, b=30, l=30, r=30)
    )
    st.plotly_chart(fig, use_container_width=True)


# --- QA GENIUS TAB ---
def show_qa_interface(project_id):
    import duckdb

    # --- Get project path and mapped file ---
    project = get_project_by_id(project_id)
    files = get_project_files(project_id)
    
    # Generate project path dynamically since project_path column doesn't exist
    safe_name = f"{project['project_name'].replace(' ', '_')}_{project_id}"
    base_path = os.path.join("projects", safe_name)
    mapped_path = os.path.join(base_path, "artifacts", "mapped_output.csv")
    
    # Get file paths
    mapping_file_path = next((f['file_path'] for f in files if f['file_type'] == 'mapping'), None)
    business_rules_file_path = next((f['file_path'] for f in files if f['file_type'] == 'business_rules'), None)
    source_file_paths = [f['file_path'] for f in files if f['file_type'] == 'source']

    # --- Mapped Output Preview ---
    st.markdown("### 📊 Mapped Output Preview")
    if os.path.exists(mapped_path):
        df_mapped = pd.read_csv(mapped_path)
        st.dataframe(df_mapped, height=200, use_container_width=True)
    else:
        st.warning("⚠️ Mapped output file not found.")
        return

    # --- Saved Test Case Batches Section ---
    st.markdown("### 🗂️ Saved Test Case Batches")
    
    # Get saved batches for this project
    saved_batches = get_test_case_batches_by_project(project_id)
    
    if saved_batches:
        # Create dropdown for saved batches
        batch_options = [f"Batch {batch['batch_id']}: {batch['batch_name']} ({batch['test_case_count']} tests, {batch['sql_validation_count']} SQL)" for batch in saved_batches]
        batch_options.insert(0, "🆕 Generate New Test Cases")
        
        selected_option = st.selectbox("📋 Select Test Case Batch", batch_options, key="batch_selector")
        
        # Handle saved batch selection
        if selected_option != "🆕 Generate New Test Cases":
            # Extract batch_id from the selected option
            batch_id = int(selected_option.split("Batch ")[1].split(":")[0])
            
            # Clear any generated results when viewing a saved batch
            session_key = f"test_results_{project_id}"
            if session_key in st.session_state:
                del st.session_state[session_key]
            
            # Load and display the saved batch
            batch_data = get_test_case_batch_by_id(batch_id)
            
            if batch_data:
                batch_info = batch_data['batch_info']
                
                st.success(f"📂 Loaded: {batch_info['batch_name']}")
                st.info(f"Created: {batch_info['created_at']} | Tests: {batch_info['test_case_count']} | SQL Validations: {batch_info['sql_validation_count']}")
                
                # Delete batch option
                col_delete, col_spacer = st.columns([1, 3])
                with col_delete:
                    if st.button("🗑️ Delete Batch", key=f"delete_batch_{batch_id}"):
                        if delete_test_case_batch(batch_id):
                            st.success("Batch deleted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to delete batch")
                
                # Display the saved test cases and SQL validations
                display_test_case_results(batch_data['test_cases'], batch_data['sql_validations'], df_mapped, is_saved_batch=True)
            else:
                st.error("Could not load the selected batch")
            return
        else:
            # User selected "Generate New Test Cases" - show stored results if available
            session_key = f"test_results_{project_id}"
            if session_key in st.session_state and st.session_state[session_key]:
                stored_results = st.session_state[session_key]
                
                st.markdown("### 📋 Previously Generated Test Results")
                
                # Show when these were generated
                generated_at = stored_results.get('generated_at', 'Unknown')
                batch_name = stored_results.get('batch_name')
                
                if batch_name:
                    st.info(f"📂 Results for batch: **{batch_name}** (Generated: {generated_at})")
                else:
                    st.info(f"📝 Generated test cases (Created: {generated_at}) - Enter a batch name below to save these results")
                
                # Clear button
                if st.button("🗑️ Clear These Results", key="clear_generated_top"):
                    del st.session_state[session_key]
                    if 'sql_results' in st.session_state:
                        # Clear SQL execution results too
                        keys_to_remove = [k for k in st.session_state.sql_results.keys() if test_id in k for test_id in [tc.get('id', tc.get('test_id', '')) for tc in stored_results.get('test_cases', [])]]
                        for key in keys_to_remove:
                            del st.session_state.sql_results[key]
                    st.rerun()
                
                # Display the stored results
                display_test_case_results(
                    stored_results.get('test_cases', []), 
                    stored_results.get('sql_validations', []), 
                    df_mapped,
                    is_saved_batch=False
                )
    else:
        st.info("No saved test case batches found for this project. Generate your first batch below!")

    # --- Main QA Features ---
    st.markdown("### 🧪 QA Testing Features")
    
    # Create two columns for the main features
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔍 SQL Query Generation")
        st.info("Generate custom SQL queries to test specific data conditions")
        
        # --- User Input for Test Case ---
        question = st.text_input("Describe the data condition to test", key="sql_question")

        if st.button("🚀 Generate SQL Query", key="generate_sql"):
            if question.strip():
                with st.spinner("Generating and validating SQL query..."):
                    # --- Load full mapped dataset ---
                    if os.path.exists(mapped_path):
                        df_full = pd.read_csv(mapped_path, header=0)
                    else:
                        st.error("❌ Mapped file not found.")
                        return

                    if df_full.empty:
                        st.warning("⚠️ Mapped file is empty.")
                        return

                    # --- Schema construction for AI ---
                    max_cols = 20
                    table_schema = ", ".join([
                        f"{col} ({dtype})"
                        for col, dtype in zip(df_full.columns[:max_cols], df_full.dtypes[:max_cols])
                    ])
                    
                    # Add sample data to the schema for better context
                    sample_data_info = "\n\nSample data:\n" + df_full.head(3).to_string()

                    try:
                        # --- Generate SQL query from LLM with enhanced prompt ---
                        enhanced_prompt = f"""
You are a highly skilled SQL analyst specializing in data validation queries.

Your task is to generate a clean, syntactically valid SQL query using the DuckDB SQL dialect.
Assume the data is loaded into a single table named `data_table`. 

=== TABLE SCHEMA (column_name: type) ===
{table_schema}
=== END SCHEMA ===

=== SAMPLE DATA ===
{sample_data_info}
=== END SAMPLE DATA ===

User Question: "{question}"

CRITICAL REQUIREMENTS:
- FOCUS ONLY on the specific question asked by the user
- Use exact column names from the schema above
- Use DuckDB-compatible functions (current_date instead of CURDATE(), current_timestamp instead of NOW())
- For validation queries, use COUNT(*) to return the number of issues found
- Return 0 when validation passes, >0 when issues are found
- If the question is about birth dates, focus ONLY on date validation
- If the question is about phone numbers, focus ONLY on phone validation
- Do NOT combine multiple unrelated validations in one query
- Use realistic date patterns (YYYY-MM-DD format: ____-__-__)
- For date validation, check for NULL dates, invalid lengths, or impossible dates
- Do NOT use type casting (::), schema prefixes, or backticks

EXAMPLES for birth date validation:
- Invalid birth dates: "SELECT COUNT(*) FROM data_table WHERE date_of_birth IS NULL OR LENGTH(date_of_birth) != 10 OR date_of_birth > current_date"
- Future birth dates: "SELECT COUNT(*) FROM data_table WHERE date_of_birth > current_date"
- Missing birth dates: "SELECT COUNT(*) FROM data_table WHERE date_of_birth IS NULL"

EXAMPLES for other validations:
- Null check: "SELECT COUNT(*) FROM data_table WHERE column_name IS NULL"
- Phone validation: "SELECT COUNT(*) FROM data_table WHERE phone IS NULL OR LENGTH(phone) < 10"
- Range check: "SELECT COUNT(*) FROM data_table WHERE age < 0 OR age > 120"

Return ONLY the SQL query that directly answers the user's question, no explanations or comments.

SQL:
"""

                        raw_sql = query_llm(enhanced_prompt, model=SQL_MODEL)
                        print("RAW SQL FROM ENHANCED LLM:\n", raw_sql)

                        # Clean the SQL response
                        cleaned_sql = clean_sql_response(raw_sql)
                        print("CLEANED SQL:\n", cleaned_sql)

                        # Validate and fix the SQL using our enhanced validation system
                        corrected_sql, is_valid = validate_and_fix_sql(cleaned_sql, table_schema, df_full)
                        print(f"CORRECTED SQL (Valid: {is_valid}):\n", corrected_sql)

                        # --- Display the query with status ---
                        st.success("✅ SQL query generated successfully!")
                        
                        if corrected_sql != cleaned_sql:
                            if is_valid:
                                st.info("🔧 Query was automatically corrected for compatibility")
                            else:
                                st.warning("⚠️ Query required fallback correction")
                        
                        st.markdown("#### 💻 Generated SQL Query")
                        st.code(corrected_sql, language="sql")
                        
                        # Add execution section with immediate display
                        if st.button("▶️ Execute Query", key=f"exec_{hash(question)}_{hash(corrected_sql)}", type="primary"):
                            st.markdown("#### 📋 Query Execution Results")
                            
                            try:
                                import duckdb
                                
                                with st.spinner("Executing query..."):
                                    # Create a fresh DuckDB connection
                                    con = duckdb.connect(':memory:')
                                    con.register("data_table", df_full)
                                    
                                    # Execute the corrected query
                                    result = con.execute(corrected_sql).fetchdf()
                                    con.close()
                                
                                # Display results immediately
                                if result.empty:
                                    st.success("✅ Query executed successfully - No records returned")
                                    st.info("*This typically means the condition was not met (good for validation queries)*")
                                else:
                                    # Enhanced result interpretation
                                    st.success(f"✅ Query executed successfully - {len(result)} record(s) returned")
                                    
                                    # Smart interpretation for validation queries
                                    if len(result) == 1 and len(result.columns) == 1:
                                        # Single value result (likely a COUNT query)
                                        count_value = result.iloc[0, 0]
                                        col_name = result.columns[0].lower()
                                        
                                        if 'count' in col_name or result.columns[0].lower().endswith('_count'):
                                            if count_value == 0:
                                                st.success(f"🎯 **VALIDATION PASSED** - No issues found (count = 0)")
                                            else:
                                                st.warning(f"⚠️ **VALIDATION FAILED** - Found {count_value} issue(s)")
                                        else:
                                            st.info(f"📊 Result: {count_value}")
                                    
                                    # Always show the data table
                                    st.dataframe(result, use_container_width=True)
                                    
                                    # Show download option for larger results
                                    if len(result) > 10:
                                        csv_data = result.to_csv(index=False)
                                        st.download_button(
                                            label="📥 Download Results as CSV",
                                            data=csv_data,
                                            file_name=f"query_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                            mime="text/csv"
                                        )
                                
                                # Show the executed query for reference
                                st.markdown("---")
                                st.markdown("#### 📝 Executed Query Details")
                                st.code(corrected_sql, language='sql')
                                st.markdown(f"**Execution Time:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
                                st.markdown(f"**Total Records Processed:** {len(df_full)}")
                                
                                # Log the interaction
                                log_ai_query(project_id, question, corrected_sql)
                                
                            except Exception as e:
                                st.error(f"❌ Query execution failed: {str(e)}")
                                
                                # Enhanced debug information (as markdown section to avoid nested expanders)
                                st.markdown("---")
                                st.markdown("#### 🔍 Debug Information")
                                st.markdown("**Query that failed:**")
                                st.code(corrected_sql, language='sql')
                                st.markdown("**Available columns:**")
                                st.write(df_full.columns.tolist())
                                st.markdown("**Sample data:**")
                                st.dataframe(df_full.head(3))
                                st.markdown("**Data types:**")
                                for col, dtype in zip(df_full.columns, df_full.dtypes):
                                    st.text(f"{col}: {dtype}")
                                st.markdown("**Error Details:**")
                                st.code(str(e))
                        
                        # Alternative: Show a preview of the data that will be queried
                        with st.expander("📊 Preview Data to be Queried"):
                            st.markdown(f"**Total records available:** {len(df_full)}")
                            st.markdown("**Sample data:**")
                            st.dataframe(df_full.head(10), use_container_width=True)
                            st.markdown("**Column information:**")
                            col_info = pd.DataFrame({
                                'Column': df_full.columns,
                                'Data Type': df_full.dtypes,
                                'Non-Null Count': df_full.count(),
                                'Sample Value': [str(df_full[col].dropna().iloc[0]) if not df_full[col].dropna().empty else 'No data' for col in df_full.columns]
                            })
                            st.dataframe(col_info, use_container_width=True)

                    except Exception as e:
                        st.error(f"❌ SQL generation failed: {str(e)}")
                        st.markdown("#### 📋 Fallback Result")
                        st.dataframe(df_full.head(10))
                        st.markdown("Please try rephrasing your question or check the sample data above for guidance.")
            else:
                st.warning("Please enter a question to generate SQL.")
    
    with col2:
        st.markdown("#### 🎯 Comprehensive Test Case Generation")
        st.info("Generate professional QA test cases based on your business rules and data structure")
        
        # Batch name input
        batch_name = st.text_input("💾 Batch Name (for saving)", placeholder="e.g., Medical Data Validation V1", key="batch_name")
        
        if st.button("🎯 Create Test Cases", key="generate_test_cases"):
            with st.spinner("AI QA Engineer is analyzing your project and creating test cases..."):
                try:
                    # Gather all project information for test case generation
                    
                    # 1. Source data schema
                    source_schema = "No source files available"
                    if source_file_paths and os.path.exists(source_file_paths[0]):
                        try:
                            if source_file_paths[0].endswith('.csv'):
                                source_df = pd.read_csv(source_file_paths[0])
                            else:
                                source_df = pd.read_excel(source_file_paths[0])
                            
                            source_schema = "Source Data Columns:\n" + "\n".join([
                                f"- {col}: {dtype}" for col, dtype in zip(source_df.columns, source_df.dtypes)
                            ])
                        except Exception as e:
                            source_schema = f"Could not read source file: {e}"
                    
                    # 2. Mapping specification
                    mapping_spec = "No mapping file available"
                    if mapping_file_path and os.path.exists(mapping_file_path):
                        try:
                            if mapping_file_path.endswith('.csv'):
                                mapping_df = pd.read_csv(mapping_file_path)
                            else:
                                mapping_df = pd.read_excel(mapping_file_path)
                            
                            mapping_spec = "Mapping Specification:\n" + mapping_df.to_string(index=False)
                        except Exception as e:
                            mapping_spec = f"Could not read mapping file: {e}"
                    
                    # 3. Business rules
                    business_rules = "No business rules provided"
                    if business_rules_file_path and os.path.exists(business_rules_file_path):
                        try:
                            with open(business_rules_file_path, 'r', encoding='utf-8') as f:
                                business_rules = f.read()
                        except Exception as e:
                            business_rules = f"Could not read business rules: {e}"
                    
                    # 4. Sample mapped data
                    sample_data = "No mapped data available"
                    if os.path.exists(mapped_path):
                        df_sample = pd.read_csv(mapped_path).head(5)
                        sample_data = "Sample Mapped Data:\n" + df_sample.to_string(index=False)
                    
                    # Generate test cases using LLM
                    test_results = generate_test_cases(source_schema, mapping_spec, business_rules, sample_data)
                    
                    if "error" in test_results:
                        st.error(f"❌ {test_results['error']}")
                        return
                    
                    # For any data type, generate dynamic specific validations
                    if os.path.exists(mapped_path):
                        df_for_validation = pd.read_csv(mapped_path)
                        dynamic_validations = generate_dynamic_validation_queries(df_for_validation)
                        
                        # Replace or enhance LLM-generated SQL validations with dynamic-specific ones
                        if dynamic_validations:
                            st.info("🔧 Generating data-specific validation queries...")
                            
                            # Generate corresponding test cases for dynamic validations
                            dynamic_test_cases = []
                            for i, validation in enumerate(dynamic_validations):
                                test_case = {
                                    "id": validation["test_id"],
                                    "category": "Data Quality",
                                    "title": validation["description"].split(" - ")[0],
                                    "description": f"Automated validation: {validation['description']}",
                                    "steps": [
                                        "1. Execute SQL validation query",
                                        "2. Check if result count is 0 (pass) or >0 (fail)",
                                        "3. Review any failing records if count > 0"
                                    ],
                                    "expected_result": "Query should return 0 for passing validation",
                                    "severity": "High" if "null" in validation["description"].lower() or "duplicate" in validation["description"].lower() else "Medium"
                                }
                                dynamic_test_cases.append(test_case)
                            
                            # Use dynamic validations instead of LLM-generated ones
                            test_results["sql_validations"] = dynamic_validations
                            # Add dynamic test cases to existing ones
                            test_results["test_cases"].extend(dynamic_test_cases)
                    
                    # Validate and fix SQL queries before saving/displaying
                    if "sql_validations" in test_results and test_results["sql_validations"]:
                        st.info("🔧 Validating and fixing SQL queries...")
                        
                        fixed_validations = []
                        for sql_validation in test_results["sql_validations"]:
                            original_query = sql_validation.get('query', '')
                            if original_query:
                                # Use the mapped data for validation since it's what will be tested
                                corrected_query, is_valid = validate_and_fix_sql(original_query, source_schema, df_mapped)
                                
                                # Update the validation with corrected query
                                sql_validation['query'] = corrected_query
                                sql_validation['query_sql'] = corrected_query  # For database storage
                                
                                # Add validation status to description
                                original_desc = sql_validation.get('description', '')
                                if not is_valid:
                                    sql_validation['description'] = f"⚠️ Auto-corrected: {original_desc}"
                                elif corrected_query != original_query:
                                    sql_validation['description'] = f"✅ Fixed: {original_desc}"
                                
                            fixed_validations.append(sql_validation)
                        
                        test_results["sql_validations"] = fixed_validations
                        st.success("✅ SQL queries validated and corrected!")
                    
                    # Save the batch if name is provided
                    batch_id = None
                    if batch_name.strip():
                        batch_id = save_test_case_batch(project_id, batch_name.strip(), test_results)
                        if batch_id:
                            st.success(f"✅ Test cases saved as batch: {batch_name}")
                        else:
                            st.warning("⚠️ Test cases generated but could not be saved to database")
                    else:
                        st.info("💡 Enter a batch name to save these test cases for later access")
                    
                    # Display results
                    st.success("✅ Professional QA test cases generated successfully!")
                    
                    # Store results in session state to persist through interactions
                    session_key = f"test_results_{project_id}"
                    st.session_state[session_key] = {
                        'test_cases': test_results.get("test_cases", []),
                        'sql_validations': test_results.get("sql_validations", []),
                        'batch_name': batch_name.strip() if batch_name.strip() else None,
                        'generated_at': pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    display_test_case_results(test_results.get("test_cases", []), test_results.get("sql_validations", []), df_mapped)
                
                except Exception as e:
                    st.error(f"❌ Failed to generate test cases: {str(e)}")
                    st.markdown("Please ensure all project files are properly uploaded and accessible.")

def display_test_case_results(test_cases, sql_validations, df_mapped, is_saved_batch=False):
    """
    Display test case results with SQL validations integrated under each test case.
    """
    # Auto-fix SQL queries for saved batches that might have old/broken queries
    if is_saved_batch and sql_validations:
        fixed_validations = []
        for sql_validation in sql_validations:
            original_query = sql_validation.get('query_sql', sql_validation.get('query', ''))
            if original_query:
                try:
                    # Quick validation and fix
                    corrected_query, is_valid = validate_and_fix_sql(original_query, "", df_mapped)
                    
                    # Update the query for display/execution
                    sql_validation['query_sql'] = corrected_query
                    sql_validation['query'] = corrected_query
                    
                    # Update description if query was fixed
                    if corrected_query != original_query:
                        original_desc = sql_validation.get('description', '')
                        if "✅ Fixed:" not in original_desc and "⚠️ Auto-corrected:" not in original_desc:
                            sql_validation['description'] = f"✅ Auto-fixed: {original_desc}"
                    
                except Exception as e:
                    # If validation fails, keep original but add warning
                    original_desc = sql_validation.get('description', '')
                    sql_validation['description'] = f"⚠️ May need manual fix: {original_desc}"
            
            fixed_validations.append(sql_validation)
        
        sql_validations = fixed_validations

    # Create dictionary to match test cases with their SQL validations
    sql_by_test_id = {}
    for sql_val in sql_validations:
        test_id = sql_val.get('test_id', '')
        sql_by_test_id[test_id] = sql_val

    # Create tabs: Integrated view and Summary
    test_tabs = st.tabs(["🧪 Test Cases & SQL Validations", "📊 Test Summary"])
    
    with test_tabs[0]:
        st.markdown("### 🧪 Comprehensive Test Cases")
        st.markdown("*Each test case includes its executable SQL validation (if available)*")
        
        # Show statistics at the top
        total_test_cases = len(test_cases)
        test_cases_with_sql = len([tc for tc in test_cases if sql_by_test_id.get(tc.get('test_id', tc.get('id', '')), None)])
        test_cases_without_sql = total_test_cases - test_cases_with_sql
        
        if test_cases_without_sql > 0:
            st.warning(f"📊 Displaying {total_test_cases} test cases: {test_cases_with_sql} with SQL validations, {test_cases_without_sql} without SQL")
        else:
            st.info(f"📊 Displaying {total_test_cases} test cases, all with SQL validations")
        
        for i, test_case in enumerate(test_cases):
            test_id = test_case.get('test_id', test_case.get('id', f'TC{i+1:03d}'))
            title = test_case.get('title', 'Test Case')
            severity = test_case.get('severity', 'Medium')
            
            # Check if this test case has a matching SQL validation
            matching_sql = sql_by_test_id.get(test_id)
            has_sql = matching_sql is not None
            
            # Color-code the severity in the expander title, add SQL indicator
            severity_icon = "🔴" if severity == "High" else "🟡" if severity == "Medium" else "🟢"
            sql_indicator = " 💻" if has_sql else " ⚠️"
            
            with st.expander(f"{severity_icon} {test_id} - {title} [{severity}]{sql_indicator}", expanded=False):
                # Test Case Details
                st.markdown("#### 📋 Test Case Details")
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**Category:** {test_case.get('category', 'General')}")
                    st.markdown(f"**Description:** {test_case.get('description', 'No description')}")
                with col2:
                    # Priority indicator
                    if severity == 'High':
                        st.error(f"🔴 **HIGH PRIORITY**")
                    elif severity == 'Medium':
                        st.warning(f"🟡 **MEDIUM PRIORITY**")
                    else:
                        st.info(f"🟢 **LOW PRIORITY**")
                
                st.markdown("**Test Steps:**")
                steps = test_case.get('steps', [])
                if isinstance(steps, str):
                    try:
                        import json
                        steps = json.loads(steps)
                    except:
                        steps = [steps]
                
                for step_num, step in enumerate(steps, 1):
                    st.markdown(f"{step_num}. {step}")
                
                st.markdown(f"**Expected Result:** {test_case.get('expected_result', 'Test should pass')}")
                
                # Display SQL validation if available
                if has_sql:
                    st.markdown("---")
                    st.markdown("#### 💻 SQL Validation Query")
                    
                    query = matching_sql.get('query_sql', matching_sql.get('query', 'SELECT 1'))
                    description = matching_sql.get('description', 'SQL Test')
                    
                    # Show description and query
                    st.markdown(f"**Purpose:** {description}")
                    st.code(query, language='sql')
                    
                    # Execution section
                    col_run, col_status = st.columns([1, 2])
                    
                    with col_run:
                        run_button_key = f"run_sql_{test_id}_{i}_{hash(str(df_mapped.columns.tolist()))}"
                        if st.button(f"▶️ Execute Test", key=run_button_key, type="primary"):
                            try:
                                import duckdb
                                
                                # Create a fresh DuckDB connection
                                con = duckdb.connect(':memory:')
                                con.register("data_table", df_mapped)
                                
                                # Clean and prepare the query
                                cleaned_query = query.strip()
                                if cleaned_query.endswith(';'):
                                    cleaned_query = cleaned_query[:-1]
                                
                                # Execute the query and get results
                                result = con.execute(cleaned_query).fetchdf()
                                con.close()
                                
                                # Display results immediately
                                if result.empty:
                                    st.success("✅ Query executed successfully - No records returned")
                                    st.info("*This typically means the condition was not met (good for validation queries)*")
                                else:
                                    # Enhanced result interpretation
                                    st.success(f"✅ Query executed successfully - {len(result)} record(s) returned")
                                    
                                    # Smart interpretation for validation queries
                                    if len(result) == 1 and len(result.columns) == 1:
                                        # Single value result (likely a COUNT query)
                                        count_value = result.iloc[0, 0]
                                        col_name = result.columns[0].lower()
                                        
                                        if 'count' in col_name or result.columns[0].lower().endswith('_count'):
                                            if count_value == 0:
                                                st.success(f"🎯 **VALIDATION PASSED** - No issues found (count = 0)")
                                            else:
                                                st.warning(f"⚠️ **VALIDATION FAILED** - Found {count_value} issue(s)")
                                        else:
                                            st.info(f"📊 Result: {count_value}")
                                    
                                    # Always show the data table
                                    st.dataframe(result, use_container_width=True)
                                    
                                    # Show download option for larger results
                                    if len(result) > 10:
                                        csv_data = result.to_csv(index=False)
                                        st.download_button(
                                            label="📥 Download Results as CSV",
                                            data=csv_data,
                                            file_name=f"query_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                            mime="text/csv"
                                        )
                                
                                # Show the executed query for reference
                                st.markdown("---")
                                st.markdown("#### 📝 Executed Query Details")
                                st.code(query, language='sql')
                                st.markdown(f"**Execution Time:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
                                st.markdown(f"**Total Records Processed:** {len(df_mapped)}")
                                
                            except Exception as e:
                                st.error(f"❌ Query execution failed: {str(e)}")
                                
                                # Enhanced debug information (as markdown section to avoid nested expanders)
                                st.markdown("---")
                                st.markdown("#### 🔍 Debug Information")
                                st.markdown("**Query that failed:**")
                                st.code(query, language='sql')
                                st.markdown("**Available columns:**")
                                st.write(df_mapped.columns.tolist())
                                st.markdown("**Sample data:**")
                                st.dataframe(df_mapped.head(3))
                                st.markdown("**Data types:**")
                                for col, dtype in zip(df_mapped.columns, df_mapped.dtypes):
                                    st.text(f"{col}: {dtype}")
                                st.markdown("**Error Details:**")
                                st.code(str(e))
                
                else:
                    # No matching SQL found - show manual testing guidance
                    st.markdown("---")
                    st.markdown("#### ⚠️ Manual Testing Required")
                    st.warning("No automated SQL validation is available for this test case.")
                    st.markdown("**Manual Testing Steps:**")
                    st.markdown("• Review the data manually based on the test steps above")
                    st.markdown("• Use the SQL Query Generation tool (left column) to create custom queries")
                    st.markdown("• Document findings and any issues discovered")
                    
                    # Offer to generate a basic SQL query
                    if st.button(f"🔧 Try to Generate SQL", key=f"generate_sql_{test_id}_{i}"):
                        st.info("💡 **Tip:** Use the 'SQL Query Generation' tool in the left column to create a custom validation query for this test case.")
                
                st.markdown("---")  # Separator between test cases
    
    with test_tabs[1]:
        st.markdown("### 📊 Test Summary")
        
        test_cases_count = len(test_cases)
        sql_tests_count = len(sql_validations)
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("📝 Test Cases", test_cases_count)
        col_b.metric("💻 SQL Validations", sql_tests_count)
        col_c.metric("🎯 Total Tests", test_cases_count + sql_tests_count)
        
        # Category breakdown
        if test_cases:
            categories = {}
            severities = {}
            
            for tc in test_cases:
                cat = tc.get("category", "General")
                sev = tc.get("severity", "Medium")
                categories[cat] = categories.get(cat, 0) + 1
                severities[sev] = severities.get(sev, 0) + 1
            
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.markdown("**📊 Test Categories:**")
                for cat, count in categories.items():
                    st.markdown(f"• {cat}: {count} tests")
            
            with col_right:
                st.markdown("**🎚️ Priority Distribution:**")
                for sev, count in severities.items():
                    color = "🔴" if sev == "High" else "🟡" if sev == "Medium" else "🟢"
                    st.markdown(f"• {color} {sev}: {count} tests")




# --- MAIN ENTRY ---
def load_tab():
    logo_path = "C:/Users/User/Downloads/Final-Logo-Design-for-K-Data-Colorfull-e1736333692140.jpg"
    if os.path.exists(logo_path):
        st.image(logo_path, width=150)
    else:
        st.warning("⚠ Logo not found at the specified path.")

    st.title("View Projects")

    rows = get_all_projects()
    df = pd.DataFrame(rows)

    if df.empty:
        st.info("No projects available.")
        return

    df_sorted = df.sort_values(by="created_at", ascending=False)

    with st.expander("📂View All Projects"):
        # Update the displayed columns to include business rules
        display_columns = ["project_id", "project_name", "project_description", "created_at"]
        if "business_rules_files" in df_sorted.columns:
            display_columns.append("business_rules_files")
        st.dataframe(df_sorted[display_columns])

    selected_project = st.selectbox("Select a Project", df_sorted["project_name"].tolist())

    if selected_project:
        project_row = df_sorted[df_sorted["project_name"] == selected_project].iloc[0]
        project_id = int(project_row["project_id"])
        st.session_state.selected_project_id = project_id

        with st.expander("🗑 Delete Project"):
            st.markdown(f"*Project:* {selected_project}")
            delete_confirm = st.checkbox("I understand deleting this project is permanent.")
            if st.button("Delete Project", disabled=not delete_confirm):
                delete_project_by_id(project_id)
                base_path = os.path.join("projects", selected_project.replace(' ', '_'))
                if os.path.exists(base_path):
                    import shutil
                    shutil.rmtree(base_path)
                st.success(f"Project '{selected_project}' has been deleted.")
                st.rerun()

        tabs = st.tabs(["QA Genius", "Migration Dashboard"])
        with tabs[0]:
            show_qa_interface(project_id)
        with tabs[1]:
            show_project_dashboard(project_id)


# ---------- Dashboard ----------
def show_project_dashboard(project_id):
    import plotly.express as px

    project = get_project_by_id(project_id)
    files = get_project_files(project_id)

    # Generate project path dynamically since project_path column doesn't exist
    safe_name = f"{project['project_name'].replace(' ', '_')}_{project_id}"
    base_path = os.path.join("projects", safe_name)
    mapped_path = os.path.join(base_path, "artifacts", "mapped_output.csv")
    summary_csv = os.path.join(base_path, "artifacts", "migration_summary.csv")
    failed_rows_csv = os.path.join(base_path, "artifacts", "failed_rows.csv")
    pdf_path = os.path.join(base_path, "artifacts", "business_summary.pdf")
    mapping_file_path = next((f['file_path'] for f in files if f['file_type'] == 'mapping'), None)
    business_rules_file_path = next((f['file_path'] for f in files if f['file_type'] == 'business_rules'), None)

    st.markdown(f"## Dashboard for Project: {project['project_name']}")
    st.markdown(f"Description: {project['project_description']}")
    st.markdown(f"Created At: {project['created_at']}")

    # --- Project Files Section ---
    with st.expander("📁 Project Files"):
        source_files = [f for f in files if f['file_type'] == 'source']
        mapping_files = [f for f in files if f['file_type'] == 'mapping']
        business_rules_files = [f for f in files if f['file_type'] == 'business_rules']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**📤 Source Files:**")
            for file in source_files:
                st.markdown(f"• {file['file_name']}")
                
        with col2:
            st.markdown("**🗂️ Mapping Files:**")
            for file in mapping_files:
                st.markdown(f"• {file['file_name']}")
                
        with col3:
            st.markdown("**📋 Business Rules:**")
            if business_rules_files:
                for file in business_rules_files:
                    st.markdown(f"• {file['file_name']}")
            else:
                st.markdown("• *No business rules uploaded*")

    # --- Business Rules Preview Section (separate from project files to avoid nesting) ---
    if business_rules_files:
        with st.expander("📋 Business Rules Preview"):
            for file in business_rules_files:
                st.markdown(f"**{file['file_name']}**")
                if file['file_name'].endswith('.txt') and os.path.exists(file['file_path']):
                    try:
                        with open(file['file_path'], 'r', encoding='utf-8') as f:
                            content = f.read()
                            st.text_area(f"Content of {file['file_name']}", content, height=200, disabled=True, key=f"business_rules_{file['file_name']}")
                    except Exception as e:
                        st.error(f"Could not preview file: {e}")
                else:
                    st.info(f"Preview not available for {file['file_name']} (only .txt files can be previewed)")

    # --- Mapped Output Preview ---
    with st.expander("View Mapped Output"):
        if os.path.exists(mapped_path):
            df_mapped = pd.read_csv(mapped_path)
            st.dataframe(df_mapped.head(10))
            with open(mapped_path, "rb") as f:
                st.download_button("Download Mapped Output", f, file_name="mapped_output.csv")

    # --- Read Migration Summary CSV ---
    total_records, passed, failed, partial = 0, 0, 0, 0
    success_rate, fail_rate, partial_rate = 0.0, 0.0, 0.0

    if os.path.exists(summary_csv):
        df_summary = pd.read_csv(summary_csv)
        if not df_summary.empty:
            row = df_summary.iloc[0]
            total_records = int(row.get("total_records", 0))
            passed = int(row.get("passed", 0))
            failed = int(row.get("failed", 0))
            partial = int(row.get("partial", 0))
            success_rate = float(row.get("success_rate", 0.0))
            fail_rate = float(row.get("fail_rate", 0.0))
            partial_rate = float(row.get("partial_rate", 0.0))

    # --- Failed Record Check ---
    unmapped_count = 0
    if os.path.exists(failed_rows_csv):
        df_failed = pd.read_csv(failed_rows_csv)
        unmapped_count = df_failed.isnull().sum().sum()

    # --- Summary Section ---
    st.subheader("Migration Health & Record Summary")
    colA, colB = st.columns([2, 3])
    with colA:
        show_migration_gauge(success_rate)
    with colB:
        st.markdown("#### Metrics Overview")
        col1, col2, col3 = st.columns(3)
        col1.metric("Records Successfully Migrated", f"{success_rate:.1f}%")
        col2.metric("Records Dropped", f"{fail_rate:.1f}%")
        col3.metric("Partially Migrated", f"{partial_rate:.1f}%")
        col4, col5, col6 = st.columns(3)
        col4.metric("Source Records", total_records)
        col5.metric("Target Records", passed)
        col6.metric("Partial Records", unmapped_count)

    # --- Rule Compliance ---
    st.subheader("Rule Compliance Overview")
    show_rule_compliance_section(base_path)

    # --- Mapping Summary ---
    if mapping_file_path and os.path.exists(mapping_file_path):
        # Handle both CSV and XLSX mapping files
        if mapping_file_path.endswith('.csv'):
            df_map = pd.read_csv(mapping_file_path)
        else:  # xlsx
            df_map = pd.read_excel(mapping_file_path)

        # Detect column mappings dynamically
        col_map = detect_column_mappings(df_map)
        
        # Check if we found the essential columns
        if 'source' not in col_map or 'target' not in col_map:
            st.warning("⚠️ Could not detect source and target columns in mapping file for analysis.")
            st.info(f"Available columns: {df_map.columns.tolist()}")
        else:
            def compute_status(row, col_map):
                target_col = col_map['target']
                transform_col = col_map.get('transformation_code', '')
                
                target_exists = pd.notnull(row[target_col]) and str(row[target_col]).strip() != ""
                transformation_code = str(row.get(transform_col, "")).strip() if transform_col else ""
                
                if not target_exists:
                    return "Not Mapped"
                elif not transformation_code or transformation_code.lower() in ["none", "", "null"]:
                    return "Column Mapped Correctly"
                else:
                    try:
                        compile(transformation_code, "<string>", "exec")
                        return "Fully Mapped"
                    except:
                        return "Mapping Failed"

            df_map["status"] = df_map.apply(lambda row: compute_status(row, col_map), axis=1)

            st.subheader("Data Mapping Summary")
            status_options = ["Fully Mapped", "Column Mapped Correctly", "Mapping Failed", "Not Mapped"]
            selected_statuses = st.multiselect("🔍 Filter Mapping Summary By Status", options=status_options, default=status_options)
            df_display = df_map[df_map["status"].isin(selected_statuses)]

            status_counts = df_display["status"].value_counts().reset_index()
            status_counts.columns = ["Mapping Status", "Count"]
            if not status_counts.empty:
                fig = px.bar(status_counts, x="Count", y="Mapping Status", orientation="h", color="Mapping Status", text="Count", title="Mapping Status Overview", height=400)
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            # Display columns using detected names
            display_cols = [col_map['source'], col_map['target']]
            if 'transformation_code' in col_map:
                display_cols.append(col_map['transformation_code'])
            display_cols.append("status")
            
            st.dataframe(df_display[display_cols])

    # --- Alerts Section (Smart) ---
    st.subheader("Priority Issues & Alerts")

    if unmapped_count > 0 or fail_rate > 0 or partial > 0 or success_rate < 80:
        alert1, alert2, alert3, alert4 = st.columns(4)

        if unmapped_count > 0:
            alert1.error("Unmapped Critical Fields")
        else:
            alert1.info("No Unmapped Fields")

        if fail_rate > 0:
            alert2.warning("⚠ Rules Failed in Compliance")
        else:
            alert2.success("All Rules Passed")

        if partial > 0:
            alert3.warning("⚠ Data Gaps Detected")
        else:
            alert3.info("No Data Gaps")

        if success_rate < 80:
            alert4.warning("Long Running Migration")
        else:
            alert4.success("Migration Healthy")
    else:
        st.info(" No alerts to display. Data looks good.")

    # --- Business Report ---
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            st.subheader("📥 Business Report")
            st.download_button("📄 Download Business Summary (PDF)", f, file_name="business_summary.pdf")

def detect_column_mappings(mapping_df: pd.DataFrame) -> dict:
    """
    Dynamically detect column mappings based on common naming patterns.
    Returns a dictionary mapping standard names to actual column names.
    """
    columns = [col.lower().strip() for col in mapping_df.columns]
    column_map = {}
    
    # Source column variations
    source_patterns = ['source', 'sourcefield', 'source_field', 'src', 'from', 'input', 'original']
    for pattern in source_patterns:
        matches = [col for col in columns if pattern in col.lower()]
        if matches:
            # Find the actual column name (preserving original case)
            actual_col = next(orig_col for orig_col in mapping_df.columns 
                            if orig_col.lower().strip() == matches[0])
            column_map['source'] = actual_col
            break
    
    # Target column variations
    target_patterns = ['target', 'targetfield', 'target_field', 'tgt', 'to', 'output', 'destination', 'dest']
    for pattern in target_patterns:
        matches = [col for col in columns if pattern in col.lower()]
        if matches:
            actual_col = next(orig_col for orig_col in mapping_df.columns 
                            if orig_col.lower().strip() == matches[0])
            column_map['target'] = actual_col
            break
    
    # Transformation column variations
    transform_patterns = ['transformation', 'transform', 'transformation_code', 'transform_code', 
                         'code', 'logic', 'rule', 'formula', 'expression']
    for pattern in transform_patterns:
        matches = [col for col in columns if pattern in col.lower()]
        if matches:
            actual_col = next(orig_col for orig_col in mapping_df.columns 
                            if orig_col.lower().strip() == matches[0])
            column_map['transformation_code'] = actual_col
            break
    
    return column_map