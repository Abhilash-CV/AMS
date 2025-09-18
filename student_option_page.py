import streamlit as st
import pandas as pd
from streamlit_sortables import sort_items  # 👈 pip install streamlit-sortables

def student_option_ui_modern(year: str, program: str, student_id: str = None):
    st.markdown(
        "<h2 style='text-align:center;color:#0d6efd;'>🎓 PG Nursing 2025 - Option Registration</h2>",
        unsafe_allow_html=True
    )
    st.markdown("<hr style='border:1px solid #ccc;'>", unsafe_allow_html=True)

    # --- Dummy Data (Replace with real tables) ---
    available_options = pd.DataFrame({
        "College": ["Govt. College of Nursing, Alappuzha (ALN)", "Govt. College of Nursing, Alappuzha (ALN)"],
        "Course": ["Child Health Nursing (CH)", "Community Health Nursing (CN)"],
        "Type": ["Govt./Aided", "Govt./Aided"],
        "Fee": ["₹32,410", "₹32,410"]
    })

    selected_options = pd.DataFrame({
        "College": ["Govt. College of Nursing, Alappuzha (ALN)", "Govt.College of Nursing, Pariyaram, Kannur. (KNN)"],
        "Course": ["Obstetrics & Gynaecology Nursing (OG)", "Medical Surgical Nursing (MS)"],
        "Type": ["Govt./Aided", "Govt./Aided"],
        "Fee": ["₹32,410", "₹32,410"]
    })

    # --- Layout with Two Columns ---
    left_col, right_col = st.columns([1, 1])

    # --- Left Column: Available Options ---
    with left_col:
        st.markdown("### 🏫 Available Options")
        search_text = st.text_input("🔍 Search by College/Course", key="search_available").lower()

        for _, row in available_options.iterrows():
            if search_text in row['College'].lower() or search_text in row['Course'].lower():
                st.markdown(
                    f"""
                    <div style='border:1px solid #ddd; border-radius:12px; padding:12px; margin-bottom:10px;
                               background:#f9f9f9; transition:0.2s;'>
                        <b>{row['College']}</b><br>
                        <span style='color:#0d6efd;font-weight:bold;'>{row['Course']}</span><br>
                        <small>Type: {row['Type']} | Tuition Fee: {row['Fee']}</small><br><br>
                        <button style='background-color:#28a745;color:white;border:none;padding:6px 12px;
                                       border-radius:8px;cursor:pointer;'>➕ Select</button>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # --- Right Column: Selected Options with Drag-and-Drop ---
    with right_col:
        st.markdown("### ⭐ Currently Selected")
        search_selected = st.text_input("🔍 Search in Selected", key="search_selected").lower()

        items = []
        for _, row in selected_options.iterrows():
            if search_selected in row['College'].lower() or search_selected in row['Course'].lower():
                items.append(
                    f"""
                    <div style='border:1px solid #ccc; border-radius:12px; padding:10px; background:white;'>
                        <b>{row['College']}</b><br>
                        <span style='color:#d63333;font-weight:bold;'>{row['Course']}</span><br>
                        <small>Type: {row['Type']} | Tuition Fee: {row['Fee']}</small>
                    </div>
                    """
                )

        if items:
            order = sort_items(items, direction="vertical", key="sortable_list")
            # order gives the new order after drag-and-drop
            # You can use it to reorder your dataframe
        else:
            st.info("No preferences added yet.")

    # --- Sticky Save Button ---
    st.markdown(
        """
        <style>
        .save-btn {
            position: fixed;
            bottom: 20px;
            right: 30px;
            background-color: #0d6efd;
            color: white;
            padding: 12px 20px;
            border-radius: 50px;
            font-size: 18px;
            font-weight: bold;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
            cursor: pointer;
            z-index: 999;
        }
        .save-btn:hover {
            background-color: #0b5ed7;
        }
        </style>
        <button class="save-btn" onclick="window.scrollTo(0, 0);">💾 Save</button>
        """,
        unsafe_allow_html=True
    )
