import ollama
import json
import duckdb
import re
import time

# --- Set model names ---
SQL_MODEL = "mistral:7b-instruct"
INSIGHT_MODEL = "mistral:7b-instruct"
TEST_CASE_MODEL = "mistral:7b-instruct"

# --- Core LLM call ---
def query_llm(prompt: str, model: str) -> str:
    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.get("message", {}).get("content", "").strip()
        if not content:
            return "ERROR: Empty response from LLM"
        return content
    except Exception as e:
        return f"ERROR: {str(e)}"

# --- Timed LLM call for tracking performance ---
def query_llm_with_timing(prompt: str, model: str) -> tuple[str, float]:
    """
    Execute LLM query and return both the response and the time taken.
    Returns (response, time_in_seconds)
    """
    try:
        start_time = time.time()
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        end_time = time.time()
        duration = end_time - start_time
        
        content = response.get("message", {}).get("content", "").strip()
        if not content:
            return "ERROR: Empty response from LLM", duration
        return content, duration
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time if 'start_time' in locals() else 0
        return f"ERROR: {str(e)}", duration

# --- SQL Cleanup Function ---
def clean_sql_response(response: str) -> str:
    if "ERROR" in response:
        return "SELECT * FROM data_table LIMIT 10"

    # Remove outer tags
    cleaned = response.replace("<sql>", "").replace("</sql>", "").strip()

    # Handle code blocks
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("sql"):
            cleaned = cleaned[3:].strip()

    # Remove lines that look like LLM metadata
    lines = cleaned.splitlines()
    sql_lines = []
    for line in lines:
        if not line.strip().startswith(("<s", "#", "--", "```")):
            sql_lines.append(line)
    cleaned_sql = "\n".join(sql_lines).strip()

    # 🔥 Strip known bad prefixes and patterns
    bad_prefixes = ["duckdb.", "duckdb_", "db.", "schema.", "`"]
    for bad in bad_prefixes:
        cleaned_sql = cleaned_sql.replace(bad, "")

    # Remove common problematic patterns
    cleaned_sql = cleaned_sql.replace("::INTEGER", "")
    cleaned_sql = cleaned_sql.replace("::VARCHAR", "")
    cleaned_sql = cleaned_sql.replace("::TEXT", "")
    
    # 🧼 Remove trailing semicolon
    if cleaned_sql.endswith(";"):
        cleaned_sql = cleaned_sql[:-1]

    # Final safety check
    if "duckdb" in cleaned_sql.lower() or not cleaned_sql or cleaned_sql.lower().startswith("error"):
        return "SELECT * FROM data_table LIMIT 10"

    return cleaned_sql.strip()

# --- SQL Query Generator ---
def generate_sql_query(table_schema: str, question: str) -> tuple[str, float]:
    prompt = f"""
You are a highly skilled SQL analyst.

Your task is to generate a clean, syntactically valid SQL query using the DuckDB SQL dialect.
Assume the data is loaded into a single table named `data_table`. Do not use any database or schema names like 'duckdb.'.

=== TABLE SCHEMA (column_name: type) ===
{table_schema}
=== END SCHEMA ===

User Question: "{question}"

Instructions:
- Use only valid DuckDB SQL syntax.
- Do not add any comments or explanations — return only clean SQL.
- If no specific condition is mentioned, just return SELECT * FROM data_table LIMIT 10.
- Do NOT use ::type casting, backticks, or schema prefixes.

SQL:
"""
    raw_response, llm_time = query_llm_with_timing(prompt, model=SQL_MODEL)

    # 🧠 Debug output
    print("RAW SQL FROM LLM:\n", raw_response)
    cleaned_sql = clean_sql_response(raw_response)
    print("CLEANED SQL SENT TO DUCKDB:\n", cleaned_sql)

    return cleaned_sql, llm_time

# --- SQL Validation and Correction Function ---
def validate_and_fix_sql(query: str, schema_info: str, sample_data_df) -> tuple[str, bool]:
    """
    Validate SQL query against actual data and fix common issues.
    Returns (corrected_query, is_valid)
    """
    try:
        # Create test connection
        con = duckdb.connect(':memory:')
        con.register("data_table", sample_data_df)
        
        # Test original query first
        try:
            result = con.execute(query).fetchdf()
            con.close()
            return query, True  # Query works as-is
        except Exception as original_error:
            original_error_str = str(original_error)
            print(f"Original query failed: {original_error_str}")
            
            # Fix common issues systematically
            fixed_query = query.strip()
            
            # 1. Fix column name case sensitivity issues
            available_columns = sample_data_df.columns.tolist()
            
            # Replace column names case-insensitively
            for col in available_columns:
                # Create patterns that match word boundaries to avoid partial replacements
                pattern = r'\b' + re.escape(col) + r'\b'
                fixed_query = re.sub(pattern, col, fixed_query, flags=re.IGNORECASE)
            
            # 2. Fix DuckDB function compatibility
            function_replacements = {
                r'\bCURDATE\(\)': 'current_date',
                r'\bNOW\(\)': 'current_timestamp',
                r'\bYEAR\(CURDATE\(\)\)': 'YEAR(current_date)',
                r'\bMONTH\(CURDATE\(\)\)': 'MONTH(current_date)',
                r'\bDAY\(CURDATE\(\)\)': 'DAY(current_date)',
            }
            
            for old_pattern, new_func in function_replacements.items():
                fixed_query = re.sub(old_pattern, new_func, fixed_query, flags=re.IGNORECASE)
            
            # 3. Fix common pattern issues
            # Fix LIKE patterns that use SQL standards instead of actual patterns
            if 'YYYY-MM-DD' in fixed_query:
                fixed_query = fixed_query.replace("NOT LIKE 'YYYY-MM-DD'", "NOT LIKE '____-__-__'")
                fixed_query = fixed_query.replace("LIKE 'YYYY-MM-DD'", "LIKE '____-__-__'")
            
            # Fix phone patterns
            if '+1-%-XXXX' in fixed_query:
                fixed_query = fixed_query.replace("LIKE '+1-%-XXXX'", "LIKE '___-____'")
                fixed_query = fixed_query.replace("NOT LIKE '+1-%-XXXX'", "NOT LIKE '___-____'")
            
            # Test the pattern-fixed query
            try:
                result = con.execute(fixed_query).fetchdf()
                con.close()
                print(f"Pattern-fixed query works: {fixed_query}")
                return fixed_query, True
            except Exception as pattern_error:
                print(f"Pattern fix failed: {pattern_error}")
                
                # 4. Use LLM for more complex fixes
                correction_prompt = f"""
Fix this SQL query to work with DuckDB and the actual data structure.

Original error: {original_error_str}
Available columns: {available_columns}
Failed query: {query}

Sample data structure:
{sample_data_df.head(2).to_string()}

Requirements:
- Use exact column names: {available_columns}
- Use DuckDB-compatible functions (current_date not CURDATE())
- For date validation, use patterns like '____-__-__' not 'YYYY-MM-DD'
- For phone validation, use realistic patterns based on the sample data
- Keep the same validation logic and purpose
- Return a COUNT query that returns 0 when validation passes
- ONLY return the SQL query, no explanations

Corrected SQL:
"""
                
                try:
                    corrected_sql, correction_time = query_llm_with_timing(correction_prompt, model=SQL_MODEL)
                    print(f"🕒 LLM SQL Correction Time: {correction_time:.2f} seconds")
                    corrected_sql = clean_sql_response(corrected_sql)
                    
                    # Test the LLM-corrected query
                    result = con.execute(corrected_sql).fetchdf()
                    con.close()
                    print(f"LLM-corrected query works: {corrected_sql}")
                    return corrected_sql, True
                except Exception as llm_error:
                    print(f"LLM correction failed: {llm_error}")
                    con.close()
                    
                    # 5. Generate a meaningful fallback based on the original intent
                    query_lower = query.lower()
                    original_question = schema_info.lower() if schema_info else ""
                    
                    if 'birth' in query_lower or 'birth_date' in query_lower or 'date_of_birth' in query_lower:
                        # Birth date specific validation
                        birth_cols = [col for col in available_columns if 'birth' in col.lower() or 'dob' in col.lower()]
                        if birth_cols:
                            birth_col = birth_cols[0]
                            fallback = f"SELECT COUNT(*) as invalid_birth_dates FROM data_table WHERE {birth_col} IS NULL OR {birth_col} > current_date OR LENGTH({birth_col}) != 10"
                        else:
                            # Look for any date column
                            date_cols = [col for col in available_columns if 'date' in col.lower()]
                            if date_cols:
                                fallback = f"SELECT COUNT(*) as invalid_dates FROM data_table WHERE {date_cols[0]} IS NULL OR {date_cols[0]} > current_date"
                            else:
                                fallback = "SELECT COUNT(*) as no_date_columns FROM data_table WHERE 1=0"
                    elif 'null' in query_lower or 'is null' in query_lower:
                        fallback = f"SELECT COUNT(*) as null_count FROM data_table WHERE {available_columns[0]} IS NULL"
                    elif 'date' in query_lower:
                        date_cols = [col for col in available_columns if 'date' in col.lower()]
                        if date_cols:
                            fallback = f"SELECT COUNT(*) as invalid_dates FROM data_table WHERE {date_cols[0]} IS NULL OR LENGTH({date_cols[0]}) != 10"
                        else:
                            fallback = "SELECT COUNT(*) as validation_count FROM data_table WHERE 1=0"
                    elif 'phone' in query_lower:
                        phone_cols = [col for col in available_columns if 'phone' in col.lower()]
                        if phone_cols:
                            fallback = f"SELECT COUNT(*) as invalid_phones FROM data_table WHERE {phone_cols[0]} IS NULL OR LENGTH({phone_cols[0]}) < 7"
                        else:
                            fallback = "SELECT COUNT(*) as validation_count FROM data_table WHERE 1=0"
                    elif 'weight' in query_lower:
                        weight_cols = [col for col in available_columns if 'weight' in col.lower()]
                        if weight_cols:
                            fallback = f"SELECT COUNT(*) as invalid_weight FROM data_table WHERE {weight_cols[0]} IS NULL OR {weight_cols[0]} < 30 OR {weight_cols[0]} > 400"
                        else:
                            fallback = "SELECT COUNT(*) as validation_count FROM data_table WHERE 1=0"
                    elif 'name' in query_lower:
                        name_cols = [col for col in available_columns if 'name' in col.lower()]
                        if name_cols:
                            fallback = f"SELECT COUNT(*) as invalid_names FROM data_table WHERE {name_cols[0]} IS NULL OR LENGTH({name_cols[0]}) < 2"
                        else:
                            fallback = "SELECT COUNT(*) as validation_count FROM data_table WHERE 1=0"
                    else:
                        fallback = "SELECT COUNT(*) as validation_count FROM data_table WHERE 1=0"
                    
                    return fallback, False
        
    except Exception as e:
        print(f"Complete validation failure: {e}")
        # Return a completely safe query
        return "SELECT COUNT(*) as total_records FROM data_table", False

# --- Enhanced Test Case Generator ---
def generate_test_cases(source_data_schema: str, mapping_spec: str, business_rules: str, sample_data: str) -> dict:
    """
    Generate comprehensive test cases like a professional QA engineer.
    Returns both structured test cases and SQL validation queries with timing information.
    """
    
    prompt = f"""
You are a highly experienced QA Engineer tasked with creating comprehensive test cases for a data migration project.

=== SOURCE DATA SCHEMA ===
{source_data_schema}
=== END SOURCE SCHEMA ===

=== MAPPING SPECIFICATION ===
{mapping_spec}
=== END MAPPING ===

=== BUSINESS RULES ===
{business_rules}
=== END BUSINESS RULES ===

=== SAMPLE DATA (first few rows) ===
{sample_data}
=== END SAMPLE DATA ===

Create a comprehensive test suite that covers:

1. **Data Quality Tests**: Null values, data types, format validation
2. **Business Rule Compliance**: Tests based on the business rules provided
3. **Mapping Accuracy**: Verify field transformations work correctly
4. **Edge Cases**: Boundary conditions, special characters, extreme values
5. **Data Integrity**: Uniqueness, referential integrity, completeness

IMPORTANT: For EACH test case, you MUST also create a corresponding SQL query that validates that specific test.

CRITICAL SQL REQUIREMENTS:
- Use simple DuckDB-compatible SQL syntax
- Always use COUNT(*) or COUNT(column_name) for validation queries
- Return 0 when test passes, >0 when test fails
- Use actual column names from the provided schema (look at the sample data section for exact column names)
- Do NOT use type casting (::), complex functions, or schema prefixes
- Use current_date instead of CURDATE(), current_timestamp instead of NOW()
- Keep queries simple and focused on one validation rule
- CRITICAL: Look at the sample data section to see the EXACT column names available
- For date validation, use realistic patterns like '____-__-__' or length checks, not 'YYYY-MM-DD'
- For phone validation, use patterns based on actual data format (like '___-____' for XXX-XXXX format)
- For numeric validations, use realistic ranges based on the data type
- For text validations, use functions like LENGTH(), UPPER(), or pattern matching

EXAMPLE GOOD SQL QUERIES based on typical medical data:
- Null check: "SELECT COUNT(*) FROM data_table WHERE patient_id IS NULL"
- Date format: "SELECT COUNT(*) FROM data_table WHERE date_of_birth IS NULL OR LENGTH(date_of_birth) != 10"
- Phone format: "SELECT COUNT(*) FROM data_table WHERE phone IS NULL OR LENGTH(phone) < 7"
- Weight range: "SELECT COUNT(*) FROM data_table WHERE weight < 30 OR weight > 300"
- Name validation: "SELECT COUNT(*) FROM data_table WHERE full_name IS NULL OR LENGTH(full_name) < 2"

Format your response as a JSON object with this EXACT structure:
{{
    "test_cases": [
        {{
            "id": "TC001",
            "category": "Data Quality",
            "title": "Validate No Null Values in Required Fields",
            "description": "Ensure that all required fields contain valid data and no null values",
            "steps": [
                "1. Execute SQL query to check for null values in required columns",
                "2. Verify that count of null values is 0",
                "3. If nulls found, identify which records and fields are affected"
            ],
            "expected_result": "All required fields should contain non-null values. Query should return 0 records with nulls.",
            "severity": "High"
        }},
        {{
            "id": "TC002", 
            "category": "Business Rule Compliance",
            "title": "Validate Email Format",
            "description": "Check that all email addresses follow proper email format pattern",
            "steps": [
                "1. Run SQL query with regex pattern to identify invalid emails",
                "2. Count records with invalid email format",
                "3. Review any records that fail validation"
            ],
            "expected_result": "All email addresses should follow valid email format (contains @ and domain)",
            "severity": "Medium"
        }}
    ],
    "sql_validations": [
        {{
            "test_id": "TC001",
            "query": "SELECT COUNT(*) as null_count FROM data_table WHERE column_name IS NULL OR column_name = ''",
            "description": "Count null or empty values in required fields - should return 0"
        }},
        {{
            "test_id": "TC002",
            "query": "SELECT COUNT(*) as invalid_emails FROM data_table WHERE email_column NOT LIKE '%@%'",
            "description": "Count records with invalid email format - should return 0"
        }}
    ]
}}

CRITICAL REQUIREMENTS:
- Generate at least 8-12 test cases covering all categories above
- For EVERY test case, create a corresponding SQL validation query
- Use actual column names from the schema provided
- Make SQL queries specific to the data structure and business rules
- Ensure test_id in sql_validations matches the id in test_cases
- Only respond with valid JSON - no additional text or explanations
"""

    try:
        raw_response, llm_time = query_llm_with_timing(prompt, model=TEST_CASE_MODEL)
        print("RAW TEST CASES FROM LLM:\n", raw_response)
        print(f"🕒 LLM Test Case Generation Time: {llm_time:.2f} seconds")
        
        # Try to parse as JSON
        try:
            # Clean the response to extract JSON
            cleaned_response = raw_response.strip()
            
            # Remove common markdown formatting
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
                
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            
            # Remove any leading/trailing whitespace
            cleaned_response = cleaned_response.strip()
            
            # Try to find JSON content if it's embedded in text
            if '{' in cleaned_response and '}' in cleaned_response:
                start_idx = cleaned_response.find('{')
                end_idx = cleaned_response.rfind('}') + 1
                cleaned_response = cleaned_response[start_idx:end_idx]
            
            test_cases_data = json.loads(cleaned_response)
            
            # Validate that we have both test_cases and sql_validations
            if "test_cases" not in test_cases_data:
                test_cases_data["test_cases"] = []
            if "sql_validations" not in test_cases_data:
                test_cases_data["sql_validations"] = []
            
            # Ensure test cases have both id and test_id fields for consistency
            for test_case in test_cases_data.get("test_cases", []):
                if "id" in test_case and "test_id" not in test_case:
                    test_case["test_id"] = test_case["id"]
                elif "test_id" in test_case and "id" not in test_case:
                    test_case["id"] = test_case["test_id"]
            
            # Add timing information to the response
            test_cases_data["generation_time"] = llm_time
            test_cases_data["generation_time_formatted"] = f"{llm_time:.2f} seconds"
            
            print(f"Successfully parsed JSON: {len(test_cases_data.get('test_cases', []))} test cases, {len(test_cases_data.get('sql_validations', []))} SQL validations (Generated in {llm_time:.2f}s)")
            
            return test_cases_data
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            print(f"Attempted to parse: {cleaned_response[:500]}...")
            
            # If JSON parsing fails, create a more structured fallback response
            return {
                "test_cases": [
                    {
                        "id": "TC001",
                        "category": "Generated Test",
                        "title": "LLM Generated Test Cases (JSON Parse Failed)",
                        "description": f"Raw LLM output (first 1000 chars): {raw_response[:1000]}",
                        "steps": [
                            "Review the generated content below",
                            "Manually extract test cases if needed",
                            "Consider refining the prompt for better JSON output"
                        ],
                        "expected_result": "Test cases should be comprehensive and actionable",
                        "severity": "Medium"
                    }
                ],
                "sql_validations": [
                    {
                        "test_id": "TC001",
                        "query": "SELECT COUNT(*) as total_records FROM data_table",
                        "description": "Basic data count validation (fallback query)"
                    },
                    {
                        "test_id": "TC002", 
                        "query": "SELECT * FROM data_table WHERE 1=0",
                        "description": "Schema validation - check table structure"
                    }
                ],
                "parsing_error": str(e),
                "raw_response": raw_response,
                "generation_time": llm_time,
                "generation_time_formatted": f"{llm_time:.2f} seconds"
            }
    except Exception as e:
        print(f"LLM query failed: {e}")
        return {
            "error": f"Failed to generate test cases: {str(e)}",
            "test_cases": [],
            "sql_validations": [],
            "generation_time": 0,
            "generation_time_formatted": "0.00 seconds"
        }

# --- Data Insight Generator (unchanged) ---
def generate_data_insight(table_schema: str, sample_rows: list, question: str) -> str:
    try:
        sample_rows = sample_rows[:10]  # Limit to first 10 rows
        formatted_rows = json.dumps(sample_rows, indent=2)

        prompt = f"""
You are a highly accurate and detail-oriented data analyst.

Your task is to analyze the data provided below and answer the user's question with insights derived directly from that data.

=== SCHEMA START ===
{table_schema}
=== SCHEMA END ===

=== DATA START ===
{formatted_rows}
=== DATA END ===

User Question: "{question}"

Instructions:
- Only use the data shown to answer the question. Do not assume other records exist.
- If the question refers to a condition that is not met in the data, state that clearly.
- Optionally suggest the closest matching result, but only if it is significantly relevant — and clearly label it as "closest match".
- Never guess or fabricate values.
- Make your response precise, readable, and fact-based.

Insight:
"""
        result = query_llm(prompt, model=INSIGHT_MODEL)
        if "ERROR" in result or not result.strip():
            return "No valid insight could be generated. Please try rephrasing the question or check the input data."
        return result.strip()

    except Exception as e:
        return f"ERROR during insight generation: {str(e)}"

# --- Generate Dynamic Data Validation Queries ---
def generate_dynamic_validation_queries(sample_df) -> list:
    """
    Generate validation queries dynamically for any data structure based on column names and data types.
    """
    validations = []
    columns = sample_df.columns.tolist()
    test_id_counter = 1
    
    # Analyze each column and generate appropriate validations
    for col in columns:
        col_lower = col.lower()
        
        # Get sample data to understand the column
        sample_values = sample_df[col].dropna().head(3).tolist()
        data_type = str(sample_df[col].dtype)
        
        # 1. Basic null check for all columns
        validations.append({
            "test_id": f"TC{test_id_counter:03d}",
            "query": f"SELECT COUNT(*) as null_count FROM data_table WHERE {col} IS NULL",
            "description": f"Count null values in {col} - should return 0 if column is required"
        })
        test_id_counter += 1
        
        # 2. ID columns (containing 'id', 'key', 'pk')
        if any(keyword in col_lower for keyword in ['id', 'key', 'pk']):
            validations.append({
                "test_id": f"TC{test_id_counter:03d}",
                "query": f"SELECT COUNT(*) - COUNT(DISTINCT {col}) as duplicate_count FROM data_table",
                "description": f"Count duplicate values in {col} - should return 0 for unique identifiers"
            })
            test_id_counter += 1
        
        # 3. Date columns (containing 'date', 'time', or date-like format)
        if any(keyword in col_lower for keyword in ['date', 'time']) or (sample_values and '-' in str(sample_values[0])):
            validations.append({
                "test_id": f"TC{test_id_counter:03d}",
                "query": f"SELECT COUNT(*) as invalid_dates FROM data_table WHERE {col} IS NOT NULL AND LENGTH({col}) != 10",
                "description": f"Count invalid date formats in {col} - should return 0 for properly formatted dates"
            })
            test_id_counter += 1
            
            # Future date check
            validations.append({
                "test_id": f"TC{test_id_counter:03d}",
                "query": f"SELECT COUNT(*) as future_dates FROM data_table WHERE {col} > current_date",
                "description": f"Count future dates in {col} - may need review depending on business rules"
            })
            test_id_counter += 1
        
        # 4. Phone/Contact columns
        if any(keyword in col_lower for keyword in ['phone', 'contact', 'mobile', 'tel']):
            validations.append({
                "test_id": f"TC{test_id_counter:03d}",
                "query": f"SELECT COUNT(*) as invalid_phones FROM data_table WHERE {col} IS NOT NULL AND (LENGTH({col}) < 7 OR LENGTH({col}) > 15)",
                "description": f"Count invalid phone numbers in {col} - should return 0 for properly formatted phones"
            })
            test_id_counter += 1
        
        # 5. Email columns
        if any(keyword in col_lower for keyword in ['email', 'mail']):
            validations.append({
                "test_id": f"TC{test_id_counter:03d}",
                "query": f"SELECT COUNT(*) as invalid_emails FROM data_table WHERE {col} IS NOT NULL AND {col} NOT LIKE '%@%'",
                "description": f"Count invalid email formats in {col} - should return 0 for valid emails"
            })
            test_id_counter += 1
        
        # 6. Name columns
        if any(keyword in col_lower for keyword in ['name', 'title']):
            validations.append({
                "test_id": f"TC{test_id_counter:03d}",
                "query": f"SELECT COUNT(*) as invalid_names FROM data_table WHERE {col} IS NOT NULL AND LENGTH({col}) < 2",
                "description": f"Count too-short names in {col} - should return 0 for valid names"
            })
            test_id_counter += 1
        
        # 7. Numeric columns (weight, height, age, amount, etc.)
        if 'int' in data_type or 'float' in data_type:
            # Determine reasonable ranges based on column name
            if any(keyword in col_lower for keyword in ['weight', 'mass']):
                min_val, max_val = 20, 300
            elif any(keyword in col_lower for keyword in ['height', 'length']):
                min_val, max_val = 100, 250
            elif any(keyword in col_lower for keyword in ['age']):
                min_val, max_val = 0, 120
            elif any(keyword in col_lower for keyword in ['price', 'cost', 'amount', 'salary']):
                min_val, max_val = 0, 1000000
            else:
                # Generic numeric validation
                min_val, max_val = -999999, 999999
            
            validations.append({
                "test_id": f"TC{test_id_counter:03d}",
                "query": f"SELECT COUNT(*) as out_of_range FROM data_table WHERE {col} IS NOT NULL AND ({col} < {min_val} OR {col} > {max_val})",
                "description": f"Count out-of-range values in {col} (range: {min_val}-{max_val}) - should return 0 for valid data"
            })
            test_id_counter += 1
        
        # 8. Text columns - check for unexpected characters or patterns
        if 'object' in data_type and not any(keyword in col_lower for keyword in ['date', 'time']):
            validations.append({
                "test_id": f"TC{test_id_counter:03d}",
                "query": f"SELECT COUNT(*) as empty_strings FROM data_table WHERE {col} IS NOT NULL AND LENGTH(TRIM({col})) = 0",
                "description": f"Count empty strings in {col} - should return 0 for valid text data"
            })
            test_id_counter += 1
    
    # 9. Cross-column validations (if applicable)
    date_columns = [col for col in columns if any(keyword in col.lower() for keyword in ['date', 'time'])]
    if len(date_columns) >= 2:
        # Check for logical date ordering (e.g., birth_date < visit_date)
        for i in range(len(date_columns) - 1):
            validations.append({
                "test_id": f"TC{test_id_counter:03d}",
                "query": f"SELECT COUNT(*) as date_order_issues FROM data_table WHERE {date_columns[i]} > {date_columns[i+1]}",
                "description": f"Count records where {date_columns[i]} is after {date_columns[i+1]} - may indicate data issues"
            })
            test_id_counter += 1
    
    return validations