import streamlit as st
import os
import pandas as pd

from core.db import insert_new_project, insert_file
from core.transformer import apply_transformations

# --- MAIN APP TAB (New Project) ---
def load_tab():
    st.markdown("## New Project")
    project_name = st.text_input("Project Name")
    project_description = st.text_area("Project Description", height=100)

    st.markdown("### Upload Project Files")
    src_files = st.file_uploader("\U0001F4E4 Upload Source Files (CSV/XLSX)", type=["csv", "xlsx"], accept_multiple_files=True)
    mapping_file = st.file_uploader("\U0001F5C2️ Upload Mapping Specification", type=["csv"])

    if st.button("Create Project"):
        if not project_name or not src_files or not mapping_file:
            st.error("❌ All fields are required.")
            return

        try:
            # --- Create Project Folders ---
            safe_name = project_name.replace(" ", "_")
            base_path = os.path.join("projects", safe_name)
            folders = {
                "source": os.path.join(base_path, "source"),
                "mapping": os.path.join(base_path, "mapping"),
                "artifacts": os.path.join(base_path, "artifacts")
            }
            for path in folders.values():
                os.makedirs(path, exist_ok=True)

            # --- DB: Insert Project Info ---
            project_id = insert_new_project(project_name, project_description)

            # --- Save Source Files ---
            for file in src_files:
                path = os.path.join(folders["source"], file.name)
                with open(path, "wb") as f:
                    f.write(file.read())
                insert_file(project_id, "source", file.name, path)

            # --- Save Mapping File ---
            mapping_path = os.path.join(folders["mapping"], mapping_file.name)
            with open(mapping_path, "wb") as f:
                f.write(mapping_file.read())
            insert_file(project_id, "mapping", mapping_file.name, mapping_path)

            # --- Apply Transformations ---
            mapping_df = pd.read_csv(mapping_path)
            src_file_path = os.path.join(folders["source"], src_files[0].name)
            df_src = pd.read_csv(src_file_path) if src_file_path.endswith(".csv") else pd.read_excel(src_file_path)
            df_mapped = apply_transformations(df_src, mapping_df)

            # --- Validation Metrics ---
            total = len(df_mapped)
            failed_rows = df_mapped[df_mapped.isnull().any(axis=1)]
            failed = len(failed_rows)
            passed = total - failed
            accuracy = (passed / total * 100) if total else 0.0

            # --- Save Results ---
            mapped_file = os.path.join(folders["artifacts"], "mapped_output.csv")
            summary_file = os.path.join(folders["artifacts"], "validation_summary.txt")
            failed_file = os.path.join(folders["artifacts"], "failed_rows.csv")
            rules_summary_file = os.path.join(folders["artifacts"], "validation_rules_summary.csv")

            df_mapped.to_csv(mapped_file, index=False)
            failed_rows.to_csv(failed_file, index=False)

            with open(summary_file, "w") as f:
                f.write(f"Project ID: {project_id}\n")
                f.write(f"Total Records: {total}\n")
                f.write(f"Passed: {passed}\n")
                f.write(f"Failed: {failed}\n")
                f.write(f"Accuracy: {accuracy:.2f}%\n")

            # --- Rule Compliance Summary ---
            summary_rows = []
            for col in df_mapped.columns:
                total_col = len(df_mapped)
                passed_col = df_mapped[col].notnull().sum()
                failed_col = total_col - passed_col
                acc_col = passed_col / total_col * 100 if total_col else 0
                summary_rows.append({"column": col, "passed": passed_col, "failed": failed_col, "accuracy": round(acc_col, 2)})
            pd.DataFrame(summary_rows).to_csv(rules_summary_file, index=False)

            st.success(f"✅ Project ID {project_id} created and mapped output generated.")

        except Exception as e:
            st.error(f"❌ Error: {e}")
