import streamlit as st
import pandas as pd
from common_functions import load_table, save_table, clean_columns

def student_option_ui(year: str, program: str, student_id: str = None):
    """
    Student Options Page (Visually Enhanced)
    """
    st.markdown("## 🎓 Student Options", unsafe_allow_html=True)
    st.markdown("<hr style='border:1px solid #ddd;'>", unsafe_allow_html=True)

    # --- Load College-Course Master ---
    df_ccm = load_table("College Course Master", year, program)
    if df_ccm.empty:
        st.warning("⚠️ No College-Course Master data available for the selected year/program.")
        return

    df_ccm = clean_columns(df_ccm)
    required_cols = ["College", "CollegeType", "Course", "CourseCode", "CollegeCode", "FeeGeneral"]
    for col in required_cols:
        if col not in df_ccm.columns:
            df_ccm[col] = ""

    # Format Fee column nicely
    if pd.api.types.is_numeric_dtype(df_ccm["FeeGeneral"]):
        df_ccm["FeeGeneral"] = df_ccm["FeeGeneral"].apply(lambda x: f"₹{x:,.0f}")

    with st.container():
        st.markdown("### 🏫 Available Colleges & Courses")
        styled_ccm = (
            df_ccm[required_cols]
            .sort_values(["College", "Course"])
            .reset_index(drop=True)
            .style.set_table_styles([
                {"selector": "thead th", "props": "background-color: #f8f9fa; color: #333; text-align:center;"},
                {"selector": "tbody td", "props": "text-align:center;"}
            ])
        )
        st.dataframe(styled_ccm, use_container_width=True, hide_index=True)

    st.markdown("<hr style='border:1px dashed #bbb;'>", unsafe_allow_html=True)

    # --- Load saved preferences ---
    df_saved = load_table("Student Options", year, program)
    if student_id and "StudentID" in df_saved.columns:
        df_saved = df_saved[df_saved["StudentID"] == student_id]

    with st.container():
        st.markdown("### ⭐ Your Current Preferences")
        if df_saved.empty:
            st.info("ℹ️ No preferences saved yet. Add one below ⬇️")
            df_saved = pd.DataFrame(columns=["StudentID", "College", "Course", "Preference"])
        else:
            df_saved = df_saved.sort_values("Preference").reset_index(drop=True)
            df_saved["Priority"] = df_saved["Preference"].apply(lambda x: f"🔝 {x}")
            styled_saved = (
                df_saved[["Priority", "College", "Course"]]
                .style.set_table_styles([
                    {"selector": "thead th", "props": "background-color: #e7f3ff; color: #0d6efd; text-align:center;"},
                    {"selector": "tbody td", "props": "text-align:center; padding:6px;"}
                ])
            )
            st.dataframe(styled_saved, use_container_width=True, hide_index=True)

    st.markdown("<hr style='border:1px dashed #bbb;'>", unsafe_allow_html=True)

    # --- Add New Preference ---
    with st.container():
        st.markdown("### ➕ Add New Preference")
        col1, col2 = st.columns([1, 1])
        selected_college = col1.selectbox("🏫 Select College", df_ccm["College"].unique())
        filtered_courses = df_ccm[df_ccm["College"] == selected_college]["Course"].unique()
        selected_course = col2.selectbox("📚 Select Course", filtered_courses)

        if st.button("✅ Add Preference", use_container_width=True):
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
                    st.success(f"✅ Added: **{selected_college} - {selected_course}**")

    st.markdown("<hr style='border:1px dashed #bbb;'>", unsafe_allow_html=True)

    # --- Reorder Preferences ---
    if not df_saved.empty:
        with st.container():
            st.markdown("### 🔀 Reorder Preferences")
            options = [f"{row['College']} - {row['Course']}" for _, row in df_saved.iterrows()]
            new_order = st.multiselect(
                "Drag & drop to reorder (top = highest priority):",
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

            st.dataframe(df_saved[["Preference", "College", "Course"]],
                         use_container_width=True,
                         hide_index=True)

    st.markdown("<hr style='border:1px dashed #bbb;'>", unsafe_allow_html=True)

    # --- Save Preferences ---
    if st.button("💾 Save Preferences", type="primary", use_container_width=True):
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
        with st.expander("🛠️ Admin Test Mode: View All Preferences", expanded=False):
            df_all = load_table("Student Options", year, program)
            if not df_all.empty:
                st.dataframe(df_all.sort_values(["StudentID", "Preference"]).reset_index(drop=True),
                             use_container_width=True,
                             hide_index=True)
            else:
                st.info("No preferences saved yet.")
