import streamlit as st
import pandas as pd

def payment_refund_ui():
    st.subheader("💰 Payment Refund Status Tracker")

    # Upload Excel/CSV
    uploaded_file = st.file_uploader("Upload Payment Excel/CSV", type=["xlsx", "xls", "csv"], key="payment_upload")
    
    if uploaded_file:
        # Load file dynamically
        if uploaded_file.name.endswith(('xlsx', 'xls')):
            df = pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file)

        # Add Status column if not present
        if 'Status' not in df.columns:
            df['Status'] = 'Not Refunded'  # Default status

        # Optional: select date column for month filtering
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

        st.subheader("Update Payment Status")

        # Bulk update buttons
        col1, col2, col3, col4 = st.columns(4)
        if col1.button("Mark All as Refunded"):
            df.loc[df_display.index, 'Status'] = 'Refunded'
        if col2.button("Mark All as Not Refunded"):
            df.loc[df_display.index, 'Status'] = 'Not Refunded'
        if col3.button("Mark All as Processing"):
            df.loc[df_display.index, 'Status'] = 'Processing'
        if col4.button("Mark All as Pending"):
            df.loc[df_display.index, 'Status'] = 'Pending'

        # Sticky table header and scrollable table
        st.markdown("""
        <style>
        .table-container {
            max-height: 400px;
            overflow-y: auto;
            display: block;
        }
        .table-container table {
            border-collapse: collapse;
            width: 100%;
        }
        .table-container th {
            position: sticky;
            top: 0;
            background-color: #add8e6;  /* light blue header */
            color: black;
            padding: 5px;
        }
        .table-container td {
            padding: 5px;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("<div class='table-container'>", unsafe_allow_html=True)

        # Table header
        st.markdown("<table>", unsafe_allow_html=True)
        st.markdown("<tr>" + "".join([f"<th>{col}</th>" for col in df_display.columns]) + "<th>Status</th></tr>", unsafe_allow_html=True)

        # Table rows with color-coded background based on status
        status_colors = {
            "Refunded": "#d4edda",       # green
            "Not Refunded": "#f8d7da",   # red
            "Processing": "#fff3cd",     # yellow
            "Pending": "#ffeeba"         # light yellow
        }

        for i, row in df_display.iterrows():
            bg_color = status_colors.get(row['Status'], "#ffffff")
            st.markdown("<tr>", unsafe_allow_html=True)
            for col_name in df_display.columns:
                st.markdown(f"<td style='background-color:{bg_color}'>{row[col_name]}</td>", unsafe_allow_html=True)
            # Dropdown to update status
            status_options = ["Refunded", "Not Refunded", "Processing", "Pending"]
            selected_status = st.selectbox("", status_options, index=status_options.index(row['Status']), key=f"status_{i}")
            df.loc[row.name, 'Status'] = selected_status
            st.markdown(f"<td style='background-color:{bg_color}'>{selected_status}</td>", unsafe_allow_html=True)
            st.markdown("</tr>", unsafe_allow_html=True)

        st.markdown("</table>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Download updated file
        st.subheader("Download Updated Payment Status")
        output_file = "updated_payment_status.xlsx"
        df.to_excel(output_file, index=False)
        st.download_button("📥 Download Excel", data=open(output_file, "rb"), file_name=output_file)

# Run standalone app
if __name__ == "__main__":
    payment_refund_ui()
