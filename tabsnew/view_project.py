import streamlit as st
import os
import pandas as pd
import plotly.graph_objects as go
import shutil
import duckdb

from core.db import (
    get_all_projects, get_project_by_id,
    get_project_files, log_ai_query, delete_project_by_id
)
from core.llm_interface import generate_sql_query, generate_data_insight


# --- VALIDATION BAR CHART ---
def show_validation_bar(summary_csv_path):
    try:
        df_summary = pd.read_csv(summary_csv_path)
        df_summary = df_summary[df_summary["passed"] != "N/A"].copy()
        df_summary["accuracy"] = pd.to_numeric(df_summary["accuracy"], errors='coerce')

        fig = go.Figure()
        for _, row in df_summary.iterrows():
            color = "green" if row["accuracy"] >= 90 else "orange" if row["accuracy"] >= 70 else "red"
            fig.add_trace(go.Bar(
                x=[f"{row['column']}"],
                y=[row['accuracy']],
                text=f"{row['accuracy']}%",
                marker_color=color,
                textposition="auto"
            ))

        fig.update_layout(
            title="\U0001F4CA Column-wise Rule Accuracy",
            yaxis_title="Accuracy (%)",
            height=400,
            width=1000,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not generate validation accuracy chart: {e}")


# --- MIGRATION GAUGE ---
def show_migration_gauge(success_rate):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=success_rate,
        number={'suffix': "%"},
        title={'text': "Migration Success Rate"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "green"},
            'steps': [
                {'range': [0, 50], 'color': "red"},
                {'range': [50, 80], 'color': "orange"},
                {'range': [80, 100], 'color': "lightgreen"}
            ]
        }
    ))
    fig.update_layout(height=250, margin=dict(t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)


# --- MAIN VIEW PROJECT TAB ---
def load_tab():
    st.title("\U0001F4C1 View Projects")
    rows = get_all_projects()
    df = pd.DataFrame(rows)

    if df.empty:
        st.info("No projects available.")
        return

    df_sorted = df.sort_values(by="created_at", ascending=False)

    with st.expander("\U0001F4C2 View All Projects"):
        st.dataframe(df_sorted[["project_id", "project_name", "project_description", "created_at"]], use_container_width=True)

    st.markdown("### Select Project")
    project_names = df_sorted["project_name"].tolist()
    selected_project = st.selectbox("Choose a Project", project_names)

    if selected_project:
        project_row = df_sorted[df_sorted["project_name"] == selected_project].iloc[0]
        project_id = int(project_row["project_id"])
        st.session_state.selected_project_id = project_id

        with st.expander("⚠️ Delete Project"):
            st.markdown(f"**Project:** `{selected_project}`")
            delete_confirm = st.checkbox("I understand deleting this project is permanent.")
            if st.button("\U0001F5D1️ Delete This Project", type="primary", disabled=not delete_confirm):
                delete_project_by_id(project_id)
                safe_name = selected_project.replace(' ', '_')
                base_path = os.path.join("projects", safe_name)
                if os.path.exists(base_path):
                    shutil.rmtree(base_path)
                st.success(f"✅ Project '{selected_project}' has been deleted.")
                st.rerun()

        show_project_dashboard(project_id)


# --- DASHBOARD VIEW ---
def show_project_dashboard(project_id):
    project = get_project_by_id(project_id)
    files = get_project_files(project_id)

    safe_name = project['project_name'].replace(' ', '_')
    base_path = f"projects/{safe_name}"
    mapped_path = os.path.join(base_path, "artifacts", "mapped_output.csv")
    summary_txt = os.path.join(base_path, "artifacts", "validation_summary.txt")
    summary_csv = os.path.join(base_path, "artifacts", "validation_rules_summary.csv")
    failed_rows_csv = os.path.join(base_path, "artifacts", "failed_rows.csv")

    st.markdown(f"## \U0001F4CA Dashboard for Project: `{project['project_name']}`")
    st.markdown(f"**Description:** {project['project_description']}")
    st.markdown(f"**Created At:** {project['created_at']}")

    with st.expander("\U0001F4C4 View Mapped Output"):
        if os.path.exists(mapped_path):
            df_mapped = pd.read_csv(mapped_path)
            st.dataframe(df_mapped.head(10))
            with open(mapped_path, "rb") as f:
                st.download_button("⬇️ Download Mapped Output", f, file_name="mapped_output.csv", key="download_mapped")

    total_records, passed, failed = 0, 0, 0
    if os.path.exists(summary_txt):
        with open(summary_txt) as f:
            lines = f.readlines()
            for line in lines:
                if "Total Records" in line:
                    total_records = int(line.split(":")[-1])
                elif "Passed" in line:
                    passed = int(line.split(":")[-1])
                elif "Failed" in line:
                    failed = int(line.split(":")[-1])

    partial = total_records - (passed + failed)
    unmapped_count = 0
    if os.path.exists(failed_rows_csv):
        df_failed = pd.read_csv(failed_rows_csv)
        unmapped_count = df_failed.isnull().sum().sum()

    success_rate = (passed / total_records * 100) if total_records else 0
    fail_rate = (failed / total_records * 100) if total_records else 0
    partial_rate = (partial / total_records * 100) if total_records else 0

    st.subheader(" Migration Health & Record Summary")
    colA, colB = st.columns([2, 3])
    with colA:
        show_migration_gauge(success_rate)
    with colB:
        st.markdown("#### Metrics Overview")
        col1, col2, col3 = st.columns(3)
        col1.metric("✅ Passed", f"{success_rate:.1f}%")
        col2.metric("❌ Failed", f"{fail_rate:.1f}%")
        col3.metric("🔁 Partial", f"{partial_rate:.1f}%")
        col4, col5, col6 = st.columns(3)
        col4.metric("📦 Total Source", total_records)
        col5.metric("📤 Migrated", passed)
        col6.metric("🧩 Unmapped Fields", unmapped_count)

    st.subheader("Rule Compliance Overview")
    if os.path.exists(summary_csv):
        df_summary = pd.read_csv(summary_csv)
        st.dataframe(df_summary)
        show_validation_bar(summary_csv)

    st.subheader("Data Mapping Summary")
    mapping_file_path = next((f['file_path'] for f in files if f['file_type'] == 'mapping'), None)
    if mapping_file_path and os.path.exists(mapping_file_path):
        df_map = pd.read_csv(mapping_file_path)
        status_col = df_map["source"].apply(lambda x: "Mapped" if pd.notnull(x) else "Unmapped")
        df_map["status"] = status_col
        show_all = st.checkbox("Show Only Unmapped or Skipped Fields")
        if show_all:
            df_map = df_map[df_map["status"] != "Mapped"]
        st.dataframe(df_map[["source", "target", "transformation_code", "status"]])

    st.subheader("Priority Issues & Alerts")
    alert1, alert2, alert3, alert4 = st.columns(4)
    alert1.error("🔴 Unmapped Critical Fields")
    alert2.warning("⚠️ Rules Failed in Compliance")
    alert3.warning("⚠️ Data Gaps Detected")
    alert4.warning("⏳ Long Running Migration")

    st.markdown("""<div style='border: 2px solid #4CAF50; border-radius: 10px; padding: 15px; margin-top: 20px; background-color: #f9fff9;'>
        <h4>🤖 Ask QA Genius</h4>
        <p>Type any question about this project data (e.g. \"Show users under 15\")</p>
    </div>""", unsafe_allow_html=True)

    st.subheader("🤖 Ask QA Genius")
    ai_mode = st.radio("Select AI Mode", ["Test Case to SQL", "Data Insights"], horizontal=True)
    question = st.text_input("Enter your question")

    if st.button("Run QA Genius") and question.strip():
        with st.spinner("Preparing your AI response..."):
            df_full = pd.read_csv(mapped_path) if os.path.exists(mapped_path) else pd.DataFrame()
            table_schema = ", ".join([f"{col} ({dtype})" for col, dtype in zip(df_full.columns, df_full.dtypes)])
            response = ""

            try:
                if ai_mode == "Test Case to SQL":
                    raw_sql = generate_sql_query(table_schema, question)

                    # DEBUG: View raw SQL returned
                    #st.markdown("##### 🧾 Raw SQL Returned by AI")
                   # st.code(raw_sql)

                    # Skip fallback if the query is valid
                    if raw_sql.lower().startswith("error") or "syntax error" in raw_sql.lower():
                        st.error("⚠️ The AI couldn't generate a valid SQL query. Using fallback query instead.")
                        raw_sql = "SELECT * FROM data_table LIMIT 10"
                        st.warning("⚠️ Using fallback SQL query.")

                    try:
                        con = duckdb.connect()
                        con.register("data_table", df_full)
                        query_result = con.execute(raw_sql).fetchdf()

                        st.markdown("#### 🧠 AI-Generated SQL Query")
                        st.code(raw_sql, language="sql")
                        st.markdown("#### 📊 Query Result")
                        st.dataframe(query_result)
                    except Exception as sql_error:
                        st.warning("⚠️ Using fallback SQL query.")
                        try:
                            query_result = df_full.head(10)
                            st.markdown("#### 📊 Fallback Query Result")
                            st.dataframe(query_result)
                        except Exception as fallback_error:
                            st.error(f"❌ SQL Execution Error: {fallback_error}")
                        return

                    response = raw_sql

                else:
                    df_sample = df_full.head(10)
                    sample_data = df_sample.to_dict(orient="records")
                    response = generate_data_insight(table_schema, sample_data, question)

                

                log_ai_query(project_id, question, response)

            except Exception as e:
                st.error(f"❌ Failed to process request: {str(e)}")

    st.subheader("📥 Download Reports")
    colD1, colD2 = st.columns(2)
    with colD1:
        st.download_button("📄 Business Summary (PDF)", b"Business Summary PDF", file_name="business_summary.pdf", key="summary_pdf")
    with colD2:
        st.download_button("📊 Rule Compliance (Excel)", b"Compliance Report", file_name="rule_compliance.xlsx", key="compliance_excel")

    if os.path.exists(failed_rows_csv):
        with open(failed_rows_csv, "rb") as f:
            st.download_button("❌ Unmapped Fields (Excel)", f, file_name="unmapped_fields.xlsx", key="unmapped_excel")
