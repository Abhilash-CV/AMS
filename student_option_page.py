import streamlit as st
import pandas as pd
from common_functions import load_table, save_table

def student_option_ui(year: str, program: str, student_id: str = None):
    """
    Student Options Page
    - Pulls College-Course Master data
    - Allows students to select/reorder preferences
    - student_id: optional, for admin/test purposes
    """
    st.subheader("🎯 Student Option Selection")

    # --- Load College-Course Master ---
    df_cc = load_table("College Course Master", year, program)

    if df_cc.empty:
        st.warning(f"⚠️ No College-Course Master data available for AdmissionYear={year}, Program={program}.")
        return

    # --- Clean and standardize columns ---
    df_cc.columns = df_cc.columns.str.replace(" ", "").str.strip()
    df_cc["AdmissionYear"] = df_cc["AdmissionYear"].astype(str).str.strip()
    df_cc["Program"] = df_cc["Program"].astype(str).str.strip()

    year_str = str(year).strip()
    program_str = str(program).strip()

    df_filtered = df_cc[
        (df_cc["AdmissionYear"] == year_str) &
        (df_cc["Program"] == program_str)
    ]

    if df_filtered.empty:
        st.warning(f"⚠️ No College-Course Master data available for selected year/program.")
        return

    # --- Show available options ---
    st.info("Select your preferred options. You can reorder before final submission.")

    # Columns to display
    display_cols = ["College", "CollegeType", "Course", "Fee"]
    for col in display_cols:
        if col not in df_filtered.columns:
            df_filtered[col] = "N/A"

    df_display = df_filtered[display_cols].copy()

    # --- Add Preference column if missing ---
    if "Preference" not in df_display.columns:
        df_display["Preference"] = range(1, len(df_display) + 1)

    # --- Editable table for students/admin ---
    edited_df = st.data_editor(
        df_display,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Preference": st.column_config.NumberColumn(
                "Preference",
                min_value=1,
                max_value=len(df_display),
                step=1,
                help="Reorder your preferences (1 = highest)"
            )
        },
        key=f"student_options_editor_{year}_{program}_{student_id}"
    )

    # --- Save/Submit preferences ---
    if st.button("💾 Save Preferences"):
        df_to_save = edited_df.copy()
        df_to_save["AdmissionYear"] = year
        df_to_save["Program"] = program
        if student_id:
            df_to_save["StudentID"] = student_id
        save_table("Student Options", df_to_save, append=True)
        st.success("✅ Preferences saved successfully!")

    # --- Show previously saved preferences ---
    st.subheader("Saved Preferences")
    df_saved = load_table("Student Options", year, program)
    if student_id:
        df_saved = df_saved[df_saved.get("StudentID", "") == student_id]

    if not df_saved.empty:
        st.dataframe(df_saved.sort_values("Preference").reset_index(drop=True))
    else:
        st.info("No saved preferences yet.")
