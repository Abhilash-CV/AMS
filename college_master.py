import pandas as pd
import streamlit as st
from common_functions import load_table, save_table, clean_columns, download_button_for_df, filter_and_sort_dataframe

def college_master_ui(year: str, program: str):
    """UI for College Master management"""
    st.subheader("🏫 College Master")

    # --- Load data ---
    df_col = load_table("College Master", year, program)

    # --- Upload Section ---
    uploaded = st.file_uploader(
        "Upload College Master (Excel/CSV)",
        type=["xlsx", "xls", "csv"],
        key=f"upl_CollegeMaster_{year}_{program}"
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

            # Deduplicate only by College column if present
            dedup_cols = ["College"] if "College" in df_new.columns else None
            if dedup_cols:
                df_new = df_new.drop_duplicates(subset=dedup_cols)

            save_table(
                "College Master",
                df_new,
                replace_where={"AdmissionYear": year, "Program": program}
            )
            df_col = load_table("College Master", year, program)
            st.success("✅ College Master uploaded successfully!")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    # --- Download + Filter + Edit Section ---
    download_button_for_df(df_col, f"College Master_{year}_{program}")
    st.caption(f"Showing rows for **AdmissionYear={year} & Program={program}**")

    df_col_filtered = filter_and_sort_dataframe(df_col, "College Master")
    edited_col = st.data_editor(
        df_col_filtered,
        num_rows="dynamic",
        use_container_width=True,
        key=f"data_editor_CollegeMaster_{year}_{program}"
    )

    # --- Save Button ---
    if st.button("💾 Save College Master", key=f"save_CollegeMaster_{year}_{program}"):
        if "AdmissionYear" not in edited_col.columns:
            edited_col["AdmissionYear"] = year
        if "Program" not in edited_col.columns:
            edited_col["Program"] = program

        dedup_cols = ["College"] if "College" in edited_col.columns else None
        if dedup_cols:
            edited_col = edited_col.drop_duplicates(subset=dedup_cols)

        save_table(
            "College Master",
            edited_col,
            replace_where={"AdmissionYear": year, "Program": program}
        )
        st.success("✅ College Master saved!")
        df_col = load_table("College Master", year, program)

    # --- Danger Zone ---
    with st.expander("🗑️ Danger Zone: College Master"):
        st.error("⚠️ This will permanently delete ALL College Master data for this year/program!")

        confirm_key = f"flush_confirm_college_{year}_{program}"
        if confirm_key not in st.session_state:
            st.session_state[confirm_key] = False

        st.session_state[confirm_key] = st.checkbox(
            f"Yes, I understand this will delete College Master permanently for {year} - {program}.",
            value=st.session_state[confirm_key],
            key=f"flush_college_confirm_{year}_{program}"
        )

        if st.session_state[confirm_key]:
            if st.button("🚨 Flush College Master Data", key=f"flush_college_btn_{year}_{program}"):
                save_table("College Master", pd.DataFrame(), replace_where={"AdmissionYear": year, "Program": program})
                st.success(f"✅ College Master data cleared for {year} - {program}!")
                st.session_state[confirm_key] = False
                st.rerun()
