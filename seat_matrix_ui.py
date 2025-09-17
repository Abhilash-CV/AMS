# seat_matrix_ui.py
import pandas as pd
import streamlit as st
from common_functions import load_table, save_table, clean_columns, download_button_for_df, filter_and_sort_dataframe


def seat_matrix_ui(year, program):
    st.header("📊 Seat Matrix")

    # Create sub-tabs for Government, Private, Minority, and All
    seat_tabs = st.tabs(["🏛️ Government", "🏢 Private", "🕌 Minority", "📑 All Seat Types"])

    for seat_type, tab in zip(["Government", "Private", "Minority"], seat_tabs[:3]):
        with tab:
            st.subheader(f"{seat_type} Seat Matrix")

            # Load only selected seat type
            df_seat = load_table("Seat Matrix", year, program)
            if "SeatType" in df_seat.columns:
                df_seat = df_seat[df_seat["SeatType"] == seat_type]

            # Upload
            uploaded = st.file_uploader(
                f"Upload {seat_type} Seat Matrix",
                type=["xlsx", "xls", "csv"],
                key=f"upl_seat_{seat_type}_{year}_{program}"
            )
            if uploaded:
                try:
                    df_new = pd.read_excel(uploaded) if uploaded.name.endswith(".xlsx") else pd.read_csv(uploaded)
                    df_new = clean_columns(df_new)
                    df_new["AdmissionYear"] = year
                    df_new["Program"] = program
                    df_new["SeatType"] = seat_type
                    save_table("Seat Matrix", df_new, replace_where={"AdmissionYear": year, "Program": program, "SeatType": seat_type})
                    df_seat = load_table("Seat Matrix", year, program)
                    df_seat = df_seat[df_seat["SeatType"] == seat_type]
                    st.success(f"✅ {seat_type} Seat Matrix uploaded successfully!")
                except Exception as e:
                    st.error(f"Error reading file: {e}")

            # Download + Edit
            download_button_for_df(df_seat, f"SeatMatrix_{seat_type}_{year}_{program}")
            df_seat_filtered = filter_and_sort_dataframe(df_seat, "Seat Matrix")
            edited_seat = st.data_editor(
                df_seat_filtered,
                num_rows="dynamic",
                use_container_width=True,
                key=f"data_editor_seat_{seat_type}_{year}_{program}"
            )

            # Save
            if st.button(f"💾 Save {seat_type} Seat Matrix", key=f"save_seat_matrix_{seat_type}_{year}_{program}"):
                if "AdmissionYear" not in edited_seat.columns:
                    edited_seat["AdmissionYear"] = year
                if "Program" not in edited_seat.columns:
                    edited_seat["Program"] = program
                if "SeatType" not in edited_seat.columns:
                    edited_seat["SeatType"] = seat_type
                save_table("Seat Matrix", edited_seat, replace_where={"AdmissionYear": year, "Program": program, "SeatType": seat_type})
                st.success(f"✅ {seat_type} Seat Matrix saved!")
                st.rerun()

            # Flush Danger Zone
            with st.expander(f"🗑️ Danger Zone: {seat_type} Seat Matrix"):
                st.error(f"⚠️ This will delete {seat_type} Seat Matrix data for AdmissionYear={year} & Program={program}!")
                confirm_key = f"flush_confirm_seat_{seat_type}_{year}_{program}"
                if confirm_key not in st.session_state:
                    st.session_state[confirm_key] = False

                st.session_state[confirm_key] = st.checkbox(
                    f"Yes, delete {seat_type} Seat Matrix permanently.",
                    value=st.session_state[confirm_key],
                    key=f"flush_seat_confirm_{seat_type}_{year}_{program}"
                )

                if st.session_state[confirm_key]:
                    if st.button(f"🚨 Flush {seat_type} Seat Matrix", key=f"flush_seat_btn_{seat_type}_{year}_{program}"):
                        save_table("Seat Matrix", pd.DataFrame(), replace_where={"AdmissionYear": year, "Program": program, "SeatType": seat_type})
                        st.success(f"✅ {seat_type} Seat Matrix cleared!")
                        st.session_state[confirm_key] = False
                        st.rerun()

    # ---------- ALL SEAT TYPES TAB ----------
    with seat_tabs[3]:
        st.subheader("📑 All Seat Types (Combined View)")
        df_all = load_table("Seat Matrix", year, program)

        # Show all data without filtering SeatType
        download_button_for_df(df_all, f"SeatMatrix_ALL_{year}_{program}")
        df_all_filtered = filter_and_sort_dataframe(df_all, "Seat Matrix")
        edited_all = st.data_editor(
            df_all_filtered,
            num_rows="dynamic",
            use_container_width=True,
            key=f"data_editor_seat_all_{year}_{program}"
        )

        if st.button("💾 Save All Seat Types", key=f"save_seat_matrix_all_{year}_{program}"):
            if "AdmissionYear" not in edited_all.columns:
                edited_all["AdmissionYear"] = year
            if "Program" not in edited_all.columns:
                edited_all["Program"] = program
            if "SeatType" not in edited_all.columns:
                st.warning("⚠️ 'SeatType' column missing! Please add it manually before saving.")
            else:
                save_table("Seat Matrix", edited_all, replace_where={"AdmissionYear": year, "Program": program})
                st.success("✅ All Seat Types saved successfully!")
                st.rerun()

        with st.expander("🗑️ Danger Zone: ALL Seat Types"):
            st.error(f"⚠️ This will delete ALL Seat Matrix data for AdmissionYear={year} & Program={program}!")
            confirm_key = f"flush_confirm_seat_all_{year}_{program}"
            if confirm_key not in st.session_state:
                st.session_state[confirm_key] = False

            st.session_state[confirm_key] = st.checkbox(
                f"Yes, delete ALL Seat Types permanently.",
                value=st.session_state[confirm_key],
                key=f"flush_seat_confirm_all_{year}_{program}"
            )

            if st.session_state[confirm_key]:
                if st.button("🚨 Flush ALL Seat Matrix", key=f"flush_seat_btn_all_{year}_{program}"):
                    save_table("Seat Matrix", pd.DataFrame(), replace_where={"AdmissionYear": year, "Program": program})
                    st.success(f"✅ ALL Seat Types cleared for AdmissionYear={year} & Program={program}!")
                    st.session_state[confirm_key] = False
                    st.rerun()
