# seat_conversion_ui.py
import io
import json
import pandas as pd
import streamlit as st
from seat_conversion_logic import load_config, save_config, init_session, process_excel, flush_session

def seat_conversion_ui():
    st.title("🎯 Seat Conversion Tool")

    # -------------------------
    # Initialize session & config
    # -------------------------
    init_session()
    config = load_config()
    round_num = st.session_state.last_round + 1
    st.info(f"Current Round: {round_num}")

    # -------------------------
    # Upload & Conversion
    # -------------------------
    uploaded = st.file_uploader("📂 Upload Input Excel", type=["xlsx", "xls"])
    if uploaded and st.button("▶️ Run Conversion", type="primary"):
        try:
            converted, fwd_map, orig_map = process_excel(
                uploaded, config, round_num,
                forward_map=st.session_state.forward_map,
                orig_map=st.session_state.orig_map
            )
            st.session_state.forward_map = fwd_map
            st.session_state.orig_map = orig_map
            st.session_state.last_round = round_num
            st.session_state.converted = converted

            st.success(f"✅ Round {round_num} conversion completed!")
        except Exception as e:
            st.error(f"❌ Error: {e}")

    # -------------------------
    # Display Converted Data
    # -------------------------
    if "converted" in st.session_state:
        st.subheader("📊 Converted Data")
        st.dataframe(st.session_state.converted, use_container_width=True)

        # Download button
        out_buffer = io.BytesIO()
        with pd.ExcelWriter(out_buffer, engine="openpyxl") as writer:
            st.session_state.converted.to_excel(writer, sheet_name=f"Round{round_num}", index=False)
        st.download_button(
            "⬇️ Download Converted Excel",
            data=out_buffer.getvalue(),
            file_name=f"converted_round{round_num}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # -------------------------
    # Rule Editor (popup-style container)
    # -------------------------
    if "show_rules_editor" not in st.session_state:
        st.session_state.show_rules_editor = False

    if st.button("⚙️ Edit Conversion Rules"):
        st.session_state.show_rules_editor = True

    if st.session_state.show_rules_editor:
        with st.container():
            st.markdown(
                """
                <div style="
                    border: 2px solid #4CAF50;
                    border-radius: 12px;
                    padding: 20px;
                    background-color: #f9f9f9;
                ">
                """,
                unsafe_allow_html=True
            )
            st.subheader("🛠 Edit Conversion Rules")
            rules_text = st.text_area(
                "Rules (JSON)",
                value=json.dumps(config, indent=2),
                height=400
            )

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("💾 Save Rules"):
                    try:
                        new_cfg = json.loads(rules_text)
                        save_config(new_cfg)
                        st.success("✅ Rules updated successfully! Reload page to apply.")
                        st.session_state.show_rules_editor = False
                    except Exception as e:
                        st.error(f"Invalid JSON: {e}")
            with col2:
                if st.button("❌ Close"):
                    st.session_state.show_rules_editor = False

            st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------
    # Clear / Reset Session
    # -------------------------
    if st.button("🗑️ Clear Conversion Session (Reset)"):
        flush_session()
        st.session_state.forward_map = {}
        st.session_state.orig_map = {}
        st.session_state.last_round = 0
        if "converted" in st.session_state:
            del st.session_state.converted
        st.success("✅ Session data cleared. Ready for fresh round.")
