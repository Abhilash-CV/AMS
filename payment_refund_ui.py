import streamlit as st
import pandas as pd
import io

def payment_refund_ui():
    # Title
    st.markdown("### 💰 Payment Refund Status Tracker")

    # File upload
    uploaded_file = st.file_uploader(
        "📂 Upload Payment Data (Excel/CSV)", 
        type=["xlsx", "xls", "csv"], 
        key="payment_upload"
    )
    
    if uploaded_file:
        # Load file dynamically
        if uploaded_file.name.endswith(('xlsx', 'xls')):
            df = pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file)

        # Ensure Status column exists
        if 'Status' not in df.columns:
            df['Status'] = 'Not Refunded'

        st.divider()
        st.markdown("#### 🔎 Filter Data")

        # Optional: select date column for filtering
        date_cols = [c for c in df.columns if 'date' in c.lower()]
        selected_date_col = st.selectbox("Select date column", [""] + date_cols)

        df_display = df.copy()
        if selected_date_col:
            df[selected_date_col] = pd.to_datetime(df[selected_date_col], errors='coerce')
            months = df[selected_date_col].dropna().dt.to_period('M').unique()
            month_options = [str(m) for m in months]
            selected_month = st.selectbox("Select Month", [""] + month_options)
            if selected_month:
                df_display = df[df[selected_date_col].dt.to_period('M') == pd.Period(selected_month)]

        # =============================
        # 📊 Summary Dashboard
        # =============================
        st.divider()
        st.markdown("#### 📊 Summary Overview")

        total = len(df_display)
        refunded = (df_display['Status'] == 'Refunded').sum()
        not_refunded = (df_display['Status'] == 'Not Refunded').sum()
        processing = (df_display['Status'] == 'Processing').sum()
        pending = (df_display['Status'] == 'Pending').sum()

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Records", total)
        col2.metric("✅ Refunded", refunded)
        col3.metric("❌ Not Refunded", not_refunded)
        col4.metric("⏳ Processing", processing)
        col5.metric("🕒 Pending", pending)

        # =============================
        # 📝 Update Payment Status
        # =============================
        st.divider()
        st.markdown("#### 📝 Update Payment Status")

        # Bulk update buttons
        st.markdown("Apply bulk updates to the filtered data:")
        col1, col2, col3, col4 = st.columns(4)
        with col1: 
            if st.button("✅ Refunded"):
                df.loc[df_display.index, 'Status'] = 'Refunded'
        with col2: 
            if st.button("❌ Not Refunded"):
                df.loc[df_display.index, 'Status'] = 'Not Refunded'
        with col3: 
            if st.button("⏳ Processing"):
                df.loc[df_display.index, 'Status'] = 'Processing'
        with col4: 
            if st.button("🕒 Pending"):
                df.loc[df_display.index, 'Status'] = 'Pending'

        # Color mapping for status
        status_colors = {
            "Refunded": "#d4edda",       # light green
            "Not Refunded": "#f8d7da",   # light red
            "Processing": "#fff3cd",     # light yellow
            "Pending": "#ffeeba"         # pale yellow
        }

        # Editable data grid with colored Status column
        status_options = list(status_colors.keys())
        edited_df = st.data_editor(
            df_display,
            num_rows="dynamic",
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=status_options,
                    required=True,
                    # Apply colors
                    cell_style=lambda v: f"background-color: {status_colors.get(v, 'white')};"
                )
            },
            use_container_width=True,
            hide_index=True
        )

        # Update original df with edits
        df.update(edited_df)

        # =============================
        # 📥 Download Updated Data
        # =============================
        st.divider()
        st.markdown("#### 📥 Download Updated Data")

        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            label="💾 Download Excel",
            data=buffer,
            file_name="updated_payment_status.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# Run standalone app
if __name__ == "__main__":
    payment_refund_ui()
