import streamlit as st
import os

def show():
    # --- Logo Banner ---
    local_logo_path = "images/Full logo-KData.png"
    fallback_logo_path = "C:/codes/teststreamlit/KData_logo/Full logo-KData.png"
    logo_width = 300
    
    # Check local images folder first, then fallback path
    logo_path = None
    if os.path.exists(local_logo_path):
        logo_path = local_logo_path
    elif os.path.exists(fallback_logo_path):
        logo_path = fallback_logo_path
    
    # Only display logo if found in either location
    if logo_path:
        try:
            st.image(logo_path, width=logo_width)
            st.markdown("<hr style='margin-top:-10px; margin-bottom: 30px;'>", unsafe_allow_html=True)
        except Exception:
            # Silently skip logo if there's any error loading it
            pass
    else:
        # Add a small spacing if no logo is displayed
        st.markdown("<br>", unsafe_allow_html=True)

    # --- Title ---
    st.subheader("About our Product: QA Genius")

    # --- Key Product Highlights ---
    st.markdown("""
    **QA Genius** is a smart and secure AI assistant built to simplify QA efforts in data migration and transformation projects.

    **Key Highlights:**
    -  **Automated Test Case Generation** using AI from mapping specs and requirement documents  
    -  **Dimension-Based Rule Classification** (e.g., Accuracy, Completeness, Consistency, etc.)  
    -  **Test Logic Extraction from BRDs** written in natural language  
    -  **Modular and Scalable** – Easy to plug into larger QA workflows    
    -  **No Internet Dependency** – Can run in isolated or secure environments   
    -  **Designed with Security in Mind** – No cloud dependency, ideal for sensitive environments
    """)

    # --- Architecture Placeholder ---
    st.markdown("---")
    st.markdown("### Architecture")
    st.info(" Architecture diagram will be uploaded soon.")
