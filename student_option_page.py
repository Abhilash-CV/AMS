import streamlit as st
import pandas as pd

def student_option_ui_modern(year: str, program: str, student_id: str = None):
    st.markdown(
        "<h2 style='text-align:center;color:#0d6efd;'>🎓 PG Nursing 2025 - Option Registration</h2>",
        unsafe_allow_html=True
    )
    st.markdown("<hr style='border:1px solid #ccc;'>", unsafe_allow_html=True)

    # --- Layout: Two Columns ---
    left_col, right_col = st.columns([1, 1])

    # --- Dummy Data for UI Demo ---
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
        "Fee": ["₹32,410", "₹32,410"],
        "Preference": [1, 2]
    })

    # --- Left Column: Available Options ---
    with left_col:
        st.markdown("### 🏫 Available Options")
        st.text_input("🔍 Search by College/Course")
        for _, row in available_options.iterrows():
            with st.container():
                st.markdown(
                    f"""
                    <div style='border:1px solid #ddd; border-radius:12px; padding:12px; margin-bottom:10px; background:#f9f9f9;'>
                        <b>{row['College']}</b><br>
                        <span style='color:#0d6efd;font-weight:bold;'>{row['Course']}</span><br>
                        <small>Type: {row['Type']} | Tuition Fee: {row['Fee']}</small><br><br>
                        <button style='background-color:#28a745;color:white;border:none;padding:6px 12px;border-radius:8px;cursor:pointer;'>➕ Select</button>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # --- Right Column: Selected Options ---
    with right_col:
        st.markdown("### ⭐ Currently Selected")
        st.text_input("🔍 Search by College/Course")
        for _, row in selected_options.iterrows():
            with st.container():
                st.markdown(
                    f"""
                    <div style='border:1px solid #ccc; border-radius:12px; padding:12px; margin-bottom:10px; background:#fff;'>
                        <span style='background:#0d6efd;color:white;padding:4px 10px;border-radius:50%;font-size:0.9em;'>{row['Preference']}</span>
                        <b style='margin-left:8px;'>{row['College']}</b><br>
                        <span style='color:#d63333;font-weight:bold;'>{row['Course']}</span><br>
                        <small>Type: {row['Type']} | Tuition Fee: {row['Fee']}</small><br><br>
                        <button style='background-color:#ffc107;color:black;border:none;padding:6px 10px;border-radius:8px;cursor:pointer;'>⬆ Move Up</button>
                        <button style='background-color:#ffc107;color:black;border:none;padding:6px 10px;border-radius:8px;cursor:pointer;'>⬇ Move Down</button>
                        <button style='background-color:#dc3545;color:white;border:none;padding:6px 10px;border-radius:8px;cursor:pointer;'>🗑 Remove</button>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # --- Save Button at Bottom ---
    st.markdown("<hr style='border:1px solid #ccc;'>", unsafe_allow_html=True)
    st.button("💾 Save Preferences", type="primary", use_container_width=True)
