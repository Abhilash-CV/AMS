import streamlit as st
import pandas as pd
from common_functions import load_table, save_table, clean_columns

def student_option_ui(year: str, program: str, student_id: str = None):
    """
    Student Options Page
    - Select College from College Master
    - Select Course from College-Course Master filtered by College
    - Show CollegeType, CourseCode, CollegeCode, FeeGeneral
    - Save and reorder preferences
    """
    st.subheader("🎓 Student Options")

    # --- Load College Master and College-Course Master ---
    df_col = load_table("College Master", year, program)
    df_ccm = load_table("College Course Master", year, program)

    if df_col.empty or df_ccm.empty:
        st.warning("⚠️ College or College-Course Master data not available for the selected year/program.")
        return

    df_col = clean_columns(df_col)
    df_ccm = clean_columns(df_ccm)

    # Ensure required columns exist
    required_cols = ["collge_desc", "CollegeType", "Course", "CourseCode", "CollegeCode", "FeeGeneral"]
    for col in required_cols:
        if col not in df_ccm.columns:
            df_ccm[col] = ""

    # --- Display Available Colleges ---
    st.markdown("Available Colleges:")
    st.dataframe(df_col.sort_values("College").reset_index(drop=True))

    # --- Load previously saved student preferences ---
    df_saved = load_table("Student Options", year, program)
    if student_id and "StudentID" in df_saved.columns:
        df_saved = df_saved[df_saved["StudentID"] == student_id]

    st.subheader("Your Current Preferences")
    if df_saved.empty:
        st.info("No preferences saved yet.")
        df_saved = pd.DataFrame(columns=["StudentID", "College", "Course", "Preference"])
    else:
        st.dataframe(df_saved.sort_values("Preference").reset_index(drop=True))

    # --- Select College & Course ---
    st.subheader("Add New Preference")
    selected_college = st.selectbox("Select College", df_col["College"].unique())
    
    # Filter courses by selected college
    filtered_courses = df_ccm[df_ccm["College"] == selected_college]
    course_display = filtered_courses.apply(lambda row: f"{row['Course']} ({row['CourseCode']}, Fee: {row['FeeGeneral']})", axis=1)
    selected_course = st.selectbox("Select Course", course_display)

    if st.button("➕ Add Preference"):
        if student_id is None:
            st.error("StudentID missing. Cannot save preference.")
        else:
            # Map back to actual course row
            course_row = filtered_courses.iloc[course_display.tolist().index(selected_course)]
            new_pref = {
                "StudentID": student_id,
                "College": selected_college,
                "Course": course_row["Course"],
                "CourseCode": course_row["CourseCode"],
                "CollegeCode": course_row["CollegeCode"],
                "FeeGeneral": course_row["FeeGeneral"],
                "Preference": len(df_saved) + 1
            }
            df_saved = pd.concat([df_saved, pd.DataFrame([new_pref])], ignore_index=True)
            st.success(f"Preference added: {selected_college} - {course_row['Course']}")

    # --- Reorder Preferences ---
    st.subheader("Reorder Preferences")
    if not df_saved.empty:
        df_saved = df_saved.sort_values("Preference").reset_index(drop=True)
        new_order = st.multiselect(
            "Drag to reorder preferences (top = highest priority)",
            options=[f"{row['College']} - {row['Course']}" for _, row in df_saved.iterrows()],
            default=[f"{row['College']} - {row['Course']}" for _, row in df_saved.iterrows()]
        )
        if new_order:
            mapping = {val: i+1 for i, val in enumerate(new_order)}
            df_saved["Preference"] = df_saved.apply(
                lambda row: mapping.get(f"{row['College']} - {row['Course']}", row["Preference"]),
                axis=1
            )

    st.dataframe(df_saved.sort_values("Preference").reset_index(drop=True))

    # --- Save Preferences ---
    if st.button("💾 Save Preferences"):
        if student_id is None:
            st.error("StudentID missing. Cannot save.")
        else:
            df_existing = load_table("Student Options", year, program)
            if df_existing.empty:
                df_existing = pd.DataFrame(columns=df_saved.columns)

            # Remove previous entries for this student
            if "StudentID" in df_existing.columns:
                df_existing = df_existing[df_existing["StudentID"] != student_id]

            # Combine and save
            df_combined = pd.concat([df_existing, df_saved], ignore_index=True)
            save_table("Student Options", df_combined, append=False)
            st.success("✅ Preferences saved successfully!")

    # --- Admin Testing View ---
    if st.session_state.get("program") == "PGN" and student_id == "admin_test":
        st.subheader("Admin Test Mode: All Preferences for PGN")
        st.dataframe(df_saved.sort_values("Preference").reset_index(drop=True))
