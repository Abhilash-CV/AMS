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

    # Generate unique key for each college-course
    df_cc["OptionKey"] = df_cc["College"] + " - " + df_cc["Course"]

    selected_options = st.multiselect(
        "Select your preferred College-Course combinations:",
        options=df_cc["OptionKey"].tolist()
    )

    if selected_options:
        # Get details for selected options
        df_selected = df_cc[df_cc["OptionKey"].isin(selected_options)].copy()

        st.markdown("### 🔢 Set Your Priority Order")

        # Add priority column using number inputs
        priorities = []
        for opt in df_selected["OptionKey"]:
            pri = st.number_input(
                f"Priority for {opt}",
                min_value=1,
                max_value=len(selected_options),
                step=1,
                value=1,
                key=f"priority_{opt}"
            )
            priorities.append(pri)

        df_selected["Priority"] = priorities
        df_selected = df_selected.sort_values("Priority")

        # Show ordered table
        st.write("✅ Your Ordered Preferences:")
        st.dataframe(
            df_selected[["Priority", "College", "Course", "CollegeType", "CoursePool", "Fee"]],
            use_container_width=True,
            hide_index=True
        )

        # --- Save button ---
        if st.button("💾 Finalize & Save Options"):
            save_table(
                "Student Options",
                df_selected.assign(StudentID=student_id, AdmissionYear=year, Program=program),
                append=True
            )
            st.success("🎉 Your preferences have been saved successfully!")
