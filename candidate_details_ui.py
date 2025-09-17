# candidate_details_ui.py
import pandas as pd
import plotly.express as px
import streamlit as st
from common_functions import load_table, save_table, clean_columns, download_button_for_df


def candidate_details_ui(year, program):
    st.header("👨‍🎓 Candidate Details")
    
    # Load data
    df_stu = load_table("Candidate Details", year, program)

    # File uploader
    uploaded = st.file_uploader(
        "Upload Candidate Details",
        type=["xlsx", "xls", "csv"],
        key=f"upl_candidate_details_{year}_{program}"
    )
    if uploaded:
        try:
            df_new = pd.read_excel(uploaded) if uploaded.name.endswith(".xlsx") else pd.read_csv(uploaded)
            df_new = clean_columns(df_new)
            df_new["AdmissionYear"] = year
            df_new["Program"] = program

            save_table(
                "Candidate Details",
                df_new,
                replace_where={"AdmissionYear": year, "Program": program}
            )

            df_stu = load_table("Candidate Details", year, program)
            st.success("✅ Candidate Details uploaded successfully!")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    # Download button
    download_button_for_df(df_stu, f"CandidateDetails_{year}_{program}")

    # Editable Table (single view)
    st.subheader("Candidate Table (Editable)")
    edited_stu = st.data_editor(
        df_stu,
        num_rows="dynamic",
        use_container_width=True,
        key=f"data_editor_candidate_{year}_{program}"
    )

    # Save edited table
    if st.button("💾 Save Candidate Details", key=f"save_candidate_{year}_{program}"):
        if "AdmissionYear" not in edited_stu.columns:
            edited_stu["AdmissionYear"] = year
        if "Program" not in edited_stu.columns:
            edited_stu["Program"] = program

        save_table(
            "Candidate Details",
            edited_stu,
            replace_where={"AdmissionYear": year, "Program": program}
        )
        st.success("✅ Candidate Details saved!")
        df_stu = load_table("Candidate Details", year, program)

    # Danger Zone: Flush Candidate Details
    with st.expander("🗑️ Danger Zone: Candidate Details"):
        st.error(f"⚠️ This will permanently delete all Candidate Details for {year} - {program}!")
        confirm_key = f"flush_confirm_candidate_{year}_{program}"
        if confirm_key not in st.session_state:
            st.session_state[confirm_key] = False

        st.session_state[confirm_key] = st.checkbox(
            f"Yes, I understand this will delete Candidate Details permanently for {year} - {program}.",
            value=st.session_state[confirm_key],
            key=f"flush_candidate_confirm_{year}_{program}"
        )

        if st.session_state[confirm_key]:
            if st.button(f"🚨 Flush Candidate Details", key=f"flush_candidate_btn_{year}_{program}"):
                save_table("Candidate Details", pd.DataFrame(), replace_where={"AdmissionYear": year, "Program": program})
                st.success(f"✅ Candidate Details cleared for {year} - {program}!")
                st.session_state[confirm_key] = False
                st.rerun()
