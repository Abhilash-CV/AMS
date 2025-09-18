# seat_comparison_ui.py
import pandas as pd
import streamlit as st
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

# ---------------- TYPE MAP ----------------
TYPE_MAP = {
    "G": "Govt",
    "S": "Self-financing",
    "A": "Aided",
    "P": "Private",
}

def get_type_from_code(code: str) -> str:
    if not code or len(code) < 2:
        return "Unknown"
    return TYPE_MAP.get(code[1].upper(), "Other")


# ---------------- MAIN COMPARISON ----------------
def compare_excels(file1, file2):
    df1 = pd.read_excel(file1, engine="openpyxl")
    df2 = pd.read_excel(file2, engine="openpyxl")

    df1.columns = ["Code1", "Seats1"]
    df2.columns = ["Code2", "Seats2"]

    results = []

    for _, row1 in df1.iterrows():
        code1, seats1 = row1["Code1"], row1["Seats1"]
        result = seats1
        code2, seats2 = None, None

        # 1) Exact match
        match = df2[df2["Code2"] == code1]
        if not match.empty:
            code2, seats2 = match.iloc[0]["Code2"], match.iloc[0]["Seats2"]
            result = seats1 - seats2
        else:
            # 2) Match by first 7 chars
            prefix = code1[:7]
            possible_matches = df2[df2["Code2"].str[:7] == prefix]

            if not possible_matches.empty:
                cat1 = code1[9:11]  # category (10th,11th)
                match_cat = possible_matches[possible_matches["Code2"].str[9:11] == cat1]

                if not match_cat.empty:
                    code2, seats2 = match_cat.iloc[0]["Code2"], match_cat.iloc[0]["Seats2"]
                    result = seats1 - seats2
                else:
                    code2, seats2 = possible_matches.iloc[0]["Code2"], possible_matches.iloc[0]["Seats2"]
                    result = seats1 - seats2

        row_type = get_type_from_code(code1)
        results.append([row_type, code1, seats1, code2, seats2, result])

    output_df = pd.DataFrame(
        results,
        columns=["Type", "Input1_Code", "Input1_Seats", "Input2_Code", "Input2_Seats", "Difference"]
    )

    # Highlight cells in Difference column (openpyxl styling)
    output = BytesIO()
    output_df.to_excel(output, index=False)
    output.seek(0)

    wb = load_workbook(output)
    ws = wb.active
    red_fill = PatternFill(start_color="FF9999", end_color="FF9999", fill_type="solid")

    for row in range(2, ws.max_row + 1):
        diff_val = ws.cell(row=row, column=6).value
        if diff_val is not None and diff_val != 0:
            ws.cell(row=row, column=6).fill = red_fill

    final_output = BytesIO()
    wb.save(final_output)
    final_output.seek(0)
    return output_df, final_output


# ---------------- STREAMLIT UI ----------------
def seat_comparison_ui():
    st.subheader("📊 Excel Seat Comparison Tool")

    st.info("Upload two Excel files to compare seat matrices.")

    col1, col2 = st.columns(2)
    with col1:
        file1 = st.file_uploader("Upload Input Excel 1", type=["xlsx", "xls"], key="file1")
    with col2:
        file2 = st.file_uploader("Upload Input Excel 2", type=["xlsx", "xls"], key="file2")

    if file1 and file2:
        if st.button("🔍 Run Comparison"):
            with st.spinner("Comparing seats..."):
                try:
                    df_out, excel_out = compare_excels(file1, file2)

                    st.success("✅ Comparison completed!")
                    st.dataframe(df_out, use_container_width=True)

                    st.download_button(
                        "📥 Download Comparison Excel",
                        data=excel_out,
                        file_name="seat_comparison.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"Error: {e}")
