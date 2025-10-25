# refund_forfeit_panel.py
import streamlit as st
import pandas as pd
import io

def refund_forfeit_panel():
    st.header("Refund & Forfeit Panel")

    # ---------------------------
    # Upload Excel
    # ---------------------------
    uploaded_file = st.file_uploader("Upload Candidate Excel File", type=["xlsx"], key="refund_upload")
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.session_state['df_refund'] = df
        st.session_state['calculated_refund'] = False
        st.success("Excel uploaded successfully!")
        st.dataframe(df.head())

    df = st.session_state.get('df_refund')
    if df is not None:
        st.subheader("Select Fee Columns per Round")
        fee_cols_options = list(df.columns) + ["Nil"]

        fee_round1 = st.selectbox("Fee Column - Round 1", fee_cols_options, index=0)
        fee_round2 = st.selectbox("Fee Column - Round 2", fee_cols_options, index=1)
        fee_round3 = st.selectbox("Fee Column - Round 3", fee_cols_options, index=2)
        reg_fee_col = st.selectbox("Registration Fee Column", fee_cols_options, index=3)

        # ---------------------------
        # Forfeit start round selection
        # ---------------------------
        st.subheader("Forfeit Configuration")
        forfeit_start_round = st.selectbox(
            "Forfeit applies from which round?", 
            options=[1, 2, 3], 
            index=1,
            help="Forfeit is calculated for non-joining (N) or TC candidates from this round onwards"
        )

        if st.button("Calculate Refund & Forfeit", key="calc_refund"):
            refund_list = []
            forfeit_list = []
            remarks_list = []

            # Create Counted columns to avoid duplication
            for round_no in [1,2,3]:
                counted_col = f"Counted_{round_no}"
                if counted_col not in df.columns:
                    df[counted_col] = False

            for idx, row in df.iterrows():
                total_refund = 0
                total_forfeit = 0
                remarks = []

                # ---------------------------
                # Registration fee logic
                # ---------------------------
                join1 = row.get("JoinStatus_1", "N")
                allot2 = row.get("Allot_2", None)

                if reg_fee_col != "Nil" and reg_fee_col in df.columns:
                    if join1 == 'Y' and (pd.isna(allot2) or allot2 in ["", "NA"]):
                        total_refund += row.get(reg_fee_col, 0)
                        remarks.append("Registration fee refunded")
                    else:
                        total_forfeit += row.get(reg_fee_col, 0)
                        remarks.append("Registration fee forfeited")

                # ---------------------------
                # Round-wise calculation
                # ---------------------------
                for round_no, fee_col in enumerate([fee_round1, fee_round2, fee_round3], start=1):
                    join_status = row.get(f"JoinStatus_{round_no}", "N")
                    counted_col = f"Counted_{round_no}"

                    # Skip if Nil column or fee not present
                    if fee_col == "Nil" or fee_col not in df.columns:
                        continue

                    if row[counted_col]:
                        continue  # Already counted

                    fee_paid = row.get(fee_col, 0)
                    next_round = round_no + 1
                    next_allot = row.get(f"Allot_{next_round}", None) if next_round <=3 else None

                    # Refund logic for joined candidates
                    if join_status == 'Y':
                        # Refund if fee=0 or no next round allotment
                        if fee_paid == 0 or pd.isna(next_allot) or next_allot in ["", "NA"]:
                            total_refund += fee_paid
                            remarks.append(f"Round {round_no} refunded")
                        else:
                            # If moved to next round but fee present, still refund
                            total_refund += fee_paid
                            remarks.append(f"Round {round_no} refunded (moved to next round)")

                    # Forfeit logic: only from selected forfeit_start_round and fee>0
                    elif round_no >= forfeit_start_round and join_status in ['N','TC'] and fee_paid > 0:
                        total_forfeit += fee_paid
                        remarks.append(f"Round {round_no} forfeited")

                    df.at[idx, counted_col] = True

                refund_list.append(total_refund)
                forfeit_list.append(total_forfeit)
                remarks_list.append(", ".join(remarks))

            # Save results
            df['Total_Refund'] = refund_list
            df['Total_Forfeit'] = forfeit_list
            df['Remarks'] = remarks_list
            st.session_state['df_refund'] = df
            st.session_state['calculated_refund'] = True

            st.success("Refund & Forfeit calculation completed!")
            st.dataframe(df.head())

        # ---------------------------
        # Download Excel
        # ---------------------------
        if st.session_state.get('calculated_refund', False):
            @st.cache_data
            def convert_df_to_excel(df):
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                return output.getvalue()

            excel_data = convert_df_to_excel(df)
            st.download_button(
                label="Download Report as Excel",
                data=excel_data,
                file_name="refund_forfeit_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
