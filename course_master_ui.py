import pandas as pd
import streamlit as st
from utils import load_table, save_table, clean_columns, download_button_for_df, filter_and_sort_dataframe  # adjust imports if needed

def course_master_ui(year, program):
    st.subheader("📚 Course Master")
    
    # Load table data for selected year & program
    df_course = load_table("Course Master", year, program)
    
    # File uploader
    upload_key = f"upl_course_master_{year}_{program}"
    uploaded = st.file_uploader(
        "Upload Course Master (Excel/CSV)",
        type=["xlsx", "xls", "csv"],
        key=upload_key
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

            # Save with replacement for same year+program
            save_table("Course Master", df_new, replace_where={"AdmissionYear": year, "Program": program})
            df_course = load_table("Course Master", year, program)
            st.success("✅ Course Master uploaded successfully!")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    # Download + Filter + Edit
    download_button_for_df(df_course, f"Course Master_{year}_{program}")
    st.caption(f"Showing rows for **AdmissionYear={year} & Program={program}**")

    df_course_filtered = filter_and_sort_dataframe(df_course, "Course Master")
    edited_course = st.data_editor(
        df_course_filtered,
        num_rows="dynamic",
        use_container_width=True,
        key=f"data_editor_course_master_{year}_{program}",
    )

    if st.button("💾 Save Course Master", key=f"save_course_master_{year}_{program}"):
        if "AdmissionYear" not in edited_course.columns:
            edited_course["AdmissionYear"] = year
        if "Program" not in edited_course.columns:
            edited_course["Program"] = program
        save_table("Course Master", edited_course, replace_where={"AdmissionYear": year, "Program": program})
        st.success("✅ Course Master saved!")
        df_course = load_table("Course Master", year, program)

    # ---------- Course Master Danger Zone ----------
    with st.expander("🗑️ Danger Zone: Course Master"):
        st.error("⚠️ This action will permanently delete ALL Course Master data!")
        confirm_key = f"flush_confirm_course_{year}_{program}"
        if confirm_key not in st.session_state:
            st.session_state[confirm_key] = False

        st.session_state[confirm_key] = st.checkbox(
            "Yes, I understand this will delete all Course Master permanently.",
            value=st.session_state[confirm_key],
            key=f"flush_course_confirm_{year}_{program}"
        )

        if st.session_state[confirm_key]:
            if st.button("🚨 Flush All Course Master Data", key=f"flush_course_btn_{year}_{program}"):
                save_table("Course Master", pd.DataFrame(), replace_where=None)
                st.success("✅ All Course Master data cleared!")
                st.session_state[confirm_key] = False
                st.rerun()
