import streamlit as st
from tabsnew import read_me, new_project, view_project
from core.db import get_database_status, create_tables_if_not_exist

st.set_page_config(page_title="QA Genius", layout="wide")

# Sidebar Navigation
st.sidebar.title("QA Genius")
choice = st.sidebar.radio(
    "Go to",
    ["Product Overview", "New Project", "View Project"]
)

# Check database status and show setup information
with st.sidebar:
    st.markdown("### Database Status")
    
    db_status = get_database_status()
    
    if db_status['all_tables_ready']:
        st.success("✅ Database Ready")
        st.info(f"{len(db_status['tables_exist'])} tables configured")
    elif db_status['connection_ok']:
        st.warning("⚠️ Incomplete Setup")
        st.error(f"❌ Missing {len(db_status['missing_tables'])} tables")
        
        if st.button("🔧 Auto-Setup Tables"):
            with st.spinner("Setting up database tables..."):
                if create_tables_if_not_exist():
                    st.success("✅ Tables created successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to create tables")
                    
        with st.expander("📋 Missing Tables"):
            for table in db_status['missing_tables']:
                st.markdown(f"• {table}")
    else:
        st.error("❌ Database Connection Failed")
        if db_status['error_message']:
            st.code(db_status['error_message'])
        st.markdown("**Check:**")
        st.markdown("• MySQL server is running")
        st.markdown("• Database credentials are correct")
        st.markdown("• Database 'ai_product_db' exists")

# Load the selected tab
if choice == "Product Overview":
    read_me.load_tab()
elif choice == "New Project":
    new_project.load_tab()
elif choice == "View Project":
    view_project.load_tab()