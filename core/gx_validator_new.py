import pandas as pd
import great_expectations as ge
from core.db import (
    update_validation_metrics,
    rule_exists,
    insert_validation_rule,
)

# --- Friendly Rule Name Mapping (25 total) ---
RULE_NAME_MAPPING = {
    # Completeness
    "expect_column_values_to_not_be_null": "No Missing Values",
    "expect_column_values_to_not_match_regex": "No Blank Strings",
    "expect_column_values_to_be_in_type_list": "Allowed Data Types",
    "expect_column_value_lengths_to_be_between": "Field Length Within Limits",
    "expect_column_values_to_be_of_type": "Expected Data Type",

    # Uniqueness
    "expect_column_values_to_be_unique": "Unique Values",
    "expect_column_most_common_value_to_be_in_set": "Most Frequent Value Check",
    "expect_column_values_to_match_regex": "Pattern Validity Check",
    
    # Validity
    "expect_column_values_to_match_regex": "Valid Character Pattern",
    "expect_column_values_to_not_match_regex": "No Disallowed Special Characters",
    
    # Consistency
    "expect_column_values_to_match_strftime_format": "Date Format Consistency",
    
    # Accuracy
    "expect_column_values_to_be_between": "Values Within Expected Range",
    "expect_column_values_to_be_in_set": "Expected Category Match",
    "expect_column_mean_to_be_between": "Mean Value Within Range",
    "expect_column_median_to_be_between": "Median Value Within Range"
}

# --- Rule Bank by Dimension (5 rules each) ---
RULES_BY_DIMENSION = {
    "completeness": [
        ("expect_column_values_to_not_be_null", {}),
        ("expect_column_values_to_not_match_regex", {"regex": r"^\s*$"}),
        ("expect_column_values_to_be_in_type_list", {"type_list": ["int", "float", "str"]}),
        ("expect_column_value_lengths_to_be_between", {"min_value": 1, "max_value": 255}),
        ("expect_column_values_to_be_of_type", {"type_": "str"})
    ],
    "uniqueness": [
        ("expect_column_values_to_be_unique", {}),
        ("expect_column_most_common_value_to_be_in_set", {"value_set": [None]}),
        ("expect_column_values_to_be_in_type_list", {"type_list": ["int", "float", "str"]}),
        ("expect_column_values_to_be_of_type", {"type_": "str"}),
        ("expect_column_values_to_match_regex", {"regex": r"^[^\s].*[^\s]$"})
    ],
    "validity": [
        ("expect_column_values_to_match_regex", {"regex": r"^[a-zA-Z0-9@.\s-]*$"}),
        ("expect_column_values_to_not_match_regex", {"regex": r".*[!#$%^&*()].*"}),
        ("expect_column_value_lengths_to_be_between", {"min_value": 1, "max_value": 255}),
        ("expect_column_values_to_be_in_type_list", {"type_list": ["int", "float", "str"]}),
        ("expect_column_values_to_be_of_type", {"type_": "str"})
    ],
    "consistency": [
        ("expect_column_values_to_match_strftime_format", {"strftime_format": "%Y-%m-%d"}),
        ("expect_column_values_to_be_in_type_list", {"type_list": ["int", "float", "str"]}),
        ("expect_column_values_to_match_regex", {"regex": r"^[^\s].*[^\s]$"}),
        ("expect_column_values_to_be_of_type", {"type_": "str"}),
        ("expect_column_most_common_value_to_be_in_set", {"value_set": [None]})
    ],
    "accuracy": [
        ("expect_column_values_to_be_between", {"min_value": 0, "max_value": 100}),
        ("expect_column_values_to_be_in_set", {"value_set": ["A", "B", "C", "D"]}),
        ("expect_column_values_to_be_of_type", {"type_": "int"}),
        ("expect_column_mean_to_be_between", {"min_value": 10, "max_value": 90}),
        ("expect_column_median_to_be_between", {"min_value": 10, "max_value": 90})
    ]
}

def create_ge_dataframe(df: pd.DataFrame):
    """
    Create a Great Expectations DataFrame object with version compatibility.
    """
    try:
        # Try modern GE API first (v0.15+)
        if hasattr(ge, 'dataset'):
            return ge.dataset.PandasDataset(df)
        # Try older API
        elif hasattr(ge, 'from_pandas'):
            return ge.from_pandas(df)
        # Fallback for even older versions
        else:
            # Import the PandasDataset class directly
            from great_expectations.dataset import PandasDataset
            return PandasDataset(df)
    except Exception as e:
        print(f"[WARNING] Could not create GE DataFrame: {e}")
        # Return None to trigger simplified validation
        return None

def simplified_validation(df: pd.DataFrame, project_id: int) -> pd.DataFrame:
    """
    Simplified validation without Great Expectations when GE is not available.
    """
    print("[INFO] Using simplified validation (Great Expectations not available)")
    summary = []
    
    for col in df.columns:
        # Basic completeness check
        null_count = df[col].isnull().sum()
        total = len(df)
        valid_count = total - null_count
        score = round((valid_count / total * 100), 2) if total > 0 else 0
        
        summary.append({
            "column_name": col,
            "rule_type": "basic_completeness_check",
            "friendly_rule_name": "Basic Completeness Check",
            "dimension": "completeness",
            "number_of_rows_passed": valid_count,
            "number_of_rows_failed": null_count,
            "total_rows_evaluated": total,
            "passed_score": score,
            "failed_score": round(100 - score, 2),
            "rule_application_status": "Basic Rule Applied"
        })
    
    return pd.DataFrame(summary)

# --- Validation Function ---
def validate_dataset(df: pd.DataFrame, project_id: int) -> pd.DataFrame:
    # Try to create GE DataFrame with version compatibility
    df_ge = create_ge_dataframe(df)
    
    # If GE is not available, use simplified validation
    if df_ge is None:
        return simplified_validation(df, project_id)
    
    summary = []

    for col in df.columns:
        for dimension, rules in RULES_BY_DIMENSION.items():
            for rule_type, kwargs in rules:
                try:
                    # Apply rule
                    getattr(df_ge, rule_type)(col, **kwargs)
                    validation_result = df_ge.validate()
                    result = validation_result["results"][-1]

                    # Parse results
                    unexpected_percent = result.get("result", {}).get("unexpected_percent", 0)
                    total = result.get("result", {}).get("element_count", len(df))
                    valid_count = int((100 - unexpected_percent) * total / 100)
                    invalid_count = int(unexpected_percent * total / 100)
                    score = round(100 - unexpected_percent, 2)

                    # Insert rule if not exists
                    if not rule_exists(col, rule_type, dimension, project_id):
                        insert_validation_rule(
                            project_id=project_id,
                            column_name=col,
                            rule_type=rule_type,
                            friendly_rule_name=RULE_NAME_MAPPING.get(rule_type, rule_type),
                            dimension=dimension
                        )

                    # Update metrics
                    update_validation_metrics(
                        column_name=col,
                        rule_type=rule_type,
                        dimension=dimension,
                        valid_count=valid_count,
                        invalid_count=invalid_count,
                        null_count=df[col].isnull().sum(),
                        total=total,
                        score=score,
                        project_id=project_id
                    )

                    summary.append({
                        "column_name": col,
                        "rule_type": rule_type,
                        "friendly_rule_name": RULE_NAME_MAPPING.get(rule_type, rule_type),
                        "dimension": dimension,
                        "number_of_rows_passed": valid_count,
                        "number_of_rows_failed": invalid_count,
                        "total_rows_evaluated": total,
                        "passed_score": score,
                        "failed_score": round(100 - score, 2),
                        "rule_application_status": "Rule Applied"
                    })

                except Exception as e:
                    print(f"[ERROR] Rule Failed → Column: {col}, Rule: {rule_type}, Dim: {dimension}, Error: {e}")
                    summary.append({
                        "column_name": col,
                        "rule_type": rule_type,
                        "friendly_rule_name": RULE_NAME_MAPPING.get(rule_type, rule_type),
                        "dimension": dimension,
                        "number_of_rows_passed": 0,
                        "number_of_rows_failed": len(df),
                        "total_rows_evaluated": len(df),
                        "passed_score": 0,
                        "failed_score": 100.0,
                        "rule_application_status": "Rule Not Applied"
                    })

    return pd.DataFrame(summary)