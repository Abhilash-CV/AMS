import streamlit as st
import pandas as pd
from streamlit_sortables import sort_items
from common_functions import load_table, save_table, clean_columns
from uuid import uuid4

def student_option_ui(year: str, program: str, student_id: str = None):
    st.markdown(
        """
        <style>
        /* --- Global Modern Look --- */
        .option-card {
            background: linear-gradient(145deg, #ffffff, #f9fafc);
            border-radius: 16px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 14px rgba(0,0,0,0.06);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .option-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.12);
        }
        .badge {
            display:inline-block;
            padding: 4px 10px;
            font-size: 0.75rem;
            border-radius: 20px;
            font-weight: 500;
            margin-right: 6px;
        }
        .badge-govt { background-color: #e0f7ec; color: #0f5132; }
        .badge-private { background-color: #fde2e1; color: #842029; }
        .pref-card {
            background: white;
            border-radius: 14px;
            padding: 0.8rem;
            margin-bottom: 0.6rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        .save-btn {
            position: fixed;
            bottom: 22px;
            right: 22px;
            background: linear-gradient(135deg, #0d6efd, #0a58ca);
            color: white;
            border-radius: 50%;
            width: 62px;
            height: 62px;
            font-size: 26px;
            box-shadow: 0 6px 14px rgba(0,0,0,0.25);
            border: none;
        }
        .save-btn:hover {
            background: linear-gradient(135deg, #0b5ed7, #084298);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<h2 style='text-align:center; margin-bottom:1.2rem;'>🎓 Student Options</h2>", unsafe_allow_html=True)

    # Load CCM
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
    col_search, col_filter = st.columns([2, 1])
    with col_search:
        search_query = st.text_input("Search by College or Course").lower()
    with col_filter:
        college_type_filter = st.selectbox("College Type", ["All"] + sorted(df_ccm["CollegeType"].unique()))

    filtered_df = df_ccm.copy()
    if search_query:
        filtered_df = filtered_df[
            filtered_df["College"].str.lower().str.contains(search_query) |
            filtered_df["Course"].str.lower().str.contains(search_query)
        ]
    if college_type_filter != "All":
        filtered_df = filtered_df[filtered_df["CollegeType"] == college_type_filter]

    col_left, col_right = st.columns([2, 1])

    # --- Left Panel: Available Options ---
    with col_left:
        st.markdown("### 📋 Available Options")
        if filtered_df.empty:
            st.info("No matching results.")
        else:
            for _, row in filtered_df.iterrows():
                badge_class = "badge-govt" if row['CollegeType'].lower() == "govt" else "badge-private"
                uid = str(uuid4())
                st.markdown(f"""
                <div class="option-card">
                    <h4 style="margin:0;">{row['College']}</h4>
                    <p style="margin:0; font-weight:600; color:#0d6efd;">{row['Course']}</p>
                    <div style="margin:6px 0;">
                        <span class="badge {badge_class}">{row['CollegeType']}</span>
                        <span class="badge" style="background:#eef2ff; color:#1e3a8a;">💰 Fee: {row['FeeGeneral']}</span>
                    </div>
                    <button style="background:#198754; color:white; padding:6px 14px; border:none; border-radius:8px; font-weight:500;">➕ Add</button>
                </div>
                """, unsafe_allow_html=True)

    # --- Right Panel: Preferences ---
    df_saved = load_table("Student Options", year, program)
    if student_id and "StudentID" in df_saved.columns:
        df_saved = df_saved[df_saved["StudentID"] == student_id]

    with col_right:
        st.markdown("### ✅ Your Preferences")
        if df_saved.empty:
            st.info("No preferences saved yet.")
        else:
            sorted_items = [
                f"{row['College']} - {row['Course']}"
                for _, row in df_saved.sort_values("Preference").iterrows()
            ]
            result = sort_items(sorted_items, multi_containers=False, direction="vertical")
            st.session_state["sorted_preferences"] = result
            for idx, val in enumerate(result, start=1):
                st.markdown(f"""
                <div class="pref-card">
                    <span><b>{idx}. {val}</b></span>
                    <button style="background:#dc3545; color:white; border:none; padding:4px 10px; border-radius:8px;">🗑 Remove</button>
                </div>
                """, unsafe_allow_html=True)

    # Floating Save Button
    st.markdown('<button class="save-btn">💾</button>', unsafe_allow_html=True)
