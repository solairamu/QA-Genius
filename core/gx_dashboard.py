import os
import pandas as pd
import plotly.express as px
import streamlit as st

def show_rule_compliance_section(base_path):
    def load_file(path_csv, path_xlsx):
        if os.path.exists(path_csv):
            return pd.read_csv(path_csv)
        elif os.path.exists(path_xlsx):
            return pd.read_excel(path_xlsx)
        st.warning(f"❌ File not found: {path_csv} or {path_xlsx}")
        return pd.DataFrame()

    summary_path_csv = os.path.join(base_path, "artifacts", "validation_rules_summary.csv")
    summary_path_xlsx = os.path.join(base_path, "artifacts", "validation_rules_summary.xlsx")
    overall_path_csv = os.path.join(base_path, "artifacts", "overall_validation_summary.csv")
    overall_path_xlsx = os.path.join(base_path, "artifacts", "overall_validation_summary.xlsx")

    df_rules = load_file(summary_path_csv, summary_path_xlsx)
    df_overall = load_file(overall_path_csv, overall_path_xlsx)

    df_rules.columns = df_rules.columns.str.strip().str.lower()
    df_overall.columns = df_overall.columns.str.strip().str.lower()

    if df_rules.empty or df_overall.empty:
        st.warning("⚠️ Validation summary files are missing or empty.")
        return

    # KPI Cards
    total_rules = len(df_rules)
    passed_rules = df_rules[df_rules["number_of_rows_failed"] == 0].shape[0]
    failed_rules = total_rules - passed_rules
    avg_score = df_rules["passed_score"].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Rules", total_rules)
    col2.metric("✅ Passed", passed_rules)
    col3.metric("❌ Failed", failed_rules)
    col4.metric("📊 Avg Score", f"{avg_score:.2f}%")

    # --- Bar Chart: Rule Compliance by Dimension (Only rule_type counted once)
    st.markdown("### 📊 Rule Compliance by Dimension")

    df_rules["Status"] = df_rules["number_of_rows_failed"].apply(lambda x: "Passed" if x == 0 else "Failed")

    # Keep only one entry per (dimension, rule_type) — pick the worst case (fail if any instance failed)
    latest_status = df_rules.sort_values("Status").drop_duplicates(subset=["dimension", "rule_type"], keep="first")

    dimension_counts = latest_status.groupby(["dimension", "Status"]).size().reset_index(name="Count")

    fig = px.bar(
        dimension_counts, x="dimension", y="Count", color="Status", barmode="group", text="Count",
        color_discrete_map={"Passed": "green", "Failed": "red"}
    )
    fig.update_traces(texttemplate='%{text}', textposition='auto')
    st.plotly_chart(fig, use_container_width=True)

    # --- Pie Charts Section ---
    st.markdown("### 🧩 Overall & Per-Dimension Validation Breakdown")

    # 🎯 Overall Validation Donut Chart
    st.markdown("#### 🎯 Overall Validation Status")
    try:
        # Check if this is migration data (has 'total records') or validation data (has 'dimension')
        if 'total records' in df_overall.columns or 'Total Records' in df_overall.columns:
            # This is migration data - handle the old way
            if 'total records' in df_overall.columns:
                total_col = 'total records'
            else:
                total_col = 'Total Records'
            
            total = int(df_overall[total_col].iloc[0])
            
            # Handle new and old field names for migration data
            complete_records = 0
            partial_records = 0
            empty_source_records = 0
            
            # Try new field names first, then fallback to old ones
            if 'passed' in df_overall.columns:
                complete_records = int(df_overall['passed'].iloc[0])
            elif 'Passed' in df_overall.columns:
                complete_records = int(df_overall['Passed'].iloc[0])
                
            if 'partial' in df_overall.columns:
                partial_records = int(df_overall['partial'].iloc[0])
            elif 'Partial' in df_overall.columns:
                partial_records = int(df_overall['Partial'].iloc[0])
                
            if 'empty source' in df_overall.columns:
                empty_source_records = int(df_overall['empty source'].iloc[0])
            elif 'Empty Source' in df_overall.columns:
                empty_source_records = int(df_overall['Empty Source'].iloc[0])
            elif 'failed' in df_overall.columns:
                # Fallback to old 'failed' field if new field not available
                empty_source_records = int(df_overall['failed'].iloc[0])
            elif 'Failed' in df_overall.columns:
                empty_source_records = int(df_overall['Failed'].iloc[0])

            # Create migration status chart
            fig_overall = px.pie(
                names=["Complete Records", "Partial Records", "Empty Source Records"],
                values=[complete_records, partial_records, empty_source_records],
                hole=0.4,
                title="Data Completeness Status",
                color_discrete_map={"Complete Records": "green", "Partial Records": "orange", "Empty Source Records": "lightcoral"}
            )
            fig_overall.update_traces(
                textposition='inside',
                textinfo='percent+label'
            )
            st.plotly_chart(fig_overall, use_container_width=True)
            
        elif 'dimension' in df_overall.columns:
            # This is validation dimension data - create a different chart
            # Calculate overall data quality score
            avg_scores = df_overall['avg_passed_score'].tolist()
            dimension_names = df_overall['dimension'].tolist()
            
            # Create a donut chart showing dimension scores
            fig_overall = px.pie(
                names=[f"{dim.capitalize()}: {score:.1f}%" for dim, score in zip(dimension_names, avg_scores)],
                values=avg_scores,
                hole=0.4,
                title="Data Quality Dimension Scores",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_overall.update_traces(
                textposition='inside',
                textinfo='label+percent'
            )
            st.plotly_chart(fig_overall, use_container_width=True)
            
            # Show overall quality score
            overall_quality = sum(avg_scores) / len(avg_scores)
            st.metric("Overall Data Quality Score", f"{overall_quality:.1f}%")
            
        else:
            st.warning("❌ Unrecognized overall validation data format")
            
    except Exception as e:
        st.warning(f"❌ Error loading overall chart: {e}")
        # Debug information
        st.write("Available columns:", df_overall.columns.tolist())
        st.write("Sample data:", df_overall.head())

    # 📊 Per-Dimension Pie Charts
    st.markdown("#### 🧪 Per-Dimension Pass Rate")
    
    # Debug section - show what rules actually exist
    if not df_rules.empty:
        with st.expander("🔍 Debug: Available Validation Rules"):
            st.write("**Dimensions found in validation data:**")
            available_dimensions = df_rules["dimension"].unique()
            st.write(available_dimensions)
            st.write("**Rule counts by dimension:**")
            dimension_counts = df_rules["dimension"].value_counts()
            st.write(dimension_counts)
            st.write("**Sample rules data:**")
            st.dataframe(df_rules[["column_name", "dimension", "rule_type", "passed_score"]].head(10))
    
    # Calculate dimension scores from the detailed rules data (more accurate)
    if not df_rules.empty:
        pie_cols = st.columns(5)
        dimensions = ["completeness", "uniqueness", "validity", "consistency", "accuracy"]
        
        for i, dimension in enumerate(dimensions):
            # Filter rules for this dimension
            dimension_rules = df_rules[df_rules["dimension"] == dimension]
            
            if not dimension_rules.empty:
                # Calculate average pass rate for this dimension
                avg_pass_rate = dimension_rules["passed_score"].mean()
                avg_fail_rate = 100.0 - avg_pass_rate
                
                # Create pie chart
                fig = px.pie(
                    names=["Passed", "Failed"],
                    values=[avg_pass_rate, avg_fail_rate],
                    hole=0.5,
                    title=dimension.capitalize()
                )
                fig.update_traces(
                    marker=dict(colors=["green", "red"]),
                    textposition='inside',
                    textinfo='percent+label'
                )
                fig.update_layout(margin=dict(t=40, b=20, l=0, r=0))
                pie_cols[i].plotly_chart(fig, use_container_width=True)
                
                # Show the actual percentage below the chart
                pie_cols[i].metric(f"{dimension.capitalize()} Score", f"{avg_pass_rate:.1f}%")
            else:
                pie_cols[i].info(f"No {dimension} rules found")
    else:
        st.warning("No detailed validation rules found for per-dimension analysis.")

    # --- Red Flag Summary
    st.markdown("### 🚨 Red Flag Summary (Failed Rows per Rule & Column)")
    df_failed = df_rules[df_rules["number_of_rows_failed"] > 0]
    available_dimensions = sorted(df_rules["dimension"].dropna().unique())
    selected_dimensions = st.multiselect("📊 Filter by Dimension", options=available_dimensions, default=available_dimensions)
    filtered_by_dimension = df_failed[df_failed["dimension"].isin(selected_dimensions)]

    available_rules = sorted(filtered_by_dimension["friendly_rule_name"].dropna().unique())
    selected_rules = st.multiselect("📋 Filter by Friendly Rule Name", options=available_rules, default=available_rules)
    filtered_df = filtered_by_dimension[filtered_by_dimension["friendly_rule_name"].isin(selected_rules)]

    fail_summary = filtered_df.groupby(["column_name", "friendly_rule_name"])["number_of_rows_failed"].sum().reset_index()
    fail_summary = fail_summary.sort_values(by="number_of_rows_failed", ascending=False)

    if fail_summary.empty:
        st.info("✅ No failed rules match your current filters.")
    else:
        fig = px.bar(
            fail_summary,
            x="number_of_rows_failed",
            y="column_name",
            color="friendly_rule_name",
            orientation="h",
            title="Failed Records by Column & Rule",
            text="number_of_rows_failed"
        )
        fig.update_layout(
            height=500,
            showlegend=True,
            yaxis_title="Column Name",
            xaxis_title="Failed Row Count"
        )
        fig.update_traces(texttemplate='%{text}', textposition="auto")
        st.plotly_chart(fig, use_container_width=True)

    # --- Top Failing Rules
    st.markdown("### Top Failing Rules")
    df_rules["score"] = df_rules["number_of_rows_failed"]
    top_failed = df_rules.sort_values(by="score", ascending=False).head(10)
    st.dataframe(top_failed[["column_name", "rule_type", "dimension",
                             "number_of_rows_failed", "total_rows_evaluated", "passed_score"]])