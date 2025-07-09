import streamlit as st
import os

def show():
    # --- Logo Banner ---
    local_logo_path = "images/Full logo-KData.png"
    #fallback_logo_path = "C:/codes/teststreamlit/KData_logo/Full logo-KData.png"
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
    st.subheader("Intelligent QA: Offline AI Engine for Systematic, Standards-Based Data Quality Testing")

    # --- Updated Product Description ---
    st.markdown("""
QA Genius delivers full-scope, high-trust data testing—offline, intelligent, and aligned to industry best practices.  
It ingests your BRDs and mapping specs, breaks them down into logical testable units, and generates exhaustive QA coverage across critical data quality dimensions.

#### 💡 Core Capabilities

✓ **Automated Test Case Generation** — Instantly turns uploaded documents into test cases with no manual effort.  
✓ **Business Rule Translation to Execution** — Converts high-level business rules into field-level, column-level, and cross-entity validations.  
✓ **Scalable & Pluggable** — Designed to slot into larger QA ecosystems with modular ease.  
✓ **Fully Offline Deployment** — Runs completely offline, making it suitable for government, defense, healthcare, and other high-security environments.

#### 🔍 Comprehensive Testing Across 6 Key Dimensions

QA Genius ensures systematic coverage across every data quality pillar—not just spot checks, but full-spectrum scanning aligned with industry frameworks:

 - **Accuracy** — Are values correct and within expected ranges?  
 - **Completeness** — Are mandatory fields populated as required?  
 - **Consistency** — Are formats and relationships between fields logically coherent?  
 - **Uniqueness** — Are key identifiers truly distinct when they need to be?  
 - **Validity** — Do values conform to domain-specific rules, formats, and types?  
 - **Timeliness** — Is the data current and refreshed within acceptable thresholds?
""")

    # --- Architecture Placeholder ---
    st.markdown("---")
    st.markdown("### 🧱 Architecture")
    st.info("Architecture diagram will be uploaded soon.")
