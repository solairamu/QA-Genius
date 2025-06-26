import pandas as pd
from typing import Union
from io import BytesIO

def convert_df_to_download(df: pd.DataFrame) -> bytes:
    """
    Convert a DataFrame to bytes for CSV download in Streamlit.

    Args:
        df (pd.DataFrame): DataFrame to convert.

    Returns:
        bytes: Encoded CSV content.
    """
    try:
        return df.to_csv(index=False).encode("utf-8")
    except Exception as e:
        print(f"❌ Failed to convert DataFrame to CSV: {e}")
        return b""


def convert_text_to_download(text: str) -> bytes:
    """
    Convert plain text to bytes for download.

    Args:
        text (str): Text to convert.

    Returns:
        bytes: UTF-8 encoded bytes.
    """
    try:
        return text.encode("utf-8")
    except Exception as e:
        print(f"❌ Failed to convert text to bytes: {e}")
        return b""


def preview_uploaded_file(file, file_type: str = "csv", max_rows: int = 500) -> pd.DataFrame:
    """
    Helper to preview uploaded CSV or Excel files in Streamlit.

    Args:
        file: Uploaded file (stream or buffer)
        file_type (str): "csv" or "excel"
        max_rows (int): Maximum number of rows to preview

    Returns:
        pd.DataFrame: Parsed preview of the file
    """
    try:
        if file_type.lower() == "csv":
            df = pd.read_csv(file)
        elif file_type.lower() == "excel":
            df = pd.read_excel(file)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        return df.head(max_rows)
    except Exception as e:
        print(f"❌ Failed to preview file: {e}")
        return pd.DataFrame()
