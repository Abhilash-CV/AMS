# student_option_page.py
import streamlit as st
import pandas as pd
from common_functions import load_table, save_table

def student_option_ui(year: str, program: str, student_id: str = "test_student"):
    """
    Student Option Entry Page (Admin/Test Version)
    - year, program => Admission Year & Program context
    - student_id => Student identifier (for now default as test_student)
    """

    st.subheader("🎓 Student Option Entry (Sample Page for Testing)")

    # --- Load College-Course Master ---
    df_cc = load_table("College-Course Master", year, program)

    if df_cc.empty:
        st.warning("⚠️ No College-Course Master data available.")
        return

    # --- Show available courses ---
    st.caption(f"Available Options for AdmissionYear={year}, Program={program}")
    st.dataframe(
        df_cc[["College", "Course", "CollegeType", "CoursePool", "Fee"]],
        use_container_width=True,
        hide_index=True
    )

    # --- Student Option Selection ---
    st.markdown("### 📝 Apply for Options")

    # Multi-select College-Course combinations
    df_cc["OptionKey"] = df_cc["College"] + " - " + df_cc["Course"]

    selected_options = st.multiselect(
        "Select your preferred College-Course combinations:",
        options=df_cc["OptionKey"].tolist()
    )

    if selected_options:
        # Map back to details
        df_selected = df_cc[df_cc["OptionKey"].isin(selected_options)]
        st.write("✅ Your Selected Options:")
        st.dataframe(
            df_selected[["College", "Course", "CollegeType", "CoursePool", "Fee"]],
            use_container_width=True,
            hide_index=True
        )

        # --- Save button ---
        if st.button("💾 Save Student Options"):
            save_table(
                "Student Options",
                df_selected.assign(StudentID=student_id, AdmissionYear=year, Program=program),
                append=True
            )
            st.success("🎉 Options saved successfully for testing!")
