import streamlit as st
import pandas as pd
import base64
import os
from pathlib import Path
from parser.mapping_parser import parse_mapping_file
from processor.generate_test_artifacts import generate_test_artifacts
from database.db_utils import insert_project
from utils.file_utils import convert_df_to_download

def show():
    # --- Logo Display ---
    local_logo_path = "images/Full logo-KData.png"  # Note: using actual filename from images folder
    #fallback_logo_path = "C:/codes/teststreamlit/KData_logo/Full logo-KData.png"

    # Check local images folder first, then fallback path
    logo_path = None
    if os.path.exists(local_logo_path):
        logo_path = local_logo_path
    elif os.path.exists(fallback_logo_path):
        logo_path = fallback_logo_path
    
    # Only display logo if found in either location
    if logo_path:
        try:
            with open(logo_path, "rb") as f:
                encoded_logo = base64.b64encode(f.read()).decode()
            st.markdown(
                f"""
                <div style="display: flex; justify-content: flex-end;">
                    <img src="data:image/png;base64,{encoded_logo}" width="180">
                </div>
                """,
                unsafe_allow_html=True
            )
        except Exception:
            # Silently skip logo if there's any error reading it
            pass

    st.subheader(" Create Project ➕")

    # --- Reset session state only once ---
    if "project_setup_visited" not in st.session_state:
        st.session_state.clear()
        st.session_state["project_setup_visited"] = True

    # --- Project Info ---
    project_name = st.text_input("Project Name", key="project_name")
    project_desc = st.text_area("Project Description", key="project_desc")

    # --- File Upload Section ---
    st.divider()
    st.markdown("### 📂 Upload Required Files")

    # --- Template Downloads ---
    mapping_template_path = Path("templates/mapping_spec_template.xlsx")
    if mapping_template_path.exists():
        with open(mapping_template_path, "rb") as f:
            st.download_button(
                label="📥 Download Mapping Template",
                data=f,
                file_name="mapping_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.warning("⚠️ Mapping template not found.")

    brd_template_path = Path("templates/Business_Requirements_Template.docx")
    if brd_template_path.exists():
        with open(brd_template_path, "rb") as f:
            st.download_button(
                label="📥 Download BRD Template",
                data=f,
                file_name="brd_template.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
    else:
        st.warning("⚠️ BRD template not found.")

    # --- File Uploaders ---
    mapping_file = st.file_uploader("Upload Mapping Spec (Excel)", type=["xlsx"], key="mapping")
    brd_file = st.file_uploader("Upload Business Requirement Document (DOCX)", type=["docx"], key="brd")

    # --- Generate Artifacts ---
    if mapping_file:
        if st.button("Generate Test Artifacts"):
            if not project_name:
                st.warning("⚠️ Please enter a project name before generating.")
                return

            with st.spinner("🔄 Processing mapping file and generating test artifacts..."):
                try:
                    # Step 1: Create project folder
                    clean_project_name = project_name.replace(" ", "_")
                    project_folder = Path("uploaded_files") / clean_project_name
                    project_folder.mkdir(parents=True, exist_ok=True)

                    # Step 2: Save mapping file
                    mapping_filename = f"{clean_project_name}_mapping.xlsx"
                    mapping_path = project_folder / mapping_filename
                    with open(mapping_path, "wb") as f:
                        f.write(mapping_file.getbuffer())

                    # Step 3: Save BRD file (optional)
                    brd_filename = None
                    if brd_file:
                        brd_filename = f"{clean_project_name}_brd.docx"
                        brd_path = project_folder / brd_filename
                        with open(brd_path, "wb") as f:
                            f.write(brd_file.getbuffer())

                    # Step 4: Parse mapping spec
                    metadata_df, rule_df = parse_mapping_file(mapping_file)

                    # Step 5: Insert project record with file names only
                    try:
                        project_key = insert_project(
                            project_name,
                            project_desc,
                            str(project_folder / mapping_filename),
                            str(project_folder / brd_filename) if brd_filename else None
                        )
                        st.success(f" Project inserted with ID: {project_key}")
                    except Exception as db_err:
                        st.warning(f"⚠️ Project not saved to DB: {db_err}")
                        project_key = None

                    # Step 6: Generate artifacts
                    final_df = generate_test_artifacts(rule_df, metadata_df, project_key=project_key)

                    if final_df.empty:
                        st.warning("⚠️ No test cases generated. Check your mapping file.")
                    else:
                        st.success(f" {len(final_df)} test artifacts generated.")
                        #display_df = final_df.drop(columns=["test_script_sql"], errors="ignore")
                        #st.dataframe(display_df, use_container_width=True)

                        csv_data = convert_df_to_download(final_df)
                        #st.download_button("📥 Download Test Artifacts CSV", csv_data, file_name="test_artifacts.csv")

                except Exception as e:
                    st.error(f"❌ Generation failed: {e}")
    else:
        st.info(" Please upload your mapping file to continue.")
