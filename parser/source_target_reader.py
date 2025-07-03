import pandas as pd
from io import StringIO

def read_source_file(uploaded_file):
    """
    Load source file (CSV) into a DataFrame.
    Returns None if no file is uploaded.
    """
    if uploaded_file:
        try:
            return pd.read_csv(uploaded_file)
        except Exception as e:
            raise RuntimeError(f"Error reading source file: {e}")
    return None

def read_target_file(uploaded_file):
    """
    Load target file (CSV) into a DataFrame.
    Returns None if no file is uploaded.
    """
    if uploaded_file:
        try:
            return pd.read_csv(uploaded_file)
        except Exception as e:
            raise RuntimeError(f"Error reading target file: {e}")
    return None