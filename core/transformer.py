import pandas as pd
import re

def apply_transformations(df: pd.DataFrame, mapping_df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.copy()

    for _, row in mapping_df.iterrows():
        src = row["source"]
        tgt = row["target"]
        required = str(row.get("required", "")).strip().lower()
        direct = str(row.get("direct_map", "")).strip().lower()
        default = str(row.get("default_value", "")).strip()
        logic_code = str(row.get("transformation_code", "")).strip()

        print(f"\n🔄 Processing: {src} → {tgt}")

        if src not in df.columns and logic_code == "":
            print(f"⛔ Skipped: '{src}' not found and no transformation provided.")
            continue

        # Step 1: Base copy if direct map
        if src in df.columns:
            renamed[tgt] = df[src]
            print(f"📄 Base copied: {src} → {tgt}")

        # Step 2: Apply transformation code if present
        if logic_code and logic_code.lower() not in ["none", "n/a", ""]:
            try:
                # Expose df and renamed to eval
                local_env = {"df": df, "renamed": renamed, "pd": pd, "re": re, "np": __import__("numpy")}
                result = eval(logic_code, {}, local_env)

                # Assign result directly
                renamed[tgt] = result
                print(f"🛠️ Transformation applied to '{tgt}' using logic: {logic_code}")
            except Exception as e:
                print(f"⚠️ Error applying transformation for '{tgt}': {e}")

        # Step 3: Apply default value if defined
        if default.lower() not in ["", "n/a", "none"]:
            renamed[tgt] = renamed[tgt].fillna(default)
            print(f"🧩 Default value applied to '{tgt}': {default}")

        # Step 4: Required field check
        if required == "yes" and renamed[tgt].isnull().any():
            print(f"❗ Warning: Missing required values in '{tgt}'")

    # Step 5: Return only mapped target columns
    target_cols = mapping_df["target"].dropna().unique().tolist()
    return renamed[target_cols]
