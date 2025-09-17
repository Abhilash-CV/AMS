import pandas as pd
import streamlit as st
from common_functions import load_table, save_table, clean_columns, download_button_for_df, filter_and_sort_dataframe

def college_course_master_ui(year: str, program: str):
    """UI for College Course Master management"""
    st.subheader("🏫📚 College Course Master")

    # --- Load data ---
    df_cc = load_table("College Course Master", year, program)

    # --- Upload Section ---
    uploaded = st.file_uploader(
        "Upload College Course Master (Excel/CSV)",
        type=["xlsx", "xls", "csv"],
        key=f"upl_CollegeCourseMaster_{year}_{program}"
    )
    if uploaded:
        try:
            if uploaded.name.lower().endswith('.csv'):
                df_new = pd.read_csv(uploaded)
            else:
                df_new = pd.read_excel(uploaded)

            df_new = clean_columns(df_new)
            df_new["AdmissionYear"] = year
            df_new["Program"] = program

            # Deduplicate on College + Course if present
            dedup_cols = []
            if "College" in df_new.columns:
                dedup_cols.append("College")
            if "Course" in df_new.columns:
                dedup_cols.append("Course")

            if dedup_cols:
                df_new = df_new.drop_duplicates(subset=dedup_cols)

            save_table(
                "College Course Master",
                df_new,
                replace_where={"AdmissionYear": year, "Program": program}
            )
            df_cc = load_table("College Course Master", year, program)
            st.success("✅ College Course Master uploaded successfully!")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    # --- Download + Filter + Edit Section ---
    download_button_for_df(df_cc, f"CollegeCourseMaster_{year}_{program}")
    st.caption(f"Showing rows for **AdmissionYear={year} & Program={program}**")

    df_cc_filtered = filter_and_sort_dataframe(df_cc, "College Course Master")
    edited_cc = st.data_editor(
        df_cc_filtered,
        num_rows="dynamic",
        use_container_width=True,
        key=f"data_editor_CollegeCourseMaster_{year}_{program}"
    )

    # --- Save Button ---
    if st.button("💾 Save College Course Master", key=f"save_CollegeCourseMaster_{year}_{program}"):
        if "AdmissionYear" not in edited_cc.columns:
            edited_cc["AdmissionYear"] = year
        if "Program" not in edited_cc.columns:
            edited_cc["Program"] = program

        dedup_cols = []
        if "College" in edited_cc.columns:
            dedup_cols.append("College")
        if "Course" in edited_cc.columns:
            dedup_cols.append("Course")

        if dedup_cols:
            edited_cc = edited_cc.drop_duplicates(subset=dedup_cols)

        save_table(
            "College Course Master",
            edited_cc,
            replace_where={"AdmissionYear": year, "Program": program}
        )
        st.success("✅ College Course Master saved!")
        df_cc = load_table("College Course Master", year, program)

    # --- Danger Zone ---
    with st.expander("🗑️ Danger Zone: College Course Master"):
        st.error("⚠️ This will permanently delete ALL College Course Master data for this year/program!")

        confirm_key = f"flush_confirm_college_course_{year}_{program}"
        if confirm_key not in st.session_state:
            st.session_state[confirm_key] = False

        st.session_state[confirm_key] = st.checkbox(
            f"Yes, I understand this will delete College Course Master permanently for {year} - {program}.",
            value=st.session_state[confirm_key],
            key=f"flush_college_course_confirm_{year}_{program}"
        )

        if st.session_state[confirm_key]:
            if st.button("🚨 Flush College Course Master Data", key=f"flush_college_course_btn_{year}_{program}"):
                save_table("College Course Master", pd.DataFrame(), replace_where={"AdmissionYear": year, "Program": program})
                st.success(f"✅ College Course Master data cleared for {year} - {program}!")
                st.session_state[confirm_key] = False
                st.rerun()
