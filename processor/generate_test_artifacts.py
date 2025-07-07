import pandas as pd
from datetime import date
from llm.llm_wrapper import ask_llm
from processor.sql_cleaner import clean_generated_sql
from database.db_utils import insert_test_artifact
import yaml
from pathlib import Path
import streamlit as st
import json

# --- Load LLM Prompt Templates Once ---
with open(Path("llm/prompts/test_artifact_prompt.yaml"), "r", encoding="utf-8") as file:
    PROMPT_TEMPLATES = yaml.safe_load(file)

# --- Main Artifact Generator ---
def generate_test_artifacts(rule_df: pd.DataFrame, metadata_df: pd.DataFrame, project_key: int = None) -> pd.DataFrame:
    test_case_counter = 1
    artifact_rows = []
    total_rows = len(rule_df)

    st.info(f"Generating {total_rows} test artifacts")
    progress = st.progress(0, text="Starting...")
    stop_placeholder = st.empty()
    stop_button = stop_placeholder.button("Stop Generation")

    # Normalize columns
    rule_df.columns = [col.strip().lower().replace(" ", "_") for col in rule_df.columns]
    metadata_df.columns = [col.strip().lower().replace(" ", "_") for col in metadata_df.columns]

    # Build metadata block
    metadata_text = "\n".join(
        f"- {row['table_name']}: Primary Key = {row['primary_key_columns']}"
        for _, row in metadata_df.iterrows()
    )

    for idx, (_, row) in enumerate(rule_df.iterrows()):
        if stop_button or st.session_state.get("stop_requested", False):
            st.warning(" Generation cancelled by user.")
            break

        try:
            field = str(row.get("target_column", "")).strip()
            rule_text = str(row.get("expected_behavior", "")).strip()
            table_name = str(row.get("target_table", "")).strip()
            join_condition = str(row.get("join_condition", "")).strip()

            if not field or not rule_text or not table_name:
                continue

            rule_text = rule_text.replace("1. ", "").replace("2. ", "").strip()

            # --- Ask LLM for test case ---
            tc_prompt = PROMPT_TEMPLATES["test_case_template"].format(field=field, rule=rule_text)
            tc_response = ask_llm(tc_prompt, expect_json=True, fallback_field=field, fallback_rule=rule_text)

            try:
                tc_json = json.loads(tc_response)
                test_case_name = tc_json.get("test_case_name", f"Check {field}")
                description = tc_json.get("description", f"{field} must satisfy the rule: {rule_text}")
                test_category = tc_json.get("test_category", "Accuracy")
            except Exception as e:
                st.warning(f" Failed to parse test case JSON on row {idx + 1}: {e}\nLLM said: {tc_response}")
                test_case_name = f"Check {field}"
                description = f"{field} must satisfy the rule: {rule_text}"
                test_category = "Accuracy"

            # --- Ask LLM for SQL ---
            if join_condition and "=" in join_condition:
                sql_prompt = PROMPT_TEMPLATES["sql_script_template_with_join"].format(
                    table=table_name,
                    field=field,
                    rule=rule_text,
                    join_condition=join_condition,
                    table_metadata=metadata_text
                )
            else:
                sql_prompt = PROMPT_TEMPLATES["sql_script_template_simple"].format(
                    table=table_name,
                    field=field,
                    rule=rule_text
                )

            raw_sql = ask_llm(sql_prompt)
            cleaned_sql = clean_generated_sql(raw_sql)

            # --- Final artifact ---
            test_case_id = f"TC-{test_case_counter:03}"
            requirement_id = f"BR-{test_case_counter:03}"

            artifact = {
                "test_case_id": test_case_id,
                "test_case_name": test_case_name,
                "description": description,
                "table_name": table_name,
                "column_name": field,
                "test_category": test_category,
                "test_script_id": None,
                "test_script_sql": cleaned_sql,
                "requirement_id": requirement_id,
            }

            artifact_rows.append(artifact)

            if project_key:
                insert_test_artifact(project_key, artifact)

            test_case_counter += 1
            progress.progress((idx + 1) / total_rows, text=f"Completed {idx + 1} of {total_rows}...")

        except Exception as e:
            st.error(f" Error on row {idx + 1}: {e}")
            continue

    progress.empty()
    stop_placeholder.empty()

    if not artifact_rows:
        st.warning(" No test cases were generated. Check your mapping file or LLM output.")
    else:
        st.success(f" Generation completed: {len(artifact_rows)} test artifacts created.")

    return pd.DataFrame(artifact_rows)