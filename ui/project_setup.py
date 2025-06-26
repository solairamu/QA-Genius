import streamlit as st
import pandas as pd
from parser.mapping_parser import parse_mapping_file
from processor.generate_test_artifacts import generate_test_artifacts
from utils.file_utils import convert_df_to_download
from database.db_utils import insert_project  # Optional, for storing project info

def show():
    st.subheader("📁 Upload Project Files")

    # --- Step 1: Project Metadata ---
    project_name = st.text_input("📝 Project Name")
    project_desc = st.text_area("📄 Project Description")

    if not project_name:
        st.warning("⚠️ Please enter a project name to proceed.")
        return

    # --- Step 2: File Uploads ---
    st.divider()
    st.markdown("### 📂 Upload Required Files")

    mapping_file = st.file_uploader("Upload Mapping Spec (Excel)", type=["xlsx"], key="mapping")
    source_file = st.file_uploader("Upload Sample Source Data (optional)", type=["csv"], key="source")
    target_file = st.file_uploader("Upload Sample Target Data (optional)", type=["csv"], key="target")

    if mapping_file:
        st.success("✅ Mapping file uploaded successfully.")

        # --- Step 3: Generate Artifacts Button ---
        if st.button("🚀 Generate Test Artifacts"):
            with st.spinner("Processing mapping file and generating AI-based test cases and SQL scripts..."):

                try:
                    # Parse mapping spec
                    metadata_df, rule_df = parse_mapping_file(mapping_file)

                    # Optional: Insert project metadata into DB
                    try:
                        project_id = insert_project(project_name, project_desc)
                        st.info("📌 Project metadata saved.")
                    except Exception as db_err:
                        st.warning(f"⚠️ Project info not saved to DB: {db_err}")

                    # Generate test cases + SQL
                    final_df = generate_test_artifacts(rule_df, project_id=project_id)


                    st.success("✅ All test artifacts generated successfully!")

                    # Show preview
                    st.markdown("### ✅ Preview Generated Artifacts")
                    st.dataframe(final_df, use_container_width=True)

                    # Download button
                    st.download_button(
                        label="⬇️ Download All Test Artifacts (CSV)",
                        data=convert_df_to_download(final_df),
                        file_name=f"{project_name}_test_artifacts.csv",
                        mime="text/csv"
                    )

                except Exception as e:
                    st.error(f"❌ Error during generation: {e}")
    else:
        st.info("📤 Please upload your mapping file to begin.")
