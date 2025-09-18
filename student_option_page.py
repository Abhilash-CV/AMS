import streamlit as st
import pandas as pd
from common_functions import load_table, save_table

def student_option_ui(year, program, student_id):
    st.subheader("📝 Student Options")

    # Load Masters
    df_col = load_table("College Master", year, program)
    df_course = load_table("Course Master", year, program)
    df_ccm = load_table("College-Course Master", year, program)
    df_saved = load_table("Student Options", year, program)

    # Standardize columns
    for df in [df_col, df_course, df_ccm, df_saved]:
        df.columns = df.columns.str.strip().str.lower()

    if df_ccm.empty or df_col.empty or df_course.empty:
        st.warning("⚠️ Required College/Course Master data missing for this year/program.")
        return

    # Filter saved options for this student
    df_student = df_saved[df_saved.get("studentid", pd.Series([])) == student_id].copy()

    # --- Add New Option ---
    st.markdown("### Add New Option")
    
    # Select College
    college_options = df_col.set_index("college")["collegedesc"].to_dict()
    selected_college = st.selectbox(
        "Select College",
        options=list(college_options.keys()),
        format_func=lambda x: college_options[x]
    )

    # Select Course
    filtered_ccm = df_ccm[df_ccm["college"] == selected_college]
    course_options = filtered_ccm.set_index("course")["coursedesc"].to_dict()
    selected_course = st.selectbox(
        "Select Course",
        options=list(course_options.keys()),
        format_func=lambda x: course_options[x]
    )

    # Fee
    fee_general = filtered_ccm.loc[filtered_ccm["course"] == selected_course, "feegeneral"].values[0]
    st.markdown(f"**Fee (General):** ₹{fee_general}")

    # Apply option
    if st.button("➕ Apply Option"):
        new_option = pd.DataFrame([{
            "studentid": student_id,
            "year": year,
            "program": program,
            "college": selected_college,
            "collegedesc": college_options[selected_college],
            "course": selected_course,
            "coursedesc": course_options[selected_course],
            "feegeneral": fee_general
        }])
        save_table("Student Options", new_option, append=True)
        st.success("✅ Option added!")
        st.experimental_rerun()

    # --- Display & Reorder Options ---
    st.markdown("### Your Selected Options")
    if not df_student.empty:
        df_student = df_student.sort_values("studentid")  # initial order
        edited = st.data_editor(
            df_student,
            num_rows="dynamic",
            use_container_width=True,
            key=f"student_options_editor_{student_id}"
        )
        if st.button("💾 Save Reordered Options"):
            save_table("Student Options", edited, append=False)  # overwrite all options for this student
            st.success("✅ Options reordered/saved!")
            st.experimental_rerun()
    else:
        st.info("No options selected yet.")
