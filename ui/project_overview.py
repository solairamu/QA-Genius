import streamlit as st
import base64

def show():
    # --- Centered Brand Header with subtle indent on subtext ---
    st.markdown(
        """
        <div style='text-align: center; margin-bottom: 10px; line-height: 1.2;'>
            <div style='font-size: 48px; font-weight: bold; color: #222;'>i-QA</div>
            <div style='font-size: 20px; color: #777; margin-top: 4px; padding-left: 150px;'>by KData</div>
        </div>
        <hr style='margin-top: -5px; margin-bottom: 30px; border: 1px solid #ccc;'>
        """,
        unsafe_allow_html=True
    )

    # --- Title ---
    st.subheader("Intelligent QA (i-QA): Offline AI Engine for Systematic, Standards-Based Data Quality Testing")

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

   # architecture_path = "C:/Users/User/Downloads/Arch Diagram.png"
    architecture_path = "Images/Arch Diagram.png"
    try:
        #  Fix extra spacing above/below the image
        st.markdown("""
            <style>
                h3 {
                    margin-bottom: 0rem !important;
                }
                img {
                    margin-top: -20px !important;
                    margin-bottom: -20px !important;
                    display: block;
                }
                }
            </style>
        """, unsafe_allow_html=True)

        st.image(architecture_path)

    except Exception as e:
        st.warning(f"Could not load architecture image: {e}")

    # --- Tool Requirements Table ---
    st.markdown("---")
    st.markdown("### 🛠️ Tool Requirements")

    requirements_table = """
    <style>
        .center-table-wrapper {
            display: flex;
            justify-content: center;
        }
        table {
            border-collapse: collapse;
            width: 80%;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        }
        th, td {
            border: 1px solid #ccc;
            padding: 10px;
            vertical-align: middle;
            text-align: center;
        }
        thead th {
            background-color: #f2f2f2;
            font-weight: bold;
            text-align: center !important;
        }
    </style>

    <div class="center-table-wrapper">
        <table>
            <thead>
                <tr>
                    <th style="text-align: center;">Specification</th>
                    <th style="text-align: center;">Ideal</th>
                    <th style="text-align: center;">Minimum</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>Response Time</td><td>~20 sec</td><td>~8–10 Minutes</td></tr>
                <tr><td>RAM</td><td>32 GB</td><td>16 GB</td></tr>
                <tr><td>GPU</td><td>NVIDIA RTX 5090</td><td>Integrated Graphics Card</td></tr>
                <tr><td>vRAM</td><td>32 GB</td><td>4 GB</td></tr>
                <tr><td>Disk Space</td><td>20 GB</td><td>10–20 GB Free</td></tr>
            </tbody>
        </table>
    </div>
    """
    st.markdown(requirements_table, unsafe_allow_html=True)
