# combine_excel_ui.py
import streamlit as st
import pandas as pd
from io import BytesIO

def combine_excel1_ui():
    st.header("📊 Combine Rows with Same Keys (Sum Seats)")

    st.write("""
    Upload a single Excel file with columns:
    **CounselGroup, CollegeType, CollegeCode, CourseCode, Category, Seat**
    """)

    file = st.file_uploader("Upload Excel File", type=["xlsx", "xls"])

    if file:
        try:
            df = pd.read_excel(file)

            # Clean column names (remove spaces, unify case)
            df.columns = df.columns.str.strip()

            required_cols = ['CounselGroup', 'CollegeType', 'CollegeCode', 'CourseCode', 'Category', 'Seat']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                st.error(f"❌ Missing columns: {', '.join(missing_cols)}")
                return

            # Group and sum
            group_cols = ['CounselGroup', 'CollegeType', 'CollegeCode', 'CourseCode', 'Category']
            combined_sum = (
                df.groupby(group_cols, as_index=False)['Seat']
                .sum()
                .sort_values(group_cols)
                .reset_index(drop=True)
            )

            st.success("✅ Grouped successfully!")
            st.dataframe(combined_sum, use_container_width=True)

            # Prepare download
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                combined_sum.to_excel(writer, index=False, sheet_name="Combined_Seats")

            st.download_button(
                label="📥 Download Grouped Excel",
                data=output.getvalue(),
                file_name="Grouped_Seats.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        except Exception as e:
            st.error(f"⚠️ Error while processing: {e}")
    else:
        st.info("Please upload your Excel file to begin.")
