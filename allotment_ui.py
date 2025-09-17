# allotment_ui.py
import streamlit as st
from common_connection import load_table, download_button_for_df


def allotment_ui(year=None, program=None):
    st.subheader("📜 Allotment")
    
    # Load data
    df_allot = load_table("Allotment", year, program)

    if df_allot.empty:
        st.info("No allotment data found yet.")
    else:
        download_button_for_df(df_allot, f"Allotment_{year}_{program}")
        st.dataframe(df_allot, use_container_width=True)
