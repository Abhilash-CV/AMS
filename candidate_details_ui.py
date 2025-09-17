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

    # Tabs for sub-views
    tab1, tab2, tab3, tab4 = st.tabs(["All Candidates", "By Quota", "By College", "By Program"])

    with tab1:
        st.subheader("All Candidates")
        st.data_editor(df_stu, num_rows="dynamic", use_container_width=True)

    with tab2:
        st.subheader("By Quota")
        if "Quota" in df_stu.columns:
            quota_count = df_stu["Quota"].value_counts().reset_index()
            quota_count.columns = ["Quota", "Count"]
            st.table(quota_count)
            fig = px.pie(
                quota_count,
                names="Quota",
                values="Count",
                title="Candidate Distribution by Quota",
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Quota column not found!")

    with tab3:
        st.subheader("By College")
        if "College" in df_stu.columns:
            college_count = df_stu["College"].value_counts().reset_index()
            college_count.columns = ["College", "Count"]
            st.table(college_count)
            fig = px.bar(
                college_count,
                x="College",
                y="Count",
                color="Count",
                title="Candidates per College"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("College column not found!")

    with tab4:
        st.subheader("By Program")
        if "Program" in df_stu.columns:
            program_count = df_stu["Program"].value_counts().reset_index()
            program_count.columns = ["Program", "Count"]
            st.table(program_count)
            fig = px.bar(
                program_count,
                x="Program",
                y="Count",
                color="Count",
                title="Candidates per Program"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Program column not found!")
