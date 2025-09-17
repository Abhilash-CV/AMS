# candidate_details_ui.py
import pandas as pd
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

    # Tabs
    tab_all, tab_college, tab_program, tab_category = st.tabs(
        ["All Candidates", "By College", "By Program", "By Category"]
    )

    # ---------------- All Candidates ----------------
    with tab_all:
        st.subheader("All Candidates")
        edited_stu = st.data_editor(
            df_stu,
            num_rows="dynamic",
            use_container_width=True,
            key=f"data_editor_all_{year}_{program}"
        )

    # ---------------- By College ----------------
    with tab_college:
        st.subheader("Filter by College")
        if "College" in df_stu.columns:
            colleges = sorted(df_stu["College"].dropna().unique())
            selected_college = st.selectbox("Select College", ["All"] + list(colleges))
            df_filtered = df_stu if selected_college == "All" else df_stu[df_stu["College"] == selected_college]
            edited_stu = st.data_editor(
                df_filtered,
                num_rows="dynamic",
                use_container_width=True,
                key=f"data_editor_college_{year}_{program}"
            )
        else:
            st.warning("⚠️ 'College' column not found!")

    # ---------------- By Program ----------------
    with tab_program:
        st.subheader("Filter by Program")
        if "Program" in df_stu.columns:
            programs = sorted(df_stu["Program"].dropna().unique())
            selected_program = st.selectbox("Select Program", ["All"] + list(programs))
            df_filtered = df_stu if selected_program == "All" else df_stu[df_stu["Program"] == selected_program]
            edited_stu = st.data_editor(
                df_filtered,
                num_rows="dynamic",
                use_container_width=True,
                key=f"data_editor_program_{year}_{program}"
            )
        else:
            st.warning("⚠️ 'Program' column not found!")

    # ---------------- By Category ----------------
    with tab_category:
        st.subheader("Filter by Category")
        if "Category" in df_stu.columns:
            categories = sorted(df_stu["Category"].dropna().unique())
            selected_category = st.selectbox("Select Category", ["All"] + list(categories))
            df_filtered = df_stu if selected_category == "All" else df_stu[df_stu["Category"] == selected_category]
            edited_stu = st.data_editor(
                df_filtered,
                num_rows="dynamic",
                use_container_width=True,
                key=f"data_editor_category_{year}_{program}"
            )
        else:
            st.warning("⚠️ 'Category' column not found!")

    # ---------------- Save Button ----------------
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

    # ---------------- Danger Zone ----------------
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
