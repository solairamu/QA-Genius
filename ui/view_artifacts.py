import streamlit as st
import pandas as pd
from database.db_utils import get_connection

def show():
    st.subheader("📂 View Generated Artifacts")

    # --- Step 1: Load all projects ---
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT project_id, name FROM projects")  # ✅ FIXED: changed from id to project_id
            projects = cursor.fetchall()
            project_options = {f"{name} (ID: {pid})": pid for pid, name in projects}
        except Exception as e:
            st.error(f"❌ Failed to load projects: {e}")
            return
        finally:
            cursor.close()
            conn.close()
    else:
        st.error("❌ Could not connect to database.")
        return

    if not project_options:
        st.warning("⚠️ No projects found.")
        return

    # --- Step 2: Project dropdown ---
    selected_project_label = st.selectbox("📋 Select a Project", list(project_options.keys()))
    selected_project_id = project_options.get(selected_project_label)

    # --- Step 3: Load and display test cases for selected project ---
    if st.button("🔍 View Artifacts"):
        conn = get_connection()
        if conn:
            try:
                query = """
                    SELECT 
                        test_case_id,
                        data_field,
                        rule_description,
                        sql_script,
                        priority,
                        status,
                        execution_date,
                        requirement_id
                    FROM test_cases
                    WHERE project_id = %s
                """
                df = pd.read_sql(query, conn, params=(selected_project_id,))
                if df.empty:
                    st.info("ℹ️ No test artifacts found for this project.")
                else:
                    st.success(f"✅ {len(df)} test artifacts found.")
                    st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"❌ Failed to fetch test artifacts: {e}")
            finally:
                conn.close()
