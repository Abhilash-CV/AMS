import streamlit as st
import pandas as pd
from common_functions import load_table, save_table, clean_columns

def student_option_ui(year: str, program: str, student_id: str = None):
    """
    Student Options Page
    - Load College-Course Master data for selected year/program
    - Allow students to select college/course preferences
    - Save preferences safely
    """
    st.subheader("🎓 Student Options")

    # --- Load College-Course Master ---
    df_ccm = load_table("College Course Master", year, program)
    if df_ccm.empty:
        st.warning("⚠️ No College-Course Master data available for the selected year/program.")
        return

    # Clean columns
    df_ccm = clean_columns(df_ccm)

    # Ensure required columns exist
    required_cols = ["College", "Course", "CollegeType", "CoursePool", "Fee"]
    for col in required_cols:
        if col not in df_ccm.columns:
            df_ccm[col] = ""

    # --- Filter CCM for display ---
    st.markdown("Available Colleges and Courses:")
    st.dataframe(df_ccm[required_cols].sort_values(["College", "Course"]).reset_index(drop=True))

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

    # --- Select College-Course ---
    st.subheader("Add New Preference")
    col1, col2 = st.columns(2)
    selected_college = col1.selectbox("Select College", df_ccm["College"].unique())
    filtered_courses = df_ccm[df_ccm["College"] == selected_college]["Course"].unique()
    selected_course = col2.selectbox("Select Course", filtered_courses)

    if st.button("➕ Add Preference"):
        if student_id is None:
            st.error("StudentID missing. Cannot save preference.")
        else:
            new_pref = {
                "StudentID": student_id,
                "College": selected_college,
                "Course": selected_course,
                "Preference": len(df_saved) + 1
            }
            df_saved = pd.concat([df_saved, pd.DataFrame([new_pref])], ignore_index=True)
            st.success(f"Preference added: {selected_college} - {selected_course}")

    # --- Reorder Preferences ---
    st.subheader("Reorder Preferences")
    if not df_saved.empty:
        df_saved = df_saved.sort_values("Preference").reset_index(drop=True)
        new_order = st.multiselect(
            "Drag to reorder preferences (top = highest priority)",
            options=[f"{row['College']} - {row['Course']}" for _, row in df_saved.iterrows()],
            default=[f"{row['College']} - {row['Course']}" for _, row in df_saved.iterrows()]
        )

        # Update Preference column based on new order
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
            # Load existing table
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
