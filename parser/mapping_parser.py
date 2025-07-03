import pandas as pd
from io import BytesIO

def parse_mapping_file(excel_file) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Parses the uploaded mapping spec Excel file using Shalini's latest structure.
    - Sheet 'table_metadata': high-level table info
    - Other sheets: field-level mapping rules

    Returns:
        metadata_df (DataFrame): table-level metadata
        rule_df (DataFrame): all rules combined across sheets
    """
    try:
        # --- Read all sheets ---
        excel_bytes = BytesIO(excel_file.read())
        sheets = pd.read_excel(excel_bytes, sheet_name=None)

        # Normalize sheet names
        normalized_sheets = {name.strip().lower(): df for name, df in sheets.items()}

        # --- Extract table metadata ---
        if 'table_metadata' not in normalized_sheets:
            raise ValueError("❌ Missing 'table_metadata' sheet.")

        metadata_df = normalized_sheets['table_metadata']
        metadata_df.columns = metadata_df.columns.str.strip()

        # --- Combine all rule sheets ---
        rule_sheets = {
            name: df for name, df in normalized_sheets.items()
            if name != 'table_metadata'
        }

        if not rule_sheets:
            raise ValueError("❌ No rule sheets found.")

        rule_df = pd.concat(rule_sheets.values(), ignore_index=True)
        rule_df.columns = rule_df.columns.str.strip()

        # Normalize column names: lowercase, replace spaces with underscores
        rule_df.columns = [col.strip().lower().replace(" ", "_") for col in rule_df.columns]

        # ❌ Strict check: fail if 'expected_field' is found
        if "expected_field" in rule_df.columns:
            raise ValueError("❌ Invalid column 'expected_field' found. Use 'expected_behavior' instead.")

        # ✅ Debug: Print final column list
        print("✅ Final columns in rule_df:", rule_df.columns.tolist())

        return metadata_df, rule_df

    except Exception as e:
        raise RuntimeError(f"❌ Failed to parse mapping file: {e}")