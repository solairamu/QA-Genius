import streamlit as st
import pandas as pd
from database.db_utils import get_connection


def show():
    st.subheader(" View Projects")

    conn = get_connection()
    if not conn:
        st.error(" Could not connect to the database.")
        return

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT project_key, name, description, created_at FROM projects ORDER BY created_at DESC")
        data = cursor.fetchall()
        df = pd.DataFrame(data, columns=["Project Key", "Project Name", "Description", "Created Date"])
    except Exception as e:
        st.error(f" Failed to fetch data: {e}")
        return
    finally:
        cursor.close()
        conn.close()

    if df.empty:
        st.warning(" No project data available.")
    else:
        st.dataframe(df, use_container_width=True)