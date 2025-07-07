import streamlit as st
import pandas as pd
from parser.mapping_parser import parse_mapping_file
from processor.generate_test_artifacts import generate_test_artifacts
from utils.file_utils import convert_df_to_download
from database.db_utils import insert_project

def show():
    st.subheader(" Upload Project Files")

    # --- Reset session state only once ---
    if "project_setup_visited" not in st.session_state:
        st.session_state.clear()
        st.session_state["project_setup_visited"] = True

    # --- Project Info ---
    project_name = st.text_input("Project Name", key="project_name")
    project_desc = st.text_area("Project Description", key="project_desc")

    # --- File Upload ---
    st.divider()
    st.markdown("###  Upload Required File")
    mapping_file = st.file_uploader("Upload Mapping Spec (Excel)", type=["xlsx"], key="mapping")

    if mapping_file:
        if st.button("Generate Test Artifacts"):
            if not project_name:
                st.warning(" Please enter a project name before generating.")
                return

            with st.spinner("Processing mapping file and generating test artifacts..."):
                try:
                    #  Step 1: Parse mapping spec
                    metadata_df, rule_df = parse_mapping_file(mapping_file)

                    #  Step 2: Insert project once
                    try:
                        project_key = insert_project(project_name, project_desc)
                        st.success(f" Project inserted with ID: {project_key}")
                    except Exception as db_err:
                        st.warning(f"⚠️ Project not saved to DB: {db_err}")
                        project_key = None

                    #  Step 3: Generate test artifacts
                    final_df = generate_test_artifacts(rule_df, metadata_df, project_key=project_key)

                    if final_df.empty:
                        st.warning("⚠️ No test cases were generated. Check your mapping file.")
                    else:
                        st.success(f" {len(final_df)} test artifacts generated.")

                        #  Hide SQL script from main table view
                        display_df = final_df.drop(columns=["test_script_sql"], errors="ignore")
                        st.dataframe(display_df, use_container_width=True)

                        #  Optional CSV download
                        csv_data = convert_df_to_download(final_df)
                        st.download_button(" Download CSV", csv_data, file_name="test_artifacts.csv")

                except Exception as e:
                    st.error(f"❌ Generation failed: {e}")

    else:
        st.info(" Please upload your mapping file to continue.")