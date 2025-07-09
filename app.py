import streamlit as st
import base64
from ui import project_overview, project_setup, view_projects, view_artifacts

# --- Page Config ---
st.set_page_config(
    page_title="QA Genius - AI Test Generator",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Sidebar Header ---
st.sidebar.title("📌 Navigate To")

# --- CSS: Clean top radio space and pin bottom logo (main page level) ---
st.markdown("""
    <style>
    section[data-testid="stSidebar"] div[data-testid="stRadio"] {
        padding-top: 0px;
        margin-top: -15px;
    }

    /* Absolute pin logo to true bottom-left corner of sidebar */
    #bottom-kdata-logo {
        position: fixed;
        bottom: 20px;
        left: 20px;
        z-index: 999999;
    }
    </style>
""", unsafe_allow_html=True)

# --- Sidebar Navigation with Emojis ---
selected_tab = st.sidebar.radio(
    label="",
    options=[
        " About i-QA",
        " Add New Project",
        " View Project Input",
        " View Project Output"
    ]
)

# --- Base64 Encode Logo ---
def get_base64_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

#logo_base64 = get_base64_image("C:/codes/teststreamlit/KData_logo/Full Logo-KData.png")
logo_base64 = get_base64_image("Images/Full Logo-KData.png")

# --- Render Logo outside sidebar, pinned to bottom-left ---
st.markdown(
    f"""
    <div id="bottom-kdata-logo">
        <img src="data:image/png;base64,{logo_base64}" width="150">
    </div>
    """,
    unsafe_allow_html=True
)

# --- Tab Routing ---
if selected_tab == " About i-QA":
    project_overview.show()
elif selected_tab == " Add New Project":
    project_setup.show()
elif selected_tab == " View Project Input":
    view_projects.show()
elif selected_tab == " View Project Output":
    view_artifacts.show()
