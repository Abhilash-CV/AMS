# seat_conversion1.py
import io
import json
import pandas as pd
import streamlit as st
from seat_conversion_logic import load_config, save_config, init_session, process_excel, flush_session

def seat_conversion_ui():
    st.header("🔄 Seat Conversion Tool")
    init_session()
    config = load_config()
    round_num = st.session_state.last_round + 1

    # -------------------------
    # File Upload & Conversion
    # -------------------------
    uploaded_file = st.file_uploader("Upload Input Excel", type=["xlsx", "xls"])
    if uploaded_file:
        st.success(f"File uploaded. Current Round: {round_num}")
        if st.button("Run Conversion", type="primary"):
            with st.spinner("Converting..."):
                converted, new_forward_map, new_orig_map = process_excel(
                    uploaded_file,
                    config,
                    round_num,
                    forward_map=st.session_state.forward_map,
                    orig_map=st.session_state.orig_map
                )
                st.session_state.forward_map = new_forward_map
                st.session_state.orig_map = new_orig_map
                st.session_state.last_round = round_num
                st.session_state.converted = converted

                st.success(f"✅ Round {round_num} conversion complete")

    # -------------------------
    # Show Converted Data
    # -------------------------
    if "converted" in st.session_state:
        df = st.session_state.converted
        st.subheader("Converted Data")
        st.dataframe(df, use_container_width=True)

        # Download button
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=f"Round{round_num}", index=False)
        st.download_button(
            "📥 Download Converted Excel",
            data=output.getvalue(),
            file_name=f"converted_round{round_num}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # -------------------------
    # Edit Rules in Modal
    # -------------------------
    if st.button("⚙️ Edit Conversion Rules"):
        # Opens a modal (Streamlit >=1.24)
        with st.modal("Edit Conversion Rules"):
            rules_text = st.text_area(
                "Rules (JSON)",
                value=json.dumps(config, indent=2),
                height=300
            )
            if st.button("💾 Save Rules", key="save_rules_modal"):
                try:
                    new_cfg = json.loads(rules_text)
                    save_config(new_cfg)
                    st.success("✅ Rules updated successfully! Reload page to apply.")
                except Exception as e:
                    st.error(f"Invalid JSON: {e}")

    # -------------------------
    # Flush Session Button
    # -------------------------
    if st.button("🗑️ Flush Session (Reset)"):
        flush_session()
        st.session_state.forward_map = {}
        st.session_state.orig_map = {}
        st.session_state.last_round = 0
        st.experimental_rerun()
