import streamlit as st
from PIL import Image
import os

def load_tab():
    # Hide Streamlit warning (optional)
    st.markdown(
        """
        <style>
        .stAlert { display: none; }
        </style>
        """,
        unsafe_allow_html=True
    )

    # --- Logo ---
    logo_path = "C:/Users/User/Downloads/Final-Logo-Design-for-K-Data-Colorfull-e1736333692140.jpg"
    if os.path.exists(logo_path):
        st.image(logo_path, width=400)
    else:
        st.warning("⚠️ Logo not found at the specified path.")

    # --- About Section ---
    st.markdown("""
    ---
    ### About Our Product: **QA Genius**

    **QA Genius** is a secure, offline tool designed to simplify and validate data migration. It maps source to target data, applies rule-based checks, generates AI-powered test cases, and shows results in clear dashboards.

    Key Features:
    - **Works Offline or On-Prem** – No internet needed. Runs fully inside your local setup.  
    - **100% Secure** – Your data stays safe inside your system. 
    - **Data Migration Mapping** – Easily map and validate source to target data.
    - **AI Test Case Generation** – Automatically creates test cases using AI.
    - **Rule-Based Validation** – Apply smart rules to check your data.
    - **Visual Dashboards** – See results with clean charts and summaries.
    ---
    """)
    # --- Architecture Diagram Section ---
    st.markdown("### Architecture")

    arch_path = "C:/Users/User/Downloads/diagram-export-6-9-2025-10_54_25-PM (1).png"  

    if os.path.exists(arch_path):
        image = Image.open(arch_path)
        st.image(image, caption="QA Genius System Architecture", width=1000)  # ← Option 1: Fixed width
    else:
        st.warning("⚠️ Architecture image not found. Please check the path and file format.")


    # --- Entity Diagram Section ---
    st.markdown("### Entity Relationship Diagram")

    arch_path = "C:/Users/User/Downloads/entity_diag.png"  

    if os.path.exists(arch_path):
        image = Image.open(arch_path)
        st.image(image, caption="ER Diagram", width=1000)  # ← Option 1: Fixed width
    else:
        st.warning("⚠️ ER image not found. Please check the path and file format.")