import streamlit as st
from tabsnew import read_me, new_project, view_project

st.set_page_config(page_title="AI Product", layout="wide")

# Sidebar Navigation
st.sidebar.title("QA Genius")
choice = st.sidebar.radio(
    "Go to",
    ["Read Me", "New Project", "View Project"]
)

# Load the selected tab
if choice == "Read Me":
    read_me.load_tab()
elif choice == "New Project":
    new_project.load_tab()
elif choice == "View Project":
    view_project.load_tab()
