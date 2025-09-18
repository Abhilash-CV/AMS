import pandas as pd
import streamlit as st
from common_functions import load_table, save_table, clean_columns, download_button_for_df, filter_and_sort_dataframe

def college_master_ui(year: str, program: str):
    """UI for College Master management (append uploads; view/edit all rows including duplicates)."""
    st.subheader("🏫 College Master")

    key_base = f"{year}_{program}"
    ss_key = f"college_master_df_{key_base}"

    # --- Load stored table for this year/program ---
    df_stored = load_table("College Master", year, program)
    if df_stored is None:
        df_stored = pd.DataFrame()

    # Initialize session_state with stored data (only once)
    if ss_key not in st.session_state:
        st.session_state[ss_key] = df_stored.copy()

    # --- Upload Section (append uploads) ---
    uploaded = st.file_uploader(
        "Upload College Master (Excel/CSV) — new rows will be APPENDED",
        type=["xlsx", "xls", "csv"],
        key=f"upl_CollegeMaster_{key_base}"
    )

    if uploaded:
        try:
            # Read incoming file
            if uploaded.name.lower().endswith('.csv'):
                df_new = pd.read_csv(uploaded)
            else:
                df_new = pd.read_excel(uploaded)

            # Normalize columns and add metadata
            df_new = clean_columns(df_new)
            df_new["AdmissionYear"] = year
            df_new["Program"] = program

            # Append to session-state table (preserves duplicates)
            df_combined = pd.concat([st.session_state[ss_key], df_new], ignore_index=True)

            # Update session state so UI shows appended rows immediately
            st.session_state[ss_key] = df_combined

            # Persist to storage by REPLACING all rows for this year/program with the combined table
            # (This makes the persisted table match what the UI shows.)
            save_table(
                "College Master",
                st.session_state[ss_key],
                replace_where={"AdmissionYear": year, "Program": program}
            )

            st.success(f"✅ Appended {len(df_new)} rows — total now {len(st.session_state[ss_key])} rows for {year} / {program}.")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    # --- Download + Filter + Edit Section ---
    # Always work with the session-state current view so user sees all appended rows
    df_current = st.session_state.get(ss_key, pd.DataFrame())

    # Download button for current view
    download_button_for_df(df_current, f"College_Master_{year}_{program}")

    st.caption(f"Showing rows for **AdmissionYear={year} & Program={program}** (including all appended uploads)")

    # Allow user to filter/sort using your helper (if it expects the full df)
    df_col_filtered = filter_and_sort_dataframe(df_current, "College Master")

    # Editable grid: user can edit existing rows or add new rows (num_rows="dynamic")
    edited_col = st.data_editor(
        df_col_filtered,
        num_rows="dynamic",
        use_container_width=True,
        key=f"data_editor_CollegeMaster_{key_base}"
    )

    # --- Save Button (replaces persisted table for that year/program with the edited table) ---
    if st.button("💾 Save College Master", key=f"save_CollegeMaster_{key_base}"):
        try:
            edited = edited_col.copy()

            # Ensure metadata columns exist
            if "AdmissionYear" not in edited.columns:
                edited["AdmissionYear"] = year
            if "Program" not in edited.columns:
                edited["Program"] = program

            # Persist exactly what user edited (this removes any duplicates only if user removed them)
            save_table(
                "College Master",
                edited,
                replace_where={"AdmissionYear": year, "Program": program}
            )

            # Update session-state so UI reflects saved data
            st.session_state[ss_key] = edited

            st.success("✅ College Master saved (storage updated).")
        except Exception as e:
            st.error(f"Save failed: {e}")

    # --- Danger Zone ---
    with st.expander("🗑️ Danger Zone: College Master"):
        st.error("⚠️ This will permanently delete ALL College Master data for this year/program!")

        confirm_key = f"flush_confirm_college_{key_base}"
        if confirm_key not in st.session_state:
            st.session_state[confirm_key] = False

        st.session_state[confirm_key] = st.checkbox(
            f"Yes, I understand this will delete College Master permanently for {year} - {program}.",
            value=st.session_state[confirm_key],
            key=f"flush_college_confirm_{key_base}"
        )

        if st.session_state[confirm_key]:
            if st.button("🚨 Flush College Master Data", key=f"flush_college_btn_{key_base}"):
                # Clear persisted data and session-state
                save_table("College Master", pd.DataFrame(), replace_where={"AdmissionYear": year, "Program": program})
                st.session_state[ss_key] = pd.DataFrame()
                st.success(f"✅ College Master data cleared for {year} - {program}!")
                st.session_state[confirm_key] = False
                st.rerun()
