import streamlit as st
import pandas as pd
from common_functions import load_table, save_table, clean_columns

def student_option_ui(year: str, program: str, student_id="admin_test"):
    """
    Student Options Page
    Admin/Test mode by default. Students can select and reorder course options.
    """
    st.subheader("🎯 Student Options Application")

    # --- Load College-Course Master ---
    df_cc = load_table("College-Course Master", year, program)

    if df_cc.empty:
        st.warning("⚠️ No College-Course Master data available for the selected year/program.")
        return

    # Ensure AdmissionYear & Program columns are strings
    df_cc["AdmissionYear"] = df_cc["AdmissionYear"].astype(str)
    df_cc["Program"] = df_cc["Program"].astype(str)

    # Filter for exact year & program match
    df_cc_filtered = df_cc[(df_cc["AdmissionYear"] == str(year)) & (df_cc["Program"] == str(program))]

    if df_cc_filtered.empty:
        st.warning("⚠️ No courses found for the selected year/program after filtering.")
        return

    st.info(f"Loaded {len(df_cc_filtered)} courses for Year={year}, Program={program}")

    # --- Show all courses (Admin/Test view) ---
    st.subheader("Available Courses")
    st.dataframe(df_cc_filtered.reset_index(drop=True))

    # --- Option selection by student/admin ---
    st.subheader("Apply for Options")
    st.markdown("Select courses from the available pool and arrange your preference:")

    course_pool = df_cc_filtered["Course"].tolist()
    if not course_pool:
        st.warning("No courses available to apply for.")
        return

    # Multiselect to choose courses
    selected_courses = st.multiselect(
        "Select your desired courses:",
        options=course_pool,
        default=course_pool[:3],  # default first 3 for testing
        help="Select multiple courses you want to apply for"
    )

    if not selected_courses:
        st.info("No courses selected yet.")
        return

    # Reordering interface using text inputs (simple for testing)
    st.markdown("**Reorder your selected courses (1 = highest priority):**")
    reordered_courses = []
    for i, course in enumerate(selected_courses):
        priority = st.number_input(f"Priority for {course}", min_value=1, max_value=len(selected_courses), value=i+1, step=1, key=f"prio_{i}")
        reordered_courses.append((priority, course))

    # Sort by priority
    reordered_courses.sort(key=lambda x: x[0])
    final_course_order = [c for _, c in reordered_courses]

    st.success("✅ Your course options in order of preference:")
    st.write(final_course_order)

    # --- Show fee & college type for selected courses ---
    st.subheader("Course Details for Selected Options")
    df_selected = df_cc_filtered[df_cc_filtered["Course"].isin(final_course_order)]
    st.dataframe(df_selected.reset_index(drop=True))

    # --- Save student application (Admin/Test mode) ---
    if st.button("💾 Save Student Option (Test)"):
        application_df = pd.DataFrame({
            "StudentID": student_id,
            "Year": year,
            "Program": program,
            "SelectedCourses": final_course_order
        }, index=[0])
        save_table("Student Options", application_df, append=True)  # append mode
        st.success("✅ Student options saved successfully (Test mode).")
