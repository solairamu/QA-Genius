import os
import pandas as pd
import pandera as pa
from pandera import Column, DataFrameSchema, Check

from core.db import fetch_validation_rules

# --- Build Schema from DB Rules ---
def get_validation_schema_from_db():
    schema = {}
    rows = fetch_validation_rules()  # Fetched from db.py

    for row in rows:
        col, dtype, rule = row["column_name"], eval(row["data_type"]), row["rule"]
        try:
            check = eval(f"Check.{rule}")
            schema[col] = Column(dtype, check, nullable=False)
        except Exception:
            schema[col] = Column(dtype, nullable=True)
    return schema

# --- Validate Data with Schema ---
def validate_data_with_rules(df: pd.DataFrame, output_dir: str) -> pd.DataFrame:
    schema_def = get_validation_schema_from_db()
    total = len(df)
    summary = []
    failed_records = []

    for col, rule in schema_def.items():
        if col not in df.columns:
            continue

        temp_schema = DataFrameSchema({col: rule})
        try:
            temp_schema.validate(df[[col]], lazy=True)
            passed, failed = total, 0
        except pa.errors.SchemaErrors as e:
            passed = total - len(e.failure_cases)
            failed = len(e.failure_cases)
            failed_records.append((col, e.failure_cases))
        except Exception:
            summary.append({
                "column": col,
                "rule": str(rule.checks),
                "passed": "N/A",
                "failed": "N/A",
                "accuracy": "Rule not applied"
            })
            continue

        summary.append({
            "column": col,
            "rule": str(rule.checks),
            "passed": passed,
            "failed": failed,
            "accuracy": round((passed / total) * 100, 2) if total else 0
        })

    # --- Save summary ---
    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(os.path.join(output_dir, "validation_rules_summary.csv"), index=False)

    if failed_records:
        all_failed = pd.concat([r[1] for r in failed_records], ignore_index=True)
        all_failed.to_csv(os.path.join(output_dir, "failed_rows.csv"), index=False)

    return summary_df
