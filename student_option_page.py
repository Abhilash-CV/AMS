import streamlit as st
import pandas as pd
from streamlit_sortables import sort_items
from common_functions import load_table, save_table, clean_columns

def student_option_ui(year: str, program: str, student_id: str = None):
    st.markdown("<h2 style='text-align:center;'>🎓 Student Option Selection</h2>", unsafe_allow_html=True)

    # --- Load College-Course Master ---
    df_ccm = load_table("College Course Master", year, program)
    if df_ccm.empty:
        st.warning("⚠️ No College-Course Master data available.")
        return

    df_ccm = clean_columns(df_ccm)
    required_cols = ["College", "CollegeType", "Course", "CourseCode", "CollegeCode", "FeeGeneral"]
    for col in required_cols:
        if col not in df_ccm.columns:
            df_ccm[col] = ""

    # --- Filters ---
    st.markdown("### 🔍 Search & Filter")
    search_query = st.text_input("Search by College / Course").lower()
    college_type_filter = st.selectbox("Institution Type", ["All"] + sorted(df_ccm["CollegeType"].unique()))

    filtered_df = df_ccm.copy()
    if search_query:
        filtered_df = filtered_df[
            filtered_df["College"].str.lower().str.contains(search_query) |
            filtered_df["Course"].str.lower().str.contains(search_query)
        ]
    if college_type_filter != "All":
        filtered_df = filtered_df[filtered_df["CollegeType"] == college_type_filter]

    col_left, col_right = st.columns(2)

    # --- Left Panel : Available Options ---
    with col_left:
        st.markdown("### 📋 Available Options")
        for _, row in filtered_df.iterrows():
            st.markdown(f"""
            <div style="border:1px solid #ddd; border-radius:12px; padding:10px; margin-bottom:10px; box-shadow:0 2px 4px rgba(0,0,0,0.05)">
                <strong>{row['College']}</strong><br>
                <span style="color:#0d6efd; font-weight:bold;">{row['Course']}</span><br>
                <small>Type: {row['CollegeType']} | Fee: <b>{row['FeeGeneral']}</b></small><br>
                <button style="margin-top:5px; background:#28a745; color:white; border:none; padding:5px 10px; border-radius:8px;">➕ Select</button>
            </div>
            """, unsafe_allow_html=True)

    # --- Load & Show Saved Preferences ---
    df_saved = load_table("Student Options", year, program)
    if student_id and "StudentID" in df_saved.columns:
        df_saved = df_saved[df_saved["StudentID"] == student_id]

    with col_right:
        st.markdown("### ✅ Your Selected Preferences")
        if df_saved.empty:
            st.info("No preferences saved yet.")
        else:
            sorted_items = [f"{row['College']} - {row['Course']}" for _, row in df_saved.sort_values("Preference").iterrows()]
            result = sort_items(sorted_items, multi_containers=False, direction="vertical")
            st.session_state["sorted_preferences"] = result  # store new order

            # Show ordered list with delete buttons
            for idx, val in enumerate(result, start=1):
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; 
                            border:1px solid #ddd; border-radius:12px; padding:8px; margin-bottom:8px;">
                    <span><b>{idx}. {val}</b></span>
                    <button style="background:#dc3545; color:white; border:none; padding:5px 10px; border-radius:8px;">🗑️</button>
                </div>
                """, unsafe_allow_html=True)

    # --- Sticky Save Button ---
    st.markdown("""
    <div style="position:fixed; bottom:10px; left:0; width:100%; text-align:center;">
        <button style="background:#0d6efd; color:white; font-size:18px; padding:10px 30px; 
                       border:none; border-radius:10px; box-shadow:0 4px 8px rgba(0,0,0,0.2);">
        💾 Save Preferences
        </button>
    </div>
    """, unsafe_allow_html=True)
