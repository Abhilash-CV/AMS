import streamlit as st
import pandas as pd
from common_functions import load_table, save_table, clean_columns

def student_option_ui(year: str, program: str, student_id: str = None):
    """
    Student Options Page (Improved UI/UX)
    - Displays available college-course data with clean formatting
    - Allows students to add & reorder preferences without duplicates
    - Saves preferences safely to storage
    """
    st.subheader("🎓 Student Options")

    # --- Load College-Course Master ---
    df_ccm = load_table("College Course Master", year, program)
    if df_ccm.empty:
        st.warning("⚠️ No College-Course Master data available for the selected year/program.")
        return

    df_ccm = clean_columns(df_ccm)

    # Ensure required columns exist
    required_cols = ["College", "CollegeType", "Course", "CourseCode", "CollegeCode", "FeeGeneral"]
    for col in required_cols:
        if col not in df_ccm.columns:
            df_ccm[col] = ""

    # Format Fee column
    if pd.api.types.is_numeric_dtype(df_ccm["FeeGeneral"]):
        df_ccm["FeeGeneral"] = df_ccm["FeeGeneral"].apply(lambda x: f"₹{x:,.0f}")

    st.markdown("### 🏫 Available Colleges and Courses")
    st.dataframe(
        df_ccm[required_cols].sort_values(["College", "Course"]).reset_index(drop=True),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # --- Load saved preferences ---
    df_saved = load_table("Student Options", year, program)
    if student_id and "StudentID" in df_saved.columns:
        df_saved = df_saved[df_saved["StudentID"] == student_id]

    st.markdown("### ⭐ Your Current Preferences")
    if df_saved.empty:
        st.info("No preferences saved yet.")
        df_saved = pd.DataFrame(columns=["StudentID", "College", "Course", "Preference"])
    else:
        df_saved = df_saved.sort_values("Preference").reset_index(drop=True)
        st.dataframe(df_saved, use_container_width=True, hide_index=True)

    st.divider()

    # --- Add New Preference ---
    st.markdown("### ➕ Add New Preference")
    col1, col2 = st.columns([1, 1])
    selected_college = col1.selectbox("🏫 Select College", df_ccm["College"].unique())
    filtered_courses = df_ccm[df_ccm["College"] == selected_college]["Course"].unique()
    selected_course = col2.selectbox("📚 Select Course", filtered_courses)

    if st.button("Add Preference"):
        if student_id is None:
            st.error("⚠️ StudentID missing. Cannot save preference.")
        else:
            # Prevent duplicates
            if ((df_saved["College"] == selected_college) & (df_saved["Course"] == selected_course)).any():
                st.warning("⚠️ This preference is already added.")
            else:
                new_pref = {
                    "StudentID": student_id,
                    "College": selected_college,
                    "Course": selected_course,
                    "Preference": len(df_saved) + 1
                }
                df_saved = pd.concat([df_saved, pd.DataFrame([new_pref])], ignore_index=True)
                st.success(f"✅ Preference added: {selected_college} - {selected_course}")

    st.divider()

    # --- Reorder Preferences ---
    st.markdown("### 🔀 Reorder Preferences")
    if not df_saved.empty:
        options = [f"{row['College']} - {row['Course']}" for _, row in df_saved.iterrows()]
        new_order = st.multiselect(
            "Drag to reorder (top = highest priority):",
            options=options,
            default=options
        )

        if new_order:
            order_map = {val: i+1 for i, val in enumerate(new_order)}
            df_saved["Preference"] = df_saved.apply(
                lambda row: order_map.get(f"{row['College']} - {row['Course']}"),
                axis=1
            )
            df_saved = df_saved.sort_values("Preference").reset_index(drop=True)

        st.dataframe(df_saved, use_container_width=True, hide_index=True)

    st.divider()

    # --- Save Preferences ---
    if st.button("💾 Save Preferences"):
        if student_id is None:
            st.error("⚠️ StudentID missing. Cannot save.")
        else:
            df_existing = load_table("Student Options", year, program)
            if "StudentID" in df_existing.columns:
                df_existing = df_existing[df_existing["StudentID"] != student_id]

            df_combined = pd.concat([df_existing, df_saved], ignore_index=True)
            save_table("Student Options", df_combined, append=False)
            st.success("✅ Preferences saved successfully!")

    # --- Admin Testing View ---
    if st.session_state.get("program") == "PGN" and student_id == "admin_test":
        st.divider()
        st.markdown("### 🛠️ Admin Test Mode: All Student Preferences")
        df_all = load_table("Student Options", year, program)
        if not df_all.empty:
            st.dataframe(df_all.sort_values(["StudentID", "Preference"]).reset_index(drop=True),
                         use_container_width=True,
                         hide_index=True)
        else:
            st.info("No preferences saved for any students yet.")
