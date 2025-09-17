import streamlit as st
import pandas as pd

def payment_refund_ui():
    st.title("💰 Payment Refund Status Tracker")

    # Upload section
    uploaded_file = st.file_uploader("Upload Payment Excel/CSV", type=["xlsx", "xls", "csv"], key="payment_upload")

    if uploaded_file:
        # Read file
        if uploaded_file.name.endswith(('xlsx', 'xls')):
            df = pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file)

        # Append 'Refunded' column if not present
        if 'Refunded' not in df.columns:
            df['Refunded'] = False

        # Optional: select date column for month filter
        date_cols = [c for c in df.columns if 'date' in c.lower()]
        selected_date_col = st.selectbox("Select date column (optional, for month filtering)", [""] + date_cols)

        # Month filter
        if selected_date_col:
            df[selected_date_col] = pd.to_datetime(df[selected_date_col], errors='coerce')
            months = df[selected_date_col].dropna().dt.to_period('M').unique()
            month_options = [str(m) for m in months]
            selected_month = st.selectbox("Select Month", month_options)
            if selected_month:
                df_display = df[df[selected_date_col].dt.to_period('M') == pd.Period(selected_month)]
            else:
                df_display = df.copy()
        else:
            df_display = df.copy()

        st.subheader("Mark Payments as Refunded")

        # Bulk mark/unmark buttons
        if st.button("Mark All Visible as Refunded"):
            df.loc[df_display.index, 'Refunded'] = True
        if st.button("Unmark All Visible as Refunded"):
            df.loc[df_display.index, 'Refunded'] = False

        # Display header row with custom color
        header_color = "#007bff"  # blue
        st.markdown(
            "<div style='display:flex; background-color:{}; padding:5px; color:white;'>".format(header_color) +
            "".join([f"<div style='flex:1; font-weight:bold'>{col}</div>" for col in df_display.columns]) +
            "<div style='flex:1; font-weight:bold'>Refunded</div></div>",
            unsafe_allow_html=True
        )

        # Display table rows with checkboxes and color coding
        for i, row in df_display.iterrows():
            cols = st.columns(len(df_display.columns) + 1)
            bg_color = "#d4edda" if row['Refunded'] else "#f8d7da"  # green/red

            for j, col_name in enumerate(df_display.columns):
                cols[j].markdown(
                    f"<div style='background-color:{bg_color}; padding:5px'>{row[col_name]}</div>", 
                    unsafe_allow_html=True
                )
            # Checkbox for refund
            refunded = cols[-1].checkbox("Refunded", value=row['Refunded'], key=f"refund_{i}")
            df.loc[row.name, 'Refunded'] = refunded

        # Download updated file
        st.subheader("Download Updated Payment Status")
        output_file = "updated_payment_status.xlsx"
        df.to_excel(output_file, index=False)
        st.download_button("📥 Download Excel", data=open(output_file, "rb"), file_name=output_file)


# --- Run standalone app ---
if __name__ == "__main__":
    payment_refund_ui()
