# combine_excel_ui.py
import streamlit as st
import pandas as pd
from io import BytesIO

def combine_excel_ui():
    st.header("📊 Combine Three Excel Files (Sum by Matching Columns)")
    st.write("""
    Upload three Excel files having columns:
    **CounselGroup, CollegeType, CollegeCode, CourseCode, Category, Seats**
    """)

    file1 = st.file_uploader("Upload Excel 1", type=["xlsx", "xls"])
    file2 = st.file_uploader("Upload Excel 2", type=["xlsx", "xls"])
    file3 = st.file_uploader("Upload Excel 3", type=["xlsx", "xls"])

    if file1 and file2 and file3:
        try:
            # Read Excel files
            df1 = pd.read_excel(file1)
            df2 = pd.read_excel(file2)
            df3 = pd.read_excel(file3)

            # Combine and sum
            combined = pd.concat([df1, df2, df3], ignore_index=True)
            group_cols = ['CounselGroup', 'CollegeType', 'CollegeCode', 'CourseCode', 'Category']
            combined_sum = (
                combined.groupby(group_cols, as_index=False)['Seats']
                .sum()
                .sort_values(group_cols)
                .reset_index(drop=True)
            )

            st.success("✅ Combined successfully!")
            st.dataframe(combined_sum, use_container_width=True)

            # Excel export
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                combined_sum.to_excel(writer, index=False, sheet_name="Combined_Seats")

            st.download_button(
                label="📥 Download Combined Excel",
                data=output.getvalue(),
                file_name="Combined_Seats.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        except Exception as e:
            st.error(f"⚠️ Error while processing: {e}")
    else:
        st.info("Please upload all three Excel files to start.")
