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

# --- Main Artifact Generator ---
def generate_test_artifacts(rule_df: pd.DataFrame, project_key: int = None) -> pd.DataFrame:
    """
    Generate test cases + SQL scripts using LLM with progress bar & cancel button.
    Final version aligned with simplified DB schema — no execution_date or expected_field.
    """
    test_case_counter = 1
    artifact_rows = []
    total_rows = len(rule_df)

    st.info(f"Generating {total_rows} test artifacts")
    progress = st.progress(0, text="Starting...")
    stop_placeholder = st.empty()
    stop_button = stop_placeholder.button("Stop Generation")

    # Normalize column names for reliable access
    rule_df.columns = [col.strip().lower().replace(" ", "_") for col in rule_df.columns]

    # 🛡️ Fallback rename if legacy column is used
    if "expected_field" in rule_df.columns and "expected_behavior" not in rule_df.columns:
        rule_df.rename(columns={"expected_field": "expected_behavior"}, inplace=True)

    # ✅ Show columns for debugging
    #st.write("📊 Available columns in rule_df:", rule_df.columns.tolist())

    for idx, (_, row) in enumerate(rule_df.iterrows()):
        if stop_button or st.session_state.get("stop_requested", False):
            st.warning("⚠️ Generation cancelled by user.")
            break

        try:
            field = str(row.get("target_column", "")).strip()
            rule_text = str(row.get("expected_behavior", "")).strip()
            table_name = str(row.get("target_table", "")).strip()
            join_condition = str(row.get("join_condition", "")).strip()

            if not field or not rule_text or not table_name:
                st.warning(f"⚠️ Missing required fields on row {idx + 1}, skipping.")
                continue

            # --- LLM Prompt Setup ---
            tc_prompt = PROMPT_TEMPLATES["test_case_template"].format(field=field, rule=rule_text)
            sql_prompt = PROMPT_TEMPLATES["sql_script_template"].format(
                table=table_name, field=field, rule=rule_text, join_condition=join_condition or "N/A"
            )

            # --- LLM Responses ---
            test_case_name = ask_llm(tc_prompt).strip()
            raw_sql = ask_llm(sql_prompt)
            cleaned_sql = clean_generated_sql(raw_sql)

            # --- Prepare Output Row ---
            test_case_id = f"TC-{test_case_counter:03}"
            requirement_id = f"BR-{test_case_counter:03}"
            description = f"{field} must satisfy the rule: {rule_text}"

            artifact = {
                "test_case_id": test_case_id,
                "test_case_name": test_case_name,
                "description": description,
                "table_name": table_name,
                "column_name": field,
                "test_category": row.get("test_category", "Accuracy"),
                "test_script_id": None,
                "test_script_sql": cleaned_sql,
                "requirement_id": requirement_id,
            }

            artifact_rows.append(artifact)

            # --- Optional DB Insert ---
            if project_key:
                insert_test_artifact(project_key, artifact)

            test_case_counter += 1
            progress.progress((idx + 1) / total_rows, text=f"Completed {idx + 1} of {total_rows}...")

        except Exception as e:
            st.error(f"❌ Error on row {idx + 1}: {e}")
            continue

    progress.empty()
    stop_placeholder.empty()
    st.success(f"Generation completed: {len(artifact_rows)} test artifacts created.")
    return pd.DataFrame(artifact_rows)