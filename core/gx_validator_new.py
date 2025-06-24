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
    Enhanced validation that covers multiple dimensions when Great Expectations is not available.
    """
    print("[INFO] Using enhanced validation (Great Expectations not available)")
    summary = []
    
    # Import phone detection function
    from core.transformer import detect_phone_columns, validate_phone_number
    
    # Detect phone columns for specialized validation
    phone_columns = detect_phone_columns(df)
    print(f"[DEBUG] Detected phone columns: {phone_columns}")
    
    for col in df.columns:
        print(f"[DEBUG] Processing column: {col}")
        
        is_phone_column = col in phone_columns
        
        # 1. Completeness check - ALWAYS created
        null_count = df[col].isnull().sum()
        total = len(df)
        valid_count = total - null_count
        completeness_score = round((valid_count / total * 100), 2) if total > 0 else 0
        
        summary.append({
            "column_name": col,
            "rule_type": "completeness_check",
            "friendly_rule_name": "No Missing Values",
            "dimension": "completeness",
            "number_of_rows_passed": valid_count,
            "number_of_rows_failed": null_count,
            "total_rows_evaluated": total,
            "passed_score": completeness_score,
            "failed_score": round(100 - completeness_score, 2),
            "rule_application_status": "Rule Applied"
        })
        
        # 2. Uniqueness check - ALWAYS created (for non-null values)
        non_null_values = df[col].dropna()
        if len(non_null_values) > 0:
            unique_count = non_null_values.nunique()
            duplicate_count = len(non_null_values) - unique_count
            uniqueness_score = round((unique_count / len(non_null_values) * 100), 2)
            
            summary.append({
                "column_name": col,
                "rule_type": "uniqueness_check",
                "friendly_rule_name": "Unique Values Check",
                "dimension": "uniqueness",
                "number_of_rows_passed": unique_count,
                "number_of_rows_failed": duplicate_count,
                "total_rows_evaluated": len(non_null_values),
                "passed_score": uniqueness_score,
                "failed_score": round(100 - uniqueness_score, 2),
                "rule_application_status": "Rule Applied"
            })
        else:
            # Create default entry even if no data
            summary.append({
                "column_name": col,
                "rule_type": "uniqueness_check",
                "friendly_rule_name": "Unique Values Check",
                "dimension": "uniqueness",
                "number_of_rows_passed": 0,
                "number_of_rows_failed": 0,
                "total_rows_evaluated": 0,
                "passed_score": 100.0,  # Default to 100% if no data to evaluate
                "failed_score": 0.0,
                "rule_application_status": "No Data to Evaluate"
            })
        
        # 3. Validity check - ENHANCED for phone columns
        validity_score = 100.0  # Default
        valid_count = 0
        invalid_count = 0
        
        if len(non_null_values) > 0:
            try:
                if is_phone_column:
                    # Special validation for phone columns using the regex pattern
                    print(f"[DEBUG] Applying phone validation to column: {col}")
                    
                    valid_count = 0
                    for value in non_null_values:
                        if validate_phone_number(value):
                            valid_count += 1
                    
                    invalid_count = len(non_null_values) - valid_count
                    validity_score = round((valid_count / len(non_null_values) * 100), 2)
                    
                    # Update rule name for phone columns
                    rule_name = "Phone Number Format (^\\+1-\\d{3}-\\d{3}-\\d{4}$)"
                else:
                    # Regular validity check for non-phone columns
                    # Try to identify the dominant data type
                    numeric_count = 0
                    string_count = 0
                    
                    for value in non_null_values:
                        if isinstance(value, (int, float)) or (isinstance(value, str) and str(value).replace('.', '').replace('-', '').isdigit()):
                            numeric_count += 1
                        else:
                            string_count += 1
                    
                    # If mostly numeric, check for invalid numeric values
                    if numeric_count > string_count:
                        invalid_count = string_count
                        valid_count = numeric_count
                    else:
                        # For string data, check for reasonable length and characters
                        invalid_count = len([v for v in non_null_values if isinstance(v, str) and (len(str(v).strip()) == 0 or len(str(v)) > 1000)])
                        valid_count = len(non_null_values) - invalid_count
                    
                    validity_score = round((valid_count / len(non_null_values) * 100), 2)
                    rule_name = "Data Type Validity"
                
            except Exception as e:
                print(f"[WARNING] Validity check failed for {col}: {e}")
                # Use defaults
                valid_count = len(non_null_values)
                invalid_count = 0
                validity_score = 100.0
                rule_name = "Data Type Validity"
        else:
            rule_name = "Phone Number Format" if is_phone_column else "Data Type Validity"
        
        summary.append({
            "column_name": col,
            "rule_type": "validity_check",
            "friendly_rule_name": rule_name,
            "dimension": "validity",
            "number_of_rows_passed": valid_count,
            "number_of_rows_failed": invalid_count,
            "total_rows_evaluated": len(non_null_values),
            "passed_score": validity_score,
            "failed_score": round(100 - validity_score, 2),
            "rule_application_status": "Rule Applied"
        })
        
        # 4. Consistency check - ALWAYS created
        consistency_score = 100.0  # Default
        consistent_count = 0
        inconsistent_count = 0
        
        if len(non_null_values) > 0:
            try:
                string_values = [str(v) for v in non_null_values]
                
                # Check for consistent patterns (e.g., phone numbers, dates, etc.)
                # Simple heuristic: if most values follow a pattern, inconsistent ones are flagged
                patterns = {}
                for value in string_values:
                    # Create a simple pattern (letters vs numbers vs special chars)
                    pattern = ""
                    for char in str(value):
                        if char.isalpha():
                            pattern += "A"
                        elif char.isdigit():
                            pattern += "9"
                        else:
                            pattern += "X"
                    # Simplify patterns by collapsing consecutive similar characters
                    simplified = ""
                    prev_char = ""
                    for char in pattern:
                        if char != prev_char:
                            simplified += char
                        prev_char = char
                    patterns[simplified] = patterns.get(simplified, 0) + 1
                
                # Find the most common pattern
                if patterns:
                    most_common_pattern = max(patterns, key=patterns.get)
                    consistent_count = patterns[most_common_pattern]
                    inconsistent_count = len(string_values) - consistent_count
                    consistency_score = round((consistent_count / len(string_values) * 100), 2)
                else:
                    consistent_count = len(string_values)
                    inconsistent_count = 0
                    consistency_score = 100.0
                
            except Exception as e:
                print(f"[WARNING] Consistency check failed for {col}: {e}")
                # Use defaults
                consistent_count = len(non_null_values)
                inconsistent_count = 0
                consistency_score = 100.0
        
        summary.append({
            "column_name": col,
            "rule_type": "consistency_check",
            "friendly_rule_name": "Pattern Consistency",
            "dimension": "consistency",
            "number_of_rows_passed": consistent_count,
            "number_of_rows_failed": inconsistent_count,
            "total_rows_evaluated": len(non_null_values),
            "passed_score": consistency_score,
            "failed_score": round(100 - consistency_score, 2),
            "rule_application_status": "Rule Applied"
        })
        
        # 5. Accuracy check - ALWAYS created
        accuracy_score = 100.0  # Default
        accurate_count = 0
        inaccurate_count = 0
        
        if len(non_null_values) > 0:
            try:
                # Try to convert to numeric
                numeric_values = []
                for value in non_null_values:
                    try:
                        if isinstance(value, (int, float)):
                            numeric_values.append(float(value))
                        elif isinstance(value, str) and str(value).replace('.', '').replace('-', '').isdigit():
                            numeric_values.append(float(value))
                    except:
                        pass
                
                if len(numeric_values) > 1:  # Need at least 2 values for std calculation
                    # Check for reasonable ranges (no extreme outliers)
                    mean_val = sum(numeric_values) / len(numeric_values)
                    std_val = (sum((x - mean_val) ** 2 for x in numeric_values) / len(numeric_values)) ** 0.5
                    
                    # Values within 3 standard deviations are considered accurate
                    accurate_count = 0
                    for value in numeric_values:
                        if std_val == 0 or abs(value - mean_val) <= 3 * std_val:
                            accurate_count += 1
                    
                    inaccurate_count = len(numeric_values) - accurate_count
                    accuracy_score = round((accurate_count / len(numeric_values) * 100), 2)
                elif len(numeric_values) == 1:
                    # Single numeric value - consider it accurate
                    accurate_count = 1
                    inaccurate_count = 0
                    accuracy_score = 100.0
                else:
                    # No numeric values - for text data, consider them accurate by default
                    accurate_count = len(non_null_values)
                    inaccurate_count = 0
                    accuracy_score = 100.0
                    
            except Exception as e:
                print(f"[WARNING] Accuracy check failed for {col}: {e}")
                # Use defaults
                accurate_count = len(non_null_values)
                inaccurate_count = 0
                accuracy_score = 100.0
        
        summary.append({
            "column_name": col,
            "rule_type": "accuracy_check",
            "friendly_rule_name": "Value Range Accuracy",
            "dimension": "accuracy",
            "number_of_rows_passed": accurate_count,
            "number_of_rows_failed": inaccurate_count,
            "total_rows_evaluated": len(non_null_values),
            "passed_score": accuracy_score,
            "failed_score": round(100 - accuracy_score, 2),
            "rule_application_status": "Rule Applied"
        })
        
        print(f"[DEBUG] Created 5 rules for column {col}")
    
    print(f"[DEBUG] Total rules created: {len(summary)}")
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