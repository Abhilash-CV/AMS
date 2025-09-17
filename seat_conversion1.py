# seat_conversion1.py
import io
import json
import streamlit as st
import pandas as pd
from seat_conversion_logic import load_config, save_config, init_session, process_excel, flush_session

# -----------------------------
# Seat Conversion Rules Editor
# -----------------------------
def edit_rules_ui(config):
    """
    Edits seat conversion rules in a safe, version-independent way.
    Returns updated config if saved, else returns original config.
    """
    st.subheader("⚙️ Edit Conversion Rules")
    
    with st.expander("Open Rules Editor"):
        rules_text = st.text_area(
            "Rules (JSON)",
            value=json.dumps(config, indent=2),
            height=300
        )

        if st.button("💾 Save Rules"):
            try:
                new_cfg = json.loads(rules_text)
                save_config(new_cfg)
                st.success("✅ Rules updated successfully! Reload page to apply.")
                return new_cfg
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
    
    return config

# -----------------------------
# Main Seat Conversion UI
# -----------------------------
def seat_conversion_ui():
    st.title("🎯 Seat Conversion Tool")
    
    # Initialize session & config
    init_session()
    if "config" not in st.session_state:
        st.session_state.config = load_config()
    config = st.session_state.config

    # Edit rules
    st.session_state.config = edit_rules_ui(config)
    
    # Display current round
    round_num = st.session_state.last_round + 1
    st.info(f"Current Round: {round_num}")

    # File uploader
    uploaded = st.file_uploader("Upload Input Excel", type=["xlsx", "xls"])
    
    if uploaded and st.button("Run Conversion", type="primary"):
        try:
            converted, fwd_map, orig_map = process_excel(
                uploaded,
                st.session_state.config,
                round_num,
                forward_map=st.session_state.forward_map,
                orig_map=st.session_state.orig_map
            )

            # Update session state
            st.session_state.forward_map = fwd_map
            st.session_state.orig_map = orig_map
            st.session_state.last_round = round_num
            st.session_state.converted = converted

            st.success(f"✅ Round {round_num} conversion completed!")
            st.dataframe(converted)

            # Download converted Excel
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

    # Flush session
    if st.button("🧹 Flush Session (Reset)"):
        flush_session()
        init_session()
        st.experimental_rerun()
