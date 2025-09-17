# seat_conversion.py
import io
import pandas as pd
import streamlit as st
from seat_conversion_logic import load_config, init_session, process_excel

def seat_conversion_ui():
    st.title("🎯 Seat Conversion Tool")
    init_session()
    config = load_config()

    st.info(f"Current Round: {st.session_state.last_round + 1}")
    uploaded = st.file_uploader("Upload Input Excel", type=["xlsx", "xls"])
    if uploaded and st.button("Run Conversion", type="primary"):
        try:
            round_num = st.session_state.last_round + 1
            converted, fwd_map, orig_map = process_excel(
                uploaded, config, round_num,
                forward_map=st.session_state.forward_map,
                orig_map=st.session_state.orig_map
            )
            st.session_state.forward_map = fwd_map
            st.session_state.orig_map = orig_map
            st.session_state.last_round = round_num

            st.success(f"✅ Round {round_num} conversion completed!")
            st.dataframe(converted)

            out_buffer = io.BytesIO()
            with pd.ExcelWriter(out_buffer, engine="openpyxl") as writer:
                converted.to_excel(writer, sheet_name=f"Round{round_num}", index=False)
            st.download_button(
                "⬇️ Download Converted Excel",
                data=out_buffer.getvalue(),
                file_name=f"converted_round{round_num}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Error: {e}")
