# ---------- StudentDetails ----------
with tabs[4]:
    # Load all student details
    df_all = load_table("StudentDetails")

    # Upload new data scoped to current year+program
    uploaded = st.file_uploader(
        "Upload StudentDetails (Excel/CSV)",
        type=["xlsx", "csv"],
        key="upload_StudentDetails"
    )
    if uploaded:
        try:
            # Read uploaded file (CSV or Excel)
            if uploaded.name.lower().endswith(".csv"):
                df_new = pd.read_csv(uploaded)
            else:
                df_new = pd.read_excel(uploaded)
            # Assign year and program to all new rows
            df_new["AdmissionYear"] = st.session_state.year
            df_new["Program"] = st.session_state.program
            df_new = clean_columns(df_new)
            # Save ONLY for current year+program (others remain)
            save_table("StudentDetails", df_new, replace_where={
                "AdmissionYear": st.session_state.year,
                "Program": st.session_state.program
            })
            st.success(f"📥 Uploaded and saved {len(df_new)} rows for AdmissionYear={st.session_state.year}, Program={st.session_state.program}")
            df_all = load_table("StudentDetails")  # Reload after save
        except Exception as e:
            st.error(f"Error reading file: {e}")

    # Show only filtered rows for current year+program
    df_filtered = df_all[
        (df_all["AdmissionYear"] == st.session_state.year) &
        (df_all["Program"] == st.session_state.program)
    ] if not df_all.empty else pd.DataFrame()

    df_filtered = filter_and_sort_dataframe(df_filtered, "StudentDetails")
    edited = st.data_editor(df_filtered, num_rows="dynamic", use_container_width=True, key="edit_students")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save StudentDetails", key="save_students"):
            save_table("StudentDetails", edited, replace_where={
                "AdmissionYear": st.session_state.year,
                "Program": st.session_state.program
            })
            st.success(f"✅ Saved edits for AdmissionYear={st.session_state.year}, Program={st.session_state.program}")

    with col2:
        if st.button("🗑️ Flush StudentDetails (Year+Program)", key="flush_students"):
            save_table("StudentDetails", pd.DataFrame(columns=df_filtered.columns), replace_where={
                "AdmissionYear": st.session_state.year,
                "Program": st.session_state.program
            })
            st.success(f"✅ Flushed data for AdmissionYear={st.session_state.year}, Program={st.session_state.program}")
