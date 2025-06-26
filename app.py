import streamlit as st
from ui import project_setup, view_artifacts
from database.db_utils import initialize_database

# --- Database Initialization ---
# Initialize database and tables if they don't exist
@st.cache_resource
def init_db():
    """Initialize database on app startup (cached to run only once)"""
    return initialize_database()

# Initialize database
init_db()

# --- Page Config ---
st.set_page_config(
    page_title="QA Genius - AI Test Generator",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Custom Header ---
st.markdown("<h2 style='text-align:center;'>🧠 QA Genius — AI Test Case & Script Generator</h2>", unsafe_allow_html=True)
st.markdown("---")

# --- Tab Navigation ---
tab1, tab2 = st.tabs([
    "📁 Project Setup",
    "📂 View Artifacts"
])

with tab1:
    project_setup.show()

with tab2:
    view_artifacts.show()
