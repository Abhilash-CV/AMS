import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

st.set_page_config(page_title="Payment Refund Tracker", layout="wide")

def payment_refund_ui():
    st.title("💰 Payment Refund Status Tracker (Interactive Table)")

    uploaded_file = st.file_uploader("Upload Payment Excel/CSV", type=["xlsx", "xls", "csv"])
    if uploaded_file:
        if uploaded_file.name.endswith(('xlsx', 'xls')):
            df = pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file)

        if 'Status' not in df.columns:
            df['Status'] = 'Not Refunded'

        # Optional month filter
        date_cols = [c for c in df.columns if 'date' in c.lower()]
        selected_date_col = st.selectbox("Select date column (optional, for month filtering)", [""] + date_cols)

        if selected_date_col:
            df[selected_date_col] = pd.to_datetime(df[selected_date_col], errors='coerce')
            months = df[selected_date_col].dropna().dt.to_period('M').unique()
            selected_month = st.selectbox("Select Month", [str(m) for m in months])
            if selected_month:
                df = df[df[selected_date_col].dt.to_period('M') == pd.Period(selected_month)]

        st.subheader("Update Payment Status (click cell to change)")

        # AG-Grid configuration
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_default_column(editable=True)
        # Dropdown editor for Status column
        gb.configure_column("Status", editable=True, cellEditor='agSelectCellEditor',
                            cellEditorParams={'values': ["Refunded", "Not Refunded", "Processing", "Pending"]})
        # Row color based on Status
        cellsytle_jscode = JsCode("""
        function(params) {
            if (params.colDef.field == 'Status') {
                if (params.value == 'Refunded') {return {'color': 'black', 'backgroundColor':'#d4edda'};}
                if (params.value == 'Not Refunded') {return {'color': 'black', 'backgroundColor':'#f8d7da'};}
                if (params.value == 'Processing') {return {'color': 'black', 'backgroundColor':'#fff3cd'};}
                if (params.value == 'Pending') {return {'color': 'black', 'backgroundColor':'#ffeeba'};}
            }
        };
        """)
        gb.configure_column("Status", cellStyle=cellsytle_jscode)
        gb.configure_grid_options(domLayout='normal')
        gridOptions = gb.build()

        grid_response = AgGrid(df, gridOptions=gridOptions, update_mode=GridUpdateMode.VALUE_CHANGED, height=400, fit_columns_on_grid_load=True)

        updated_df = grid_response['data']

        st.subheader("Download Updated Payment Status")
        updated_df.to_excel("updated_payment_status.xlsx", index=False)
        st.download_button("📥 Download Excel", data=open("updated_payment_status.xlsx", "rb"), file_name="updated_payment_status.xlsx")


if __name__ == "__main__":
    payment_refund_ui()
