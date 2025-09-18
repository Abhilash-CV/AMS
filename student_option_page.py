import streamlit as st
import pandas as pd
from common_functions import load_table, save_table, clean_columns

def student_option_ui(year: str, program: str, student_id: str = None):
    # --- Custom CSS for Modern Look ---
    st.markdown(
        """
        <style>
        .pref-card {
            background: white;
            border-radius: 12px;
            padding: 0.8rem;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .pref-buttons button {
            margin-left: 6px;
            border: none;
            border-radius: 8px;
            padding: 4px 8px;
            cursor: pointer;
            font-size: 16px;
        }
        .btn-up { background-color: #0dcaf0; color: white; }
        .btn-down { background-color: #ffc107; color: white; }
        .btn-del { background-color: #dc3545; color: white; }
        .add-btn {
            background: #28a745; 
            color: white; 
            border-radius: 8px; 
            border: none; 
            padding: 6px 16px;
            margin-top: 8px;
            font-size: 16px;
        }
        .save-btn {
            background: #0d6efd; 
            color: white; 
            border-radius: 10px;
            padding: 10px 20px;
            font-size: 18px;
            margin-top: 10px;
            border: none;
            box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<h2 style='text-align:center;'>🎓 Student Options</h2>", unsafe_allow_html=True)

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

    # --- Load previously saved preferences ---
    df_saved = load_table("Student Options", year, program)
    if "StudentID" in df_saved.columns and student_id:
        df_saved = df_saved[df_saved["StudentID"] == student_id]

    # ✅ Safe handling of Preference column
    if not df_saved.empty and "Preference" in df_saved.columns:
        prefs_list = df_saved.sort_values("Preference")[["College", "Course"]].to_dict(orient="records")
    else:
        prefs_list = []

    if "preferences" not in st.session_state:
        st.session_state.preferences = prefs_list

    prefs = st.session_state.preferences

    # --- Display Current Preferences ---
    st.subheader("✅ Your Preferences")
    if not prefs:
        st.info("No preferences saved yet.")
    else:
        for idx, pref in enumerate(prefs):
            col1, col2, col3, col4 = st.columns([6, 1, 1, 1])
            with col1:
                st.markdown(
                    f"<div class='pref-card'><b>{idx+1}. {pref['College']} - {pref['Course']}</b></div>",
                    unsafe_allow_html=True
                )
            with col2:
                if st.button("⬆", key=f"up_{idx}"):
                    if idx > 0:
                        prefs[idx - 1], prefs[idx] = prefs[idx], prefs[idx - 1]
                        st.experimental_rerun()
            with col3:
                if st.button("⬇", key=f"down_{idx}"):
                    if idx < len(prefs) - 1:
                        prefs[idx + 1], prefs[idx] = prefs[idx], prefs[idx + 1]
                        st.experimental_rerun()
            with col4:
                if st.button("🗑", key=f"del_{idx}"):
                    prefs.pop(idx)
                    st.experimental_rerun()

    # --- Add New Preference ---
    st.subheader("➕ Add New Preference")
    col1, col2 = st.columns(2)
    selected_college = col1.selectbox("Select College", df_ccm["College"].unique())
    filtered_courses = df_ccm[df_ccm["College"] == selected_college]["Course"].unique()
    selected_course = col2.selectbox("Select Course", filtered_courses)

    if st.button("Add Preference"):
        prefs.append({"College": selected_college, "Course": selected_course})
        st.success(f"Added: {selected_college} - {selected_course}")
        st.experimental_rerun()

    # --- Save Preferences ---
    if st.button("💾 Save Preferences", key="save", help="Save your final preference order"):
        if student_id is None:
            st.error("StudentID missing. Cannot save.")
        else:
            df_existing = load_table("Student Options", year, program)
            if df_existing.empty:
                df_existing = pd.DataFrame(columns=["StudentID", "College", "Course", "Preference"])

            # Remove old entries for this student
            df_existing = df_existing[df_existing["StudentID"] != student_id]

            # Build new dataframe with updated preferences
            df_new = pd.DataFrame([
                {"StudentID": student_id, "College": p["College"], "Course": p["Course"], "Preference": i+1}
                for i, p in enumerate(prefs)
            ])
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            save_table("Student Options", df_combined, append=False)
            st.success("✅ Preferences saved successfully!")
