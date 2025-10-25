import streamlit as st
import pandas as pd
from io import BytesIO

st.title("🔗 Combine Three Excel Files (Sum Seats by Matching Columns)")

st.write("""
Upload three Excel files having columns:
**CounselGroup, CollegeType, CollegeCode, CourseCode, Category, Seats**
""")

# Upload three Excel files
file1 = st.file_uploader("Upload Excel 1", type=["xlsx", "xls"])
file2 = st.file_uploader("Upload Excel 2", type=["xlsx", "xls"])
file3 = st.file_uploader("Upload Excel 3", type=["xlsx", "xls"])

if file1 and file2 and file3:
    try:
        # Read files
        df1 = pd.read_excel(file1)
        df2 = pd.read_excel(file2)
        df3 = pd.read_excel(file3)

        # Combine all data
        combined = pd.concat([df1, df2, df3], ignore_index=True)

        # Group by matching columns & sum Seats
        group_cols = ['CounselGroup', 'CollegeType', 'CollegeCode', 'CourseCode', 'Category']
        combined_sum = combined.groupby(group_cols, as_index=False)['Seats'].sum()

        st.success("✅ Files combined successfully!")

        # Show preview
        st.dataframe(combined_sum)

        # Export to Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            combined_sum.to_excel(writer, index=False, sheet_name="Combined_Seats")

        st.download_button(
            label="📥 Download Combined Excel",
            data=output.getvalue(),
            file_name="Combined_Seats.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"⚠️ Error: {e}")
else:
    st.info("Please upload all three Excel files to proceed.")
