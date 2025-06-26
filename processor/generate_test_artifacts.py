import pandas as pd
from datetime import date
from llm.llm_wrapper import ask_llm
from processor.sql_cleaner import clean_generated_sql
from database.db_utils import insert_test_artifact
import yaml
from pathlib import Path
import streamlit as st

# --- Load LLM Prompt Templates Once ---
with open(Path("llm/prompts/test_artifact_prompt.yaml"), "r") as file:
    PROMPT_TEMPLATES = yaml.safe_load(file)

def generate_test_artifacts(rule_df: pd.DataFrame, project_id: int = None, max_rows: int = 50) -> pd.DataFrame:
    """
    Generate test cases + SQL scripts using LLM with progress bar & cancel button.
    """
    test_case_counter = 1
    artifact_rows = []

    total_rows = min(len(rule_df), max_rows)
    st.info(f"🧠 Generating up to {total_rows} test artifacts...")

    # Progress UI
    progress = st.progress(0, text="Starting...")
    stop_placeholder = st.empty()
    stop_button = stop_placeholder.button("🛑 Stop Generation")

    for idx, (_, row) in enumerate(rule_df.iterrows()):
        if idx >= max_rows:
            st.warning(f"⏹️ Max row limit ({max_rows}) reached. Stopping.")
            break

        # Check for stop
        if stop_button or st.session_state.get("stop_requested", False):
            st.warning("🛑 Generation cancelled by user.")
            break

        try:
            field = str(row.get("Target Column", "")).strip()
            rule_text = str(row.get("Expected Behavior", "")).strip()

            if not field or not rule_text:
                continue

            # --- Generate Prompts ---
            tc_prompt = PROMPT_TEMPLATES["test_case_template"].format(field=field, rule=rule_text)
            sql_prompt = PROMPT_TEMPLATES["sql_script_template"].format(field=field, rule=rule_text)

            # --- LLM Responses ---
            st.write(f"🔍 Generating test case for: `{field}`")
            tc_description = ask_llm(tc_prompt).strip()

            st.write(f"🧾 Generating SQL for: `{field}`")
            raw_sql = ask_llm(sql_prompt)
            cleaned_sql = clean_generated_sql(raw_sql)

            # --- Build Result Row ---
            artifact = {
                "Test Case ID": f"TC-{test_case_counter:03}",
                "Data Field": field,
                "Business Rule (Plain English)": tc_description,
                "SQL Script(s)": f"-- SQL-{test_case_counter:03}\n{cleaned_sql}",
                "Priority": "High",
                "Status": "Pending",
                "Execution Date": date.today().isoformat(),
                "Requirement ID": f"BR-{10000 + test_case_counter}"
            }

            artifact_rows.append(artifact)

            # --- Optional DB insert ---
            if project_id:
                insert_test_artifact(project_id, artifact)

            test_case_counter += 1

            # Update progress
            percent_complete = int((idx + 1) / total_rows * 100)
            progress.progress((idx + 1) / total_rows, text=f"✅ Completed {idx + 1} of {total_rows}...")

        except Exception as e:
            st.error(f"❌ Error on row {idx + 1}: {e}")
            continue

    progress.empty()
    stop_placeholder.empty()

    st.success(f"✅ Generation completed: {len(artifact_rows)} test artifacts created.")
    return pd.DataFrame(artifact_rows)
