import streamlit as st
import pandas as pd
from streamlit_sortables import sort_items
from common_functions import load_table, save_table, clean_columns

def student_option_ui(year: str, program: str, student_id: str = None):
    st.markdown(
        """
        <style>
        /* --- General Styling --- */
        .option-card {
            background: rgba(255, 255, 255, 0.85);
            border-radius: 16px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .option-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 18px rgba(0,0,0,0.1);
        }
        .badge {
            display:inline-block;
            padding: 2px 8px;
            font-size: 0.8rem;
            border-radius: 12px;
            font-weight: 500;
            margin-right: 6px;
        }
        .badge-govt { background-color: #d4edda; color: #155724; }
        .badge-private { background-color: #f8d7da; color: #721c24; }
        .pref-card {
            background: white;
            border-radius: 12px;
            padding: 0.7rem;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .save-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #0d6efd;
            color: white;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            font-size: 24px;
            box-shadow: 0 6px 12px rgba(0,0,0,0.2);
            border: none;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<h2 style='text-align:center;'>🎓 Student Options</h2>", unsafe_allow_html=True)

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
    st.markdown("### 🔍 Find a College/Course")
    search_query = st.text_input("Search by College or Course").lower()
    college_type_filter = st.selectbox("Filter by Type", ["All"] + sorted(df_ccm["CollegeType"].unique()))

    filtered_df = df_ccm.copy()
    if search_query:
        filtered_df = filtered_df[
            filtered_df["College"].str.lower().str.contains(search_query) |
            filtered_df["Course"].str.lower().str.contains(search_query)
        ]
    if college_type_filter != "All":
        filtered_df = filtered_df[filtered_df["CollegeType"] == college_type_filter]

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("### 📋 Available Options")
        for _, row in filtered_df.iterrows():
            badge_class = "badge-govt" if row['CollegeType'].lower() == "govt" else "badge-private"
            st.markdown(f"""
            <div class="option-card">
                <h4 style="margin:0;">{row['College']}</h4>
                <p style="margin:0; font-weight:600; color:#0d6efd;">{row['Course']}</p>
                <span class="badge {badge_class}">{row['CollegeType']}</span>
                <span class="badge" style="background:#e2e3e5; color:#383d41;">Fee: {row['FeeGeneral']}</span>
                <br><br>
                <button style="background:#28a745; color:white; padding:6px 12px; border:none; border-radius:10px;">➕ Add</button>
            </div>
            """, unsafe_allow_html=True)

    df_saved = load_table("Student Options", year, program)
    if student_id and "StudentID" in df_saved.columns:
        df_saved = df_saved[df_saved["StudentID"] == student_id]

    with col_right:
        st.markdown("### ✅ Your Preferences")
        if df_saved.empty:
            st.info("No preferences saved yet.")
        else:
            sorted_items = [f"{row['College']} - {row['Course']}" for _, row in df_saved.sort_values("Preference").iterrows()]
            result = sort_items(sorted_items, multi_containers=False, direction="vertical")
            st.session_state["sorted_preferences"] = result
            for idx, val in enumerate(result, start=1):
                st.markdown(f"""
                <div class="pref-card">
                    <span><b>{idx}. {val}</b></span>
                    <button style="background:#dc3545; color:white; border:none; padding:4px 10px; border-radius:8px;">🗑</button>
                </div>
                """, unsafe_allow_html=True)

    st.markdown('<button class="save-btn">💾</button>', unsafe_allow_html=True)
