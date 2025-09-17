# seat_conversion1.py
import streamlit as st
import io
import json
import pandas as pd
from seat_conversion_logic import load_config, save_config, load_session, save_session, flush_session, process_excel

def seat_conversion_ui():
    st.header("🔄 Seat Conversion Tool")
    
    # Load session & config
    if "session" not in st.session_state:
        st.session_state.session = load_session()
    if "config" not in st.session_state:
        st.session_state.config = load_config()

    session = st.session_state.session
    config = st.session_state.config
    round_num = session.get("last_round", 0) + 1

    uploaded_file = st.file_uploader("Upload Input Excel", type=["xlsx", "xls"])
    if uploaded_file:
        st.success(f"File uploaded. Current round: {round_num}")
        if st.button("Run Conversion"):
            with st.spinner("Converting..."):
                converted, new_forward_map, new_orig_map = process_excel(
                    uploaded_file, config, round_num,
                    forward_map=session.get("forward_map", {}),
                    orig_map=session.get("orig_map", {})
                )
                session["forward_map"] = new_forward_map
                session["orig_map"] = new_orig_map
                session["last_round"] = round_num
                save_session(session)
                st.session_state.converted = converted
                st.success(f"✅ Round {round_num} conversion complete")

    if "converted" in st.session_state:
        df = st.session_state.converted
        st.subheader("Converted Data")
        st.dataframe(df, use_container_width=True)

        out_buffer = io.BytesIO()
        with pd.ExcelWriter(out_buffer, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=f"Round{round_num}", index=False)
        st.download_button(
            "📥 Download Converted Excel",
            data=out_buffer.getvalue(),
            file_name=f"converted_round{round_num}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    if st.button("Flush Session / Clear Data"):
        flush_session()
        st.session_state.session = load_session()
        if "converted" in st.session_state:
            del st.session_state.converted
        st.experimental_rerun()
