import streamlit as st
import pandas as pd
import os
import docx
from database.db_utils import get_connection
import base64

def show():
    # --- Logo as Top-Right Banner (smaller + aligned) ---
   # logo_path = "C:/codes/teststreamlit/KData_logo/Only logo.png"
    logo_path = "images/Only logo.png"
    with open(logo_path, "rb") as f:
        encoded_logo = base64.b64encode(f.read()).decode()

    st.markdown(
        f"""
        <div style="display: flex; justify-content: flex-end;">
            <img src="data:image/png;base64,{encoded_logo}" width="70">
        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader(" Project Inputs 📋")

    # --- Setup session state for previews ---
    if "view_mapping_row" not in st.session_state:
        st.session_state["view_mapping_row"] = None
    if "view_brd_row" not in st.session_state:
        st.session_state["view_brd_row"] = None

    # --- Database Fetch ---
    conn = get_connection()
    if not conn:
        st.error("❌ Could not connect to the database.")
        st.stop()

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT project_key, name, description, mapping_file, brd_file, created_at 
            FROM projects ORDER BY created_at DESC
        """)
        data = cursor.fetchall()
        columns = ["Project Key", "Project Name", "Description", "Mapping File", "BRD File", "Created Date"]
        df = pd.DataFrame(data, columns=columns)
    except Exception as e:
        st.error(f"❌ Failed to fetch data: {e}")
        st.stop()
    finally:
        cursor.close()
        conn.close()

    # --- Render Table ---
    if df.empty:
        st.warning("⚠️ No project data available.")
    else:
        header = st.columns([1, 2, 2, 2, 2, 2])
        header[0].markdown("**Project Key**")
        header[1].markdown("**Project Name**")
        header[2].markdown("**Description**")
        header[3].markdown("**Mapping File**")
        header[4].markdown("**BRD File**")
        header[5].markdown("**Created Date**")

        for idx, row in df.iterrows():
            cols = st.columns([1, 2, 2, 2, 2, 2])
            cols[0].write(row["Project Key"])
            cols[1].write(row["Project Name"])
            cols[2].write(row["Description"])
            cols[5].write(str(row["Created Date"]))

            # --- Mapping File View Button
            if row["Mapping File"]:
                if cols[3].button("View", key=f"mapping_{idx}"):
                    st.session_state["view_mapping_row"] = idx if st.session_state["view_mapping_row"] != idx else None
            else:
                cols[3].markdown("⚠️ Not Found")

            # --- BRD File View Button
            if row["BRD File"]:
                if cols[4].button("View", key=f"brd_{idx}"):
                    st.session_state["view_brd_row"] = idx if st.session_state["view_brd_row"] != idx else None
            else:
                cols[4].markdown("⚠️ Not Found")

            # --- Show Mapping File Preview ---
            if st.session_state["view_mapping_row"] == idx:
                mapping_path = row["Mapping File"]
                if os.path.exists(mapping_path):
                    st.markdown(f"#### 📊 Mapping File Preview: `{os.path.basename(mapping_path)}`")
                    try:
                        all_sheets = pd.read_excel(mapping_path, sheet_name=None)
                        for sheet_name, sheet_df in all_sheets.items():
                            st.markdown(f"**Sheet: `{sheet_name}`**")
                            st.dataframe(sheet_df, use_container_width=True)
                    except Exception as e:
                        st.error(f"❌ Failed to read mapping file: {e}")
                else:
                    st.warning("⚠️ Mapping file not found on disk.")

            # --- Show BRD File Preview ---
            if st.session_state["view_brd_row"] == idx:
                brd_path = row["BRD File"]
                if os.path.exists(brd_path):
                    st.markdown(f"#### 📄 BRD File Preview: `{os.path.basename(brd_path)}`")
                    try:
                        doc = docx.Document(brd_path)
                        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
                        st.text_area("📄 BRD Contents", value=text, height=300)
                    except Exception as e:
                        st.error(f"❌ Failed to read BRD file: {e}")
                else:
                    st.warning("⚠️ BRD file not found on disk.")

            # Visual divider
            st.markdown("<hr style='margin-top: 4px; margin-bottom: 4px; border: 1px solid #ccc;'>", unsafe_allow_html=True)
