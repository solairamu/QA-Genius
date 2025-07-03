import streamlit as st
from ui import project_setup, view_artifacts, view_projects  # make sure view_projects.py exists

# --- Page Config ---
st.set_page_config(
    page_title="QA Genius - AI Test Generator",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Custom Header ---
st.markdown("<h2 style='text-align:center;'> QA Genius — AI Test Case & Script Generator</h2>", unsafe_allow_html=True)
st.markdown("---")

# --- Tab Navigation with new tab in middle ---
tab1, tab2, tab3 = st.tabs([
    " Project Setup",
    " View Projects",      
    " View Artifacts"
])

with tab1:
    project_setup.show()

with tab2:
    view_projects.show()  

with tab3:
    view_artifacts.show()