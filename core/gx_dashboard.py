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
        total = int(df_overall['total records'].iloc[0])
        passed = int(df_overall['passed'].iloc[0])
        failed = int(df_overall['failed'].iloc[0])
        other = total - passed - failed

        fig_overall = px.pie(
            names=["Passed", "Failed", "Other"],
            values=[passed, failed, other],
            hole=0.4,
            title="Overall Validation"
        )
        fig_overall.update_traces(
            marker=dict(colors=["green", "red", "gray"]),
            textposition='inside',
            textinfo='percent+label'
        )
        st.plotly_chart(fig_overall, use_container_width=True)
    except Exception as e:
        st.warning(f"❌ Error loading overall chart: {e}")

    # 📊 Per-Dimension Pie Charts
    st.markdown("#### 🧪 Per-Dimension Pass Rate")
    dimension_cols = {
        "completeness (%)": "Completeness",
        "uniqueness (%)": "Uniqueness",
        "validity (%)": "Validity",
        "consistency (%)": "Consistency",
        "accuracy (%)": "Accuracy"
    }

    pie_cols = st.columns(5)
    for i, (col_key, display_name) in enumerate(dimension_cols.items()):
        col_key = col_key.lower()
        if col_key in df_overall.columns:
            try:
                score = float(df_overall[col_key].iloc[0])
                fail_score = max(0.0, 100 - score)
                fig = px.pie(
                    names=["Passed", "Failed"],
                    values=[score, fail_score],
                    hole=0.5,
                    title=display_name
                )
                fig.update_traces(
                    marker=dict(colors=["green", "red"]),
                    textposition='inside',
                    textinfo='percent+label'
                )
                fig.update_layout(margin=dict(t=40, b=20, l=0, r=0))
                pie_cols[i].plotly_chart(fig, use_container_width=True)
            except:
                pie_cols[i].info(f"{display_name} data not available")
        else:
            pie_cols[i].warning(f"Missing: {display_name}")

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