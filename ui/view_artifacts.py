import streamlit as st
import pandas as pd
from database.db_utils import get_connection, delete_project_and_artifacts
from io import BytesIO

def show():
    st.subheader("View Artifacts")

    # --- Step 1: Load all projects ---
    conn = get_connection()
    if not conn:
        st.error("❌ Could not connect to database.")
        return

    try:
        project_df = pd.read_sql("SELECT project_key, name FROM projects", conn)
        if project_df.empty:
            st.warning("⚠️ No projects found.")
            return
    except Exception as e:
        st.error(f"❌ Failed to load projects: {e}")
        return
    finally:
        conn.close()

    # --- Select project ---
    selected_row = st.selectbox(
        " Select a Project",
        project_df.itertuples(index=False),
        format_func=lambda x: f"{x.name} (Project Key: {x.project_key})"
    )
    selected_project_key = selected_row.project_key
    #st.write("🔍 Selected Project Key:", selected_project_key)

    view_mode = st.radio(" View Mode", [" Table View", " Dropdown View"], horizontal=True)

    # --- Load test artifacts ---
    conn = get_connection()
    if not conn:
        st.error("❌ Could not connect to database.")
        return

    try:
        query = """
            SELECT 
                test_case_id,
                test_case_name,
                description,
                table_name,
                column_name,
                test_category,
                test_script_id,
                test_script_sql,
                requirement_id
            FROM test_cases
            WHERE project_key = %s
        """
        df = pd.read_sql(query, conn, params=(selected_project_key,))

        # --- Download + Delete Section ---
        col_dl, _, col_del = st.columns([1, 6, 1])

        with col_dl:
            if not df.empty:
                def convert_df_to_excel(df):
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='TestCases')
                    return output.getvalue()

                excel_data = convert_df_to_excel(df)
                st.download_button(
                    label=" Download as Excel",
                    data=excel_data,
                    file_name=f"test_cases_project_{selected_project_key}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        with col_del:
            if st.button("Delete Project", key="show_confirm_button"):
                st.session_state["show_delete_confirm"] = True

        if st.session_state.get("show_delete_confirm"):
            st.warning("⚠️ Are you sure you want to delete this entire project and all its artifacts?")
            confirm_col1, confirm_col2, confirm_col3 = st.columns([5, 1, 1])

            with confirm_col2:
                if st.button("✅ Yes, Delete", key="confirm_delete"):
                    success = delete_project_and_artifacts(selected_project_key)
                    if success:
                        st.success("✅ Project and artifacts deleted.")
                        st.session_state.clear()
                        st.rerun()
                    else:
                        st.error("❌ Failed to delete project.")

            with confirm_col3:
                if st.button("❌ Cancel", key="cancel_delete"):
                    st.session_state["show_delete_confirm"] = False
                    st.rerun()

        # --- Show results ---
        if df.empty:
            st.info("ℹ️ No test artifacts found for this project.")
        else:
            st.success(f"✅ {len(df)} test artifacts found.")
            if view_mode == " Table View":
                st.dataframe(df, use_container_width=True)
            else:
                for _, row in df.iterrows():
                    with st.expander(f"{row['test_case_id']} — {row['test_case_name']}"):
                        st.markdown("**🧾 Test Case Details:**")
                        st.markdown(f"- **Table Name:** `{row['table_name']}`")
                        st.markdown(f"- **Column Name:** `{row['column_name']}`")
                        st.markdown(f"- **Description:** {row['description']}")
                        #st.markdown(f"- **Test Category:** `{row['test_category']}`")
                        st.markdown(f"- **Test Script ID:** `{row['test_script_id']}`")
                        st.markdown("**🛠️ SQL Script:**")
                        st.code(row['test_script_sql'], language='sql')
                        st.markdown(f"- **Requirement ID:** `{row['requirement_id']}`")

    except Exception as e:
        st.error(f"❌ Failed to fetch test artifacts: {e}")
    finally:
        conn.close()