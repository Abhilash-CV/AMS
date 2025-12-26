import streamlit as st
import pandas as pd

EXCEL_PATH = "Checklist_Single.xlsx"   # keep in app root

def checklist_ui(year, program):
    st.header("📘 Admission Process – Master Verification Checklist")
    st.caption(f"Academic Year: {year} | Program: {program}")
    st.info("Static reference view (as per approved checklist Excel)")

    # Load Excel
    df = pd.read_excel(EXCEL_PATH)

    # Normalize column names
    df.columns = ["Main", "Sub", "Description"]

    # Forward fill merged cells (VERY IMPORTANT)
    df["Main"] = df["Main"].ffill()
    df["Sub"] = df["Sub"].ffill()

    # Unique main sections → Tabs
    main_sections = df["Main"].dropna().unique().tolist()

    tabs = st.tabs(main_sections)

    for i, section in enumerate(main_sections):
        with tabs[i]:
            st.subheader(section)

            section_df = df[df["Main"] == section][["Sub", "Description"]]
            section_df = section_df.rename(columns={
                "Sub": "Checklist Item",
                "Description": "Description / Validation Points"
            })

            st.dataframe(
                section_df,
                use_container_width=True,
                hide_index=True
            )
