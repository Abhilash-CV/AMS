def refund_forfeit_panel():
    st.header("Refund & Forfeit Calculation")

    df = st.session_state.get('df_refund', None)  # separate df for this panel
    
    # Upload section (if you want separate upload)
    uploaded_file = st.file_uploader("Upload Candidate Excel", type=["xlsx"], key="refund_upload")
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.session_state['df_refund'] = df
        st.session_state['calculated_refund'] = False
        st.success("Excel uploaded successfully!")
    
    if df is not None:
        st.write("Select Fee Columns for Each Round and Registration Fee")
        fee_round1 = st.selectbox("Fee Column - Round 1", df.columns, index=0)
        fee_round2 = st.selectbox("Fee Column - Round 2", df.columns, index=1)
        fee_round3 = st.selectbox("Fee Column - Round 3", df.columns, index=2)
        reg_fee_col = st.selectbox("Registration Fee Column", df.columns, index=3)

        if st.button("Calculate Refund & Forfeit", key="calc_refund"):
            # calculation logic same as before
            refund_list, forfeit_list, remarks_list = [], [], []

            for round_no in [1, 2, 3]:
                counted_col = f"Counted_{round_no}"
                if counted_col not in df.columns:
                    df[counted_col] = False

            for idx, row in df.iterrows():
                total_refund, total_forfeit = 0, 0
                remarks = []

                # Registration fee logic
                join1 = row.get("JoinStatus_1", "N")
                allot2 = row.get("Allot_2", None)
                if join1 == 'Y' and (pd.isna(allot2) or allot2 in ["", "NA"]):
                    total_refund += row.get(reg_fee_col, 0)
                    remarks.append("Registration fee refunded")
                else:
                    total_forfeit += row.get(reg_fee_col, 0)
                    remarks.append("Registration fee forfeited")

                # Round-wise processing
                for round_no, fee_col in enumerate([fee_round1, fee_round2, fee_round3], start=1):
                    join_status = row.get(f"JoinStatus_{round_no}", "N")
                    fee_paid = row.get(fee_col, 0)
                    counted_col = f"Counted_{round_no}"
                    if row[counted_col]:
                        continue
                    next_round = round_no + 1
                    next_allot = row.get(f"Allot_{next_round}", None) if next_round <=3 else None

                    if join_status in ['N', 'TC']:
                        total_forfeit += fee_paid
                        remarks.append(f"Round {round_no} forfeited")
                    elif join_status == 'Y':
                        if next_round >3 or pd.isna(next_allot) or next_allot in ["", "NA"]:
                            total_refund += fee_paid
                            remarks.append(f"Round {round_no} refunded")
                        else:
                            total_forfeit += fee_paid
                            remarks.append(f"Round {round_no} forfeited (moved to next round)")
                    df.at[idx, counted_col] = True

                refund_list.append(total_refund)
                forfeit_list.append(total_forfeit)
                remarks_list.append(", ".join(remarks))

            df['Total_Refund'] = refund_list
            df['Total_Forfeit'] = forfeit_list
            df['Remarks'] = remarks_list
            st.session_state['df_refund'] = df
            st.session_state['calculated_refund'] = True
            st.success("Calculation completed!")
            st.dataframe(df.head())

        # Download option
        if st.session_state.get('calculated_refund', False):
            @st.cache_data
            def convert_df_to_excel(df):
                import io
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
