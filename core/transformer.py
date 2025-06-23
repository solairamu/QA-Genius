import pandas as pd
import numpy as np
import re
from datetime import datetime

def detect_column_mappings(mapping_df: pd.DataFrame) -> dict:
    """
    Dynamically detect column mappings based on common naming patterns.
    Returns a dictionary mapping standard names to actual column names.
    """
    columns = [col.lower().strip() for col in mapping_df.columns]
    column_map = {}
    
    # Source column variations
    source_patterns = ['source', 'sourcefield', 'source_field', 'src', 'from', 'input', 'original']
    for pattern in source_patterns:
        matches = [col for col in columns if pattern in col.lower()]
        if matches:
            # Find the actual column name (preserving original case)
            actual_col = next(orig_col for orig_col in mapping_df.columns 
                            if orig_col.lower().strip() == matches[0])
            column_map['source'] = actual_col
            break
    
    # Target column variations
    target_patterns = ['target', 'targetfield', 'target_field', 'tgt', 'to', 'output', 'destination', 'dest']
    for pattern in target_patterns:
        matches = [col for col in columns if pattern in col.lower()]
        if matches:
            actual_col = next(orig_col for orig_col in mapping_df.columns 
                            if orig_col.lower().strip() == matches[0])
            column_map['target'] = actual_col
            break
    
    # Transformation column variations
    transform_patterns = ['transformation', 'transform', 'transformation_code', 'transform_code', 
                         'code', 'logic', 'rule', 'formula', 'expression']
    for pattern in transform_patterns:
        matches = [col for col in columns if pattern in col.lower()]
        if matches:
            actual_col = next(orig_col for orig_col in mapping_df.columns 
                            if orig_col.lower().strip() == matches[0])
            column_map['transformation_code'] = actual_col
            break
    
    # Required column variations
    required_patterns = ['required', 'mandatory', 'req', 'must', 'essential']
    for pattern in required_patterns:
        matches = [col for col in columns if pattern in col.lower()]
        if matches:
            actual_col = next(orig_col for orig_col in mapping_df.columns 
                            if orig_col.lower().strip() == matches[0])
            column_map['required'] = actual_col
            break
    
    # Direct map column variations
    direct_patterns = ['direct', 'direct_map', 'directmap', 'copy', 'direct_copy']
    for pattern in direct_patterns:
        matches = [col for col in columns if pattern in col.lower()]
        if matches:
            actual_col = next(orig_col for orig_col in mapping_df.columns 
                            if orig_col.lower().strip() == matches[0])
            column_map['direct_map'] = actual_col
            break
    
    # Default value column variations
    default_patterns = ['default', 'default_value', 'defaultvalue', 'fallback', 'backup']
    for pattern in default_patterns:
        matches = [col for col in columns if pattern in col.lower()]
        if matches:
            actual_col = next(orig_col for orig_col in mapping_df.columns 
                            if orig_col.lower().strip() == matches[0])
            column_map['default_value'] = actual_col
            break
    
    return column_map

def apply_transformations(df: pd.DataFrame, mapping_df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.copy()
    
    # Dynamically detect column mappings
    col_map = detect_column_mappings(mapping_df)
    
    print(f"🔍 Detected column mappings: {col_map}")
    
    # Check if we found the essential columns
    if 'source' not in col_map or 'target' not in col_map:
        print("❌ Could not detect source and target columns in mapping file.")
        print("Available columns:", mapping_df.columns.tolist())
        print("Please ensure your mapping file has columns that contain 'source' and 'target' (or similar variations)")
        return df

    # Define reusable helper functions for transformation logic
    def cap_value(x, cap=10000):
        return np.minimum(x, cap)

    def concat(a, b, sep=' '):
        return a.astype(str) + sep + b.astype(str)

    def years_since(date_series):
        today = datetime.today()
        return pd.to_datetime(date_series, errors='coerce').apply(lambda d: today.year - d.year if pd.notnull(d) else None)

    for _, row in mapping_df.iterrows():
        # Use detected column names
        src = row[col_map['source']]
        tgt = row[col_map['target']]
        
        # Get optional columns with fallbacks
        required = str(row.get(col_map.get('required', ''), "")).strip().lower()
        direct = str(row.get(col_map.get('direct_map', ''), "")).strip().lower()
        default = str(row.get(col_map.get('default_value', ''), "")).strip()
        logic_code = str(row.get(col_map.get('transformation_code', ''), "")).strip()

        print(f"\n🔄 Processing: {src} → {tgt}")

        if src not in df.columns and logic_code == "":
            print(f"⛔ Skipped: '{src}' not found and no transformation provided.")
            continue

        # Step 1: Base copy if direct map
        if src in df.columns:
            renamed[tgt] = df[src]
            print(f"📄 Base copied: {src} → {tgt}")

        # Step 2: Apply transformation code if present
        if logic_code and logic_code.lower() not in ["none", "n/a", "", "null"]:
            try:
                local_env = {
                    "df": df,
                    "renamed": renamed,
                    "pd": pd,
                    "np": np,
                    "re": re,
                    "datetime": datetime,
                    "today": datetime.today(),
                    "cap_value": cap_value,
                    "concat": concat,
                    "years_since": years_since
                }
                result = eval(logic_code, {}, local_env)
                renamed[tgt] = result
                print(f"🛠️ Transformation applied to '{tgt}' using logic: {logic_code}")
            except Exception as e:
                print(f"⚠️ Error applying transformation for '{tgt}': {e}")

        # Step 3: Apply default value if defined
        if default.lower() not in ["", "n/a", "none", "null"]:
            renamed[tgt] = renamed[tgt].fillna(default)
            print(f"🧩 Default value applied to '{tgt}': {default}")

        # Step 4: Required field check
        if required == "yes" and renamed[tgt].isnull().any():
            print(f"❗ Warning: Missing required values in '{tgt}'")

    # Step 5: Return only mapped target columns
    target_cols = mapping_df[col_map['target']].dropna().unique().tolist()
    return renamed[target_cols]