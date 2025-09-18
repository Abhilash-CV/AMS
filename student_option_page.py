# student_option_page.py
import streamlit as st
import pandas as pd
from common_functions import load_table, save_table

def student_option_ui(year: str, program: str, student_id: str = None):
    """
    UI for students to select college-course options.
    Admin test mode supported via student_id.
    """
    st.subheader("🎓 Student Options")

    # --- Load data ---
    df_col = load_table("College Master", year, program)
    df_course = load_table("Course Master", year, program)
    df_ccm = load_table("College-Course Master", year, program)
    df_saved = load_table("Student Options", year, program)

    # Ensure all column names are strings for .str operations
    for df in [df_col, df_course, df_ccm, df_saved]:
        df.columns = df.columns.astype(str).str.strip().str.lower()

    # --- Check availability ---
    if df_col.empty or df_course.empty or df_ccm.empty:
        st.warning("⚠️ No College/Course Master data available for the selected year/program.")
        return

    # --- Filter saved options for student ---
    if student_id:
        df_saved_student = df_saved[df_saved.get("studentid", "") == student_id].copy()
    else:
        df_saved_student = pd.DataFrame(columns=["studentid", "college", "course", "fee_general"])

    # --- College selection ---
    college_options = df_col["college_desc"].unique()
    selected_college = st.selectbox("Select College", college_options)

    # --- Course selection ---
    filtered_courses = df_ccm[df_ccm["college_desc"] == selected_college]
    if filtered_courses.empty:
        st.warning(f"No courses found for {selected_college}")
        return
    course_options = filtered_courses["course_desc"].unique()
    selected_course = st.selectbox("Select Course", course_options)

    # --- Show Fee ---
    fee_row = filtered_courses[filtered_courses["course_desc"] == selected_course]
    if not fee_row.empty:
        fee_general = fee_row.iloc[0].get("fee_general", 0)
    else:
        fee_general = 0
    st.markdown(f"**Fee (General):** {fee_general}")

    # --- Apply button ---
    if st.button("✅ Apply Option"):
        new_entry = pd.DataFrame([{
            "studentid": student_id,
            "college": selected_college,
            "course": selected_course,
            "fee_general": fee_general
        }])
        save_table("Student Options", new_entry, append=True)
        st.success(f"Option applied: {selected_college} - {selected_course}")

    # --- Display current selections with reorder ---
    df_saved_student = load_table("Student Options", year, program)
    if student_id:
        df_saved_student = df_saved_student[df_saved_student.get("studentid", "") == student_id]
    if not df_saved_student.empty:
        st.markdown("### Your Selected Options (Reorder if needed)")
        df_saved_student = df_saved_student.reset_index(drop=True)
        edited = st.data_editor(
            df_saved_student,
            num_rows="dynamic",
            use_container_width=True,
            key=f"student_options_editor_{student_id}"
        )
        if st.button("💾 Save Updated Order"):
            save_table("Student Options", edited, append=False)
            st.success("Updated options saved!")
