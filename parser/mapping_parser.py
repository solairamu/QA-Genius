import pandas as pd
from io import BytesIO

def parse_mapping_file(excel_file) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Parses the uploaded mapping spec Excel file with:
    - Sheet 'table_metadata' (contains high-level table info)
    - Other sheets = mapping rule specs (one or more)

    Returns:
        metadata_df (DataFrame): table-level metadata
        rule_df (DataFrame): all rules combined across sheets
    """
    try:
        # --- Read all sheets ---
        excel_bytes = BytesIO(excel_file.read())
        sheets = pd.read_excel(excel_bytes, sheet_name=None)

        # Normalize sheet names (in case of spaces or casing)
        normalized_sheets = {name.strip().lower(): df for name, df in sheets.items()}

        # --- Extract metadata sheet ---
        if 'table_metadata' not in normalized_sheets:
            raise ValueError("❌ Required sheet 'table_metadata' not found in the Excel file.")
        
        metadata_df = normalized_sheets['table_metadata']
        metadata_df.columns = metadata_df.columns.str.strip()

        # --- Extract all other sheets as rule definitions ---
        rule_sheets = {name: df for name, df in normalized_sheets.items() if name != 'table_metadata'}

        if not rule_sheets:
            raise ValueError("❌ No rule sheets found (must have at least one sheet besides 'table_metadata').")

        rule_df = pd.concat(rule_sheets.values(), ignore_index=True)
        rule_df.columns = rule_df.columns.str.strip()

        # --- Ensure required columns exist ---
        required_cols = [
            "Mapping ID", "Source Table", "Source Column", "Source Type",
            "Transformation Logic", "Target Table", "Target Column", "Target Type",
            "Join Condition", "Rule Type", "Expected Behavior", "Example Value",
            "Comments", "Is Mandatory", "Key Role"
        ]
        for col in required_cols:
            if col not in rule_df.columns:
                rule_df[col] = None  # Fill missing columns

        return metadata_df, rule_df

    except Exception as e:
        raise RuntimeError(f"❌ Failed to parse mapping file: {e}")
