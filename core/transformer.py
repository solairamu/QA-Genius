import pandas as pd
import numpy as np
import re
from datetime import datetime
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    from difflib import SequenceMatcher
    RAPIDFUZZ_AVAILABLE = False
    print("⚠️ RapidFuzz not found. Install with: pip install rapidfuzz")
    print("   Falling back to difflib (slower)")

def detect_column_mappings_exact(mapping_df: pd.DataFrame) -> dict:
    """
    Fast exact pattern matching - tries predetermined patterns first.
    Returns a dictionary mapping standard names to actual column names.
    """
    columns = [col.lower().strip() for col in mapping_df.columns]
    column_map = {}
    
    # Source column variations
    source_patterns = ['source', 'sourcefield', 'source_field', 'src', 'from', 'input', 'original',
                      'beginning', 'start', 'initial', 'baseline', 'raw_material', 'initial_value']
    for pattern in source_patterns:
        matches = [col for col in columns if pattern in col.lower()]
        if matches:
            # Find the actual column name (preserving original case)
            actual_col = next(orig_col for orig_col in mapping_df.columns 
                            if orig_col.lower().strip() == matches[0])
            column_map['source'] = actual_col
            break
    
    # Target column variations
    target_patterns = ['target', 'targetfield', 'target_field', 'tgt', 'to', 'output', 'destination', 'dest',
                      'endpoint', 'end', 'final', 'outcome', 'finished_product', 'final_value']
    for pattern in target_patterns:
        matches = [col for col in columns if pattern in col.lower()]
        if matches:
            actual_col = next(orig_col for orig_col in mapping_df.columns 
                            if orig_col.lower().strip() == matches[0])
            column_map['target'] = actual_col
            break
    
    # Transformation column variations
    transform_patterns = ['transformation', 'transform', 'transformation_code', 'transform_code', 
                         'code', 'logic', 'rule', 'formula', 'expression',
                         'method', 'procedure', 'process', 'algorithm']
    for pattern in transform_patterns:
        matches = [col for col in columns if pattern in col.lower()]
        if matches:
            actual_col = next(orig_col for orig_col in mapping_df.columns 
                            if orig_col.lower().strip() == matches[0])
            column_map['transformation_code'] = actual_col
            break
    
    # Required column variations
    required_patterns = ['required', 'mandatory', 'req', 'must', 'essential',
                        'necessary', 'needed', 'critical', 'vital']
    for pattern in required_patterns:
        matches = [col for col in columns if pattern in col.lower()]
        if matches:
            actual_col = next(orig_col for orig_col in mapping_df.columns 
                            if orig_col.lower().strip() == matches[0])
            column_map['required'] = actual_col
            break
    
    # Direct map column variations
    direct_patterns = ['direct', 'direct_map', 'directmap', 'copy', 'direct_copy',
                      'simple', 'plain', 'unchanged', 'identical']
    for pattern in direct_patterns:
        matches = [col for col in columns if pattern in col.lower()]
        if matches:
            actual_col = next(orig_col for orig_col in mapping_df.columns 
                            if orig_col.lower().strip() == matches[0])
            column_map['direct_map'] = actual_col
            break
    
    # Default value column variations
    default_patterns = ['default', 'default_value', 'defaultvalue', 'fallback', 'backup',
                       'preset', 'standard', 'placeholder', 'substitute']
    for pattern in default_patterns:
        matches = [col for col in columns if pattern in col.lower()]
        if matches:
            actual_col = next(orig_col for orig_col in mapping_df.columns 
                            if orig_col.lower().strip() == matches[0])
            column_map['default_value'] = actual_col
            break
    
    # Conditional mapping column variations
    conditional_patterns = ['conditional', 'conditionalmapping', 'conditional_mapping', 'condition', 'conditions',
                           'conditional_logic', 'if_then', 'business_rule', 'mapping_rule', 'conditional_rule',
                           'criteria', 'criterion', 'constraints', 'requirements', 'specifications']
    for pattern in conditional_patterns:
        matches = [col for col in columns if pattern in col.lower()]
        if matches:
            actual_col = next(orig_col for orig_col in mapping_df.columns 
                            if orig_col.lower().strip() == matches[0])
            column_map['conditional_mapping'] = actual_col
            break
    
    return column_map

def fuzzy_match_columns(mapping_df: pd.DataFrame, confidence_threshold: float = 0.6) -> dict:
    """
    Use fuzzy string matching to detect column mappings with higher tolerance for variations.
    Uses RapidFuzz if available, falls back to difflib.
    Returns a dictionary mapping standard names to actual column names.
    """
    columns = mapping_df.columns.tolist()
    column_map = {}
    used_columns = set()  # Track which columns have been assigned
    
    # Define semantic categories with comprehensive synonym coverage
    categories = {
        'source': [
            # Direct variations
            'source', 'sourcefield', 'source_field', 'source_column', 'src', 'from', 'input', 
            'original', 'orig', 'source_name', 'input_field', 'input_column', 'origin',
            
            # True synonyms - semantically similar but different spelling
            'beginning', 'start', 'initial', 'baseline', 'raw', 'incoming', 'inbound',
            'primary', 'base', 'foundation', 'raw_material', 'initial_value', 'starting_point',
            'old', 'existing', 'current', 'before', 'legacy', 'previous', 'old_value',
            'predecessor', 'antecedent', 'originator', 'parent', 'root'
        ],
        'target': [
            # Direct variations  
            'target', 'targetfield', 'target_field', 'target_column', 'tgt', 'to', 'output', 
            'destination', 'dest', 'target_name', 'output_field', 'output_column', 'result',
            
            # True synonyms
            'endpoint', 'end', 'final', 'outcome', 'finished', 'outgoing', 'outbound',
            'secondary', 'derived', 'conclusion', 'finished_product', 'final_value', 'ending_point',
            'new', 'updated', 'modified', 'after', 'revised', 'changed', 'new_value',
            'successor', 'consequent', 'child', 'offspring', 'branch'
        ],
        'transformation_code': [
            # Direct variations
            'transformation', 'transform', 'transformation_code', 'transform_code', 'code', 
            'logic', 'rule', 'formula', 'expression', 'transform_logic', 'mapping_logic',
            'calculation', 'function', 'transform_rule', 'transformation_rule',
            
            # True synonyms
            'method', 'procedure', 'process', 'algorithm', 'technique', 'approach',
            'methodology', 'operation', 'conversion', 'manipulation', 'processing',
            'computation', 'evaluation', 'execution', 'implementation', 'derivation'
        ],
        'conditional_mapping': [
            # Direct variations
            'conditional', 'conditionalmapping', 'conditional_mapping', 'condition', 'conditions',
            'conditional_logic', 'if_then', 'business_rule', 'mapping_rule', 'conditional_rule',
            
            # True synonyms  
            'criteria', 'criterion', 'constraints', 'requirements', 'specifications',
            'guidelines', 'policies', 'rules', 'provisions', 'stipulations',
            'parameters', 'limitations', 'restrictions', 'filters', 'validators'
        ],
        'required': [
            # Direct variations
            'required', 'mandatory', 'req', 'must', 'essential', 'is_required', 'is_mandatory',
            'mandatory_flag', 'required_flag', 'necessity', 'compulsory',
            
            # True synonyms
            'obligatory', 'necessary', 'needed', 'demanded', 'critical', 'vital',
            'important', 'key', 'fundamental', 'indispensable', 'prerequisite'
        ],
        'direct_map': [
            # Direct variations
            'direct', 'direct_map', 'directmap', 'copy', 'direct_copy', 'is_direct',
            'direct_mapping', 'passthrough', 'direct_transfer',
            
            # True synonyms
            'straight', 'simple', 'plain', 'basic', 'unchanged', 'identical',
            'mirror', 'duplicate', 'replicate', 'clone', 'reproduce'
        ],
        'default_value': [
            # Direct variations
            'default', 'default_value', 'defaultvalue', 'fallback', 'backup', 'default_val',
            'fallback_value', 'backup_value', 'null_replacement',
            
            # True synonyms
            'preset', 'standard', 'initial', 'baseline', 'placeholder', 'substitute',
            'alternative', 'replacement', 'standby', 'reserve', 'contingency'
        ]
    }
    
    def get_similarity(str1: str, str2: str) -> float:
        """Calculate similarity between two strings using best available method"""
        # Normalize strings: lowercase, replace underscores/spaces, remove special chars
        s1 = re.sub(r'[_\s-]+', '', str1.lower())
        s2 = re.sub(r'[_\s-]+', '', str2.lower())
        
        if RAPIDFUZZ_AVAILABLE:
            # Use RapidFuzz with token_sort_ratio for better word order handling
            return fuzz.token_sort_ratio(s1, s2) / 100.0
        else:
            # Fallback to difflib
            return SequenceMatcher(None, s1, s2).ratio()
    
    def find_best_match(column_name: str, patterns: list) -> tuple:
        """Find the best matching pattern and return (pattern, similarity_score)"""
        best_score = 0
        best_pattern = None
        
        for pattern in patterns:
            score = get_similarity(column_name, pattern)
            if score > best_score:
                best_score = score
                best_pattern = pattern
        
        return best_pattern, best_score
    
    # Create a list of all potential matches with scores
    all_matches = []
    for category, patterns in categories.items():
        for column in columns:
            if column not in used_columns:
                _, score = find_best_match(column, patterns)
                if score >= confidence_threshold:
                    all_matches.append((score, category, column))
    
    # Sort by score (highest first) and assign columns to categories
    all_matches.sort(key=lambda x: x[0], reverse=True)
    
    for score, category, column in all_matches:
        # Only assign if category not yet filled and column not yet used
        if category not in column_map and column not in used_columns:
            column_map[category] = column
            used_columns.add(column)
            fuzzy_type = "RapidFuzz" if RAPIDFUZZ_AVAILABLE else "difflib"
            print(f"🔍 Fuzzy matched '{category}' → '{column}' (confidence: {score:.2f}, {fuzzy_type})")
    
    return column_map

def detect_column_mappings(mapping_df: pd.DataFrame) -> dict:
    """
    Tiered approach to column detection:
    1. First try exact pattern matching (fastest)
    2. Fall back to fuzzy matching (more robust)
    3. Fall back to user interaction (most reliable)
    """
    print("🔍 Attempting exact pattern matching...")
    
    # Tier 1: Try exact pattern matching first
    column_map = detect_column_mappings_exact(mapping_df)
    
    # Check if we got the essential columns
    if 'source' in column_map and 'target' in column_map:
        print(f"✅ Exact pattern matching successful!")
        for key, value in column_map.items():
            print(f"   {key} → {value}")
        return column_map
    
    print("⚠️ Exact pattern matching incomplete. Trying fuzzy matching...")
    
    # Tier 2: Try fuzzy matching
    fuzzy_map = fuzzy_match_columns(mapping_df, confidence_threshold=0.6)
    
    # Merge results (fuzzy matching fills in gaps)
    for key, value in fuzzy_map.items():
        if key not in column_map:
            column_map[key] = value
    
    # Check again if we have essential columns
    if 'source' in column_map and 'target' in column_map:
        print(f"✅ Fuzzy matching successful!")
        return column_map
    
    # Try with lower confidence threshold
    print("🔄 Trying fuzzy matching with relaxed confidence...")
    relaxed_fuzzy_map = fuzzy_match_columns(mapping_df, confidence_threshold=0.3)
    
    for key, value in relaxed_fuzzy_map.items():
        if key not in column_map:
            column_map[key] = value
    
    if 'source' in column_map and 'target' in column_map:
        print(f"✅ Relaxed fuzzy matching successful!")
        return column_map
    
    # Tier 3: Interactive fallback
    print("\n❌ Automatic column detection failed!")
    print("Available columns:", mapping_df.columns.tolist())
    print("\nPlease manually specify the column mappings:")
    
    # Reset column_map for clean start
    column_map = {}
    essential_mappings = ['source', 'target']
    
    for mapping in essential_mappings:
        while mapping not in column_map:
            user_input = input(f"Which column contains the {mapping} field names? Enter column name: ").strip()
            if user_input in mapping_df.columns:
                column_map[mapping] = user_input
                print(f"✅ Set {mapping} → {user_input}")
            else:
                print(f"❌ Column '{user_input}' not found. Available: {mapping_df.columns.tolist()}")
    
    # Optional mappings
    optional_mappings = ['transformation_code', 'required', 'direct_map', 'default_value']
    for mapping in optional_mappings:
        user_input = input(f"Which column contains {mapping}? (Press Enter to skip): ").strip()
        if user_input and user_input in mapping_df.columns:
            column_map[mapping] = user_input
            print(f"✅ Set {mapping} → {user_input}")
    
    return column_map

def apply_transformations(df: pd.DataFrame, mapping_df: pd.DataFrame) -> pd.DataFrame:
    # Step 1: Apply automatic phone number cleaning BEFORE manual transformations
    print("📞 Checking for phone number columns to clean...")
    df_clean = apply_phone_transformations(df)
    
    renamed = df_clean.copy()
    
    # Dynamically detect column mappings
    col_map = detect_column_mappings(mapping_df)
    
    print(f"🔍 Detected column mappings: {col_map}")
    
    # Check if we found the essential columns
    if 'source' not in col_map or 'target' not in col_map:
        print("❌ Could not detect source and target columns in mapping file.")
        print("Available columns:", mapping_df.columns.tolist())
        print("Please ensure your mapping file has columns that contain 'source' and 'target' (or similar variations)")
        return df_clean  # Return at least the phone-cleaned data

    # Define reusable helper functions for transformation logic
    def cap_value(x, cap=10000):
        return np.minimum(x, cap)

    def concat(a, b, sep=' '):
        return a.astype(str) + sep + b.astype(str)

    def years_since(date_series):
        today = datetime.today()
        return pd.to_datetime(date_series, errors='coerce').apply(lambda d: today.year - d.year if pd.notnull(d) else None)

    # LLM-based conditional mapping
    def llm_parse_conditional(conditional_text: str, source_field: str) -> str:
        """
        Use LLM to convert natural language conditional logic to pandas code.
        Returns executable Python code string.
        """
        if not conditional_text or conditional_text.lower() in ["none", "n/a", "", "null", "nan"]:
            return None
        
        # Simple prompt for local LLM
        prompt = f"""Convert this conditional mapping rule to Python pandas code:

Rule: {conditional_text}
Source field: {source_field}

Requirements:
- Return only executable Python code
- Use pandas Series.apply() with lambda
- Reference the source series as 'series'
- Return the transformed series

Example input: "If Gender == 'M' then 'Male', else 'Female'"
Example output: series.apply(lambda x: 'Male' if str(x).strip() == 'M' else 'Female')

Convert the rule to code:"""

        try:
            # Try to use local LLM (you can replace this with your LLM client)
            # For now, we'll use a fallback pattern-based approach
            return fallback_conditional_parser(conditional_text)
        except Exception as e:
            print(f"❌ LLM conditional parsing failed: {e}")
            return fallback_conditional_parser(conditional_text)

    def fallback_conditional_parser(conditional_str: str) -> str:
        """Enhanced fallback parser for common conditional patterns"""
        if not conditional_str or str(conditional_str).lower() in ["none", "n/a", "", "null", "nan"]:
            return None
        
        conditional_str = str(conditional_str).strip()
        
        try:
            # Normalize whitespace and prepare for multiple pattern matching
            normalized = ' '.join(conditional_str.split())
            
            # Pattern 1: Standard If-Then-Else with == (handles various quote types)
            pattern1 = r'if\s+\w+\s*==\s*["\']([^"\']+)["\']\s+then\s+["\']([^"\']+)["\'],?\s*else\s+["\']([^"\']+)["\']'
            match1 = re.search(pattern1, normalized, re.IGNORECASE)
            if match1:
                condition_value, then_value, else_value = match1.groups()
                return f"series.apply(lambda x: '{then_value}' if str(x).strip() == '{condition_value}' else '{else_value}')"
            
            # Pattern 2: If-Then-Else with keep original (else FieldName)
            pattern2 = r'if\s+\w+\s*==\s*["\']([^"\']+)["\']\s+then\s+["\']([^"\']+)["\'],?\s*else\s+\w+'
            match2 = re.search(pattern2, normalized, re.IGNORECASE)
            if match2:
                condition_value, then_value = match2.groups()
                return f"series.apply(lambda x: '{then_value}' if str(x).strip() == '{condition_value}' else str(x))"
            
            # Pattern 3: Alternative operators (= instead of ==)
            pattern3 = r'if\s+\w+\s*=\s*([A-Za-z0-9]+)\s+then\s+([A-Za-z0-9]+)\s*else\s+([A-Za-z0-9]+)'
            match3 = re.search(pattern3, normalized, re.IGNORECASE)
            if match3:
                condition_value, then_value, else_value = match3.groups()
                return f"series.apply(lambda x: '{then_value}' if str(x).strip() == '{condition_value}' else '{else_value}')"
            
            # Pattern 4: When-Set-Otherwise format
            pattern4 = r'when\s+\w+\s+equals?\s+([A-Za-z0-9]+)\s+set\s+to\s+([A-Za-z0-9]+)\s+otherwise\s+([A-Za-z0-9]+)'
            match4 = re.search(pattern4, normalized, re.IGNORECASE)
            if match4:
                condition_value, then_value, else_value = match4.groups()
                return f"series.apply(lambda x: '{then_value}' if str(x).strip() == '{condition_value}' else '{else_value}')"
            
            # Pattern 5: Map X/Y to A/B format
            if "map" in conditional_str.lower() and "/" in conditional_str:
                if "m/f" in conditional_str.lower() and "male/female" in conditional_str.lower():
                    return "series.apply(lambda x: 'Male' if str(x).strip().upper() == 'M' else 'Female')"
            
            # Pattern 6: Handle extra whitespace in standard format
            pattern6 = r'if\s+\w+\s*==\s*["\']([^"\']+)["\']\s+then\s+["\']([^"\']+)["\']\s*,?\s*else\s+["\']([^"\']+)["\']'
            match6 = re.search(pattern6, conditional_str, re.IGNORECASE)
            if match6:
                condition_value, then_value, else_value = match6.groups()
                return f"series.apply(lambda x: '{then_value}' if str(x).strip() == '{condition_value}' else '{else_value}')"
            
            print(f"⚠️ Could not parse conditional: {conditional_str}")
            return None
            
        except Exception as e:
            print(f"❌ Error parsing conditional '{conditional_str}': {e}")
            return None

    def parse_conditional_logic(conditional_str: str, source_series: pd.Series) -> pd.Series:
        """Parse and apply conditional mapping logic using LLM or fallback"""
        if not conditional_str or str(conditional_str).lower() in ["none", "n/a", "", "null", "nan"]:
            return source_series
        
        try:
            # Get executable code from LLM or fallback parser
            code = llm_parse_conditional(conditional_str, source_series.name or 'source')
            
            if code:
                print(f"   🎯 Generated code: {code}")
                # Execute the generated code
                local_env = {"series": source_series, "pd": pd, "np": np}
                result = eval(code, {}, local_env)
                return result
            else:
                print(f"   ⚠️ No code generated for: {conditional_str}")
                return source_series
                
        except Exception as e:
            print(f"   ❌ Error executing conditional logic: {e}")
            return source_series

    for _, row in mapping_df.iterrows():
        # Use detected column names
        src = row[col_map['source']]
        tgt = row[col_map['target']]
        
        # Get optional columns with fallbacks - properly handle NaN values
        required = str(row.get(col_map.get('required', ''), "")).strip().lower()
        direct = str(row.get(col_map.get('direct_map', ''), "")).strip().lower()
        default = str(row.get(col_map.get('default_value', ''), "")).strip()
        
        # Handle transformation code - check for NaN/empty values
        logic_code_raw = row.get(col_map.get('transformation_code', ''), "")
        logic_code = str(logic_code_raw).strip() if pd.notna(logic_code_raw) else ""
        
        # Handle conditional mapping - check for NaN/empty values  
        conditional_raw = row.get(col_map.get('conditional_mapping', ''), "")
        conditional_logic = str(conditional_raw).strip() if pd.notna(conditional_raw) else ""

        print(f"\n🔄 Processing: {src} → {tgt}")
        
        # Debug info
        if conditional_logic and conditional_logic.lower() not in ["none", "n/a", "", "null", "nan"]:
            print(f"   📋 Conditional rule: {conditional_logic}")

        if src not in df_clean.columns and logic_code == "" and conditional_logic == "":
            print(f"⛔ Skipped: '{src}' not found and no transformation provided.")
            continue

        # Step 1: Base copy if direct map
        if src in df_clean.columns:
            renamed[tgt] = df_clean[src]
            print(f"📄 Base copied: {src} → {tgt}")

        # Step 2: Apply conditional mapping if present (highest priority)
        if conditional_logic and conditional_logic.lower() not in ["none", "n/a", "", "null", "nan"]:
            if src in df_clean.columns:
                renamed[tgt] = parse_conditional_logic(conditional_logic, df_clean[src])
                print(f"🔀 Conditional mapping applied to '{tgt}'")
            else:
                print(f"⚠️ Cannot apply conditional mapping: source '{src}' not found")

        # Step 3: Apply transformation code if present (and no conditional mapping applied)
        elif logic_code and logic_code.lower() not in ["none", "n/a", "", "null", "nan"]:
            try:
                local_env = {
                    "df": df_clean,
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

        # Step 4: Apply default value if defined
        if default.lower() not in ["", "n/a", "none", "null", "nan"]:
            renamed[tgt] = renamed[tgt].fillna(default)
            print(f"🧩 Default value applied to '{tgt}': {default}")

        # Step 5: Required field check
        if required == "yes" and renamed[tgt].isnull().any():
            print(f"❗ Warning: Missing required values in '{tgt}'")

    # Step 6: Return only mapped target columns
    target_cols = mapping_df[col_map['target']].dropna().unique().tolist()
    return renamed[target_cols]

def clean_phone_number(phone_str):
    """
    Clean and standardize phone number to +1-XXX-XXX-XXXX format.
    Handles various input formats including extensions and different separators.
    
    Examples:
    - "(815)454-1041x1567" → "+1-815-454-1041"
    - "815-454-1041 ext 1567" → "+1-815-454-1041"
    - "(815) 454 1041" → "+1-815-454-1041"
    - "8154541041" → "+1-815-454-1041"
    """
    if pd.isna(phone_str) or phone_str == "":
        return phone_str
    
    # Convert to string and strip whitespace
    phone = str(phone_str).strip()
    
    # Remove extensions (x####, ext ####, extension ####)
    phone = re.sub(r'(?i)\s*(x|ext|extension)\.?\s*\d+', '', phone)
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Handle different digit counts
    if len(digits_only) == 10:
        # US number without country code
        formatted = f"+1-{digits_only[:3]}-{digits_only[3:6]}-{digits_only[6:]}"
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        # US number with country code
        formatted = f"+1-{digits_only[1:4]}-{digits_only[4:7]}-{digits_only[7:]}"
    elif len(digits_only) == 7:
        # Local number (add default area code - you might want to customize this)
        formatted = f"+1-000-{digits_only[:3]}-{digits_only[3:]}"
    else:
        # Invalid length - return original for manual review
        return phone_str
    
    return formatted

def validate_phone_number(phone_str):
    """
    Validate phone number against the standard format: ^\+1-\d{3}-\d{3}-\d{4}$
    Returns True if valid, False otherwise.
    """
    if pd.isna(phone_str) or phone_str == "":
        return False
    
    pattern = r'^\+1-\d{3}-\d{3}-\d{4}$'
    return bool(re.match(pattern, str(phone_str)))

def detect_phone_columns(df):
    """
    Dynamically detect phone number columns in a DataFrame.
    Returns list of column names that likely contain phone numbers.
    """
    phone_columns = []
    
    for col in df.columns:
        col_lower = col.lower()
        
        # Check for phone-related keywords in column name
        phone_keywords = ['phone', 'tel', 'telephone', 'mobile', 'cell', 'contact', 'number']
        if any(keyword in col_lower for keyword in phone_keywords):
            phone_columns.append(col)
            continue
        
        # Check data patterns in the column for phone-like formats
        if df[col].dtype == 'object':  # Only check string columns
            # Sample non-null values
            sample_values = df[col].dropna().head(10).astype(str)
            
            if len(sample_values) > 0:
                phone_like_count = 0
                
                for value in sample_values:
                    # Check if value looks like a phone number
                    # Remove all non-digits and check length
                    digits_only = re.sub(r'\D', '', str(value))
                    
                    # Phone numbers typically have 7, 10, or 11 digits
                    if len(digits_only) in [7, 10, 11]:
                        # Check for common phone patterns
                        phone_patterns = [
                            r'\(\d{3}\)\s*\d{3}[-\s]?\d{4}',  # (123) 456-7890
                            r'\d{3}[-\s]\d{3}[-\s]\d{4}',     # 123-456-7890 or 123 456 7890
                            r'\+?1?[-\s]?\d{10}',             # +1 1234567890
                            r'\d{10}',                        # 1234567890
                            r'\d{3}\.\d{3}\.\d{4}'            # 123.456.7890
                        ]
                        
                        if any(re.search(pattern, str(value)) for pattern in phone_patterns):
                            phone_like_count += 1
                
                # If more than 60% of sampled values look like phone numbers
                if phone_like_count / len(sample_values) > 0.6:
                    phone_columns.append(col)
    
    return phone_columns

def apply_phone_transformations(df):
    """
    Automatically detect and clean phone number columns in a DataFrame.
    Returns the DataFrame with cleaned phone numbers.
    """
    df_cleaned = df.copy()
    phone_columns = detect_phone_columns(df)
    
    if phone_columns:
        print(f"📞 Detected phone columns: {phone_columns}")
        
        for col in phone_columns:
            print(f"   🧹 Cleaning phone numbers in column: {col}")
            
            # Show some before/after examples
            sample_before = df[col].dropna().head(3).tolist()
            
            # Apply cleaning
            df_cleaned[col] = df[col].apply(clean_phone_number)
            
            # Show after
            sample_after = df_cleaned[col].dropna().head(3).tolist()
            
            print(f"   📋 Examples:")
            for before, after in zip(sample_before, sample_after):
                print(f"      {before} → {after}")
            
            # Validate cleaned numbers
            valid_count = df_cleaned[col].apply(validate_phone_number).sum()
            total_count = df_cleaned[col].dropna().shape[0]
            
            print(f"   ✅ Validation: {valid_count}/{total_count} numbers match standard format")
            
            if valid_count < total_count:
                invalid_numbers = df_cleaned[~df_cleaned[col].apply(validate_phone_number) & df_cleaned[col].notna()][col].head(5).tolist()
                print(f"   ⚠️ Some numbers need manual review: {invalid_numbers}")
    
    return df_cleaned