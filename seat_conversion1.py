# seat_conversion_ui.py
import io
import json
import pandas as pd
import streamlit as st
from seat_conversion_logic import load_config, save_config, init_session, process_excel, flush_session

def seat_conversion_ui():
    st.set_page_config(page_title="Seat Conversion Tool", layout="wide")
    st.title("🎯 Seat Conversion Tool")

    # -------------------------
    # Initialize session & config
    # -------------------------
    init_session()
    config = load_config()
    round_num = st.session_state.get("last_round", 0) + 1
    st.info(f"📝 Current Round: {round_num}")

    # -------------------------
    # Main Tabs
    # -------------------------
    tabs = st.tabs(["📂 Upload & Convert", "📊 Converted Data", "⚙️ Conversion Rules"])

    # -------------------------
    # Tab 1: Upload & Convert
    # -------------------------
    with tabs[0]:
        uploaded = st.file_uploader("Upload Input Excel", type=["xlsx", "xls"])
        col1, col2 = st.columns([1,1])
        with col1:
            if uploaded and st.button("▶️ Run Conversion", type="primary"):
                try:
                    converted, fwd_map, orig_map = process_excel(
                        uploaded, config, round_num,
                        forward_map=st.session_state.get("forward_map", {}),
                        orig_map=st.session_state.get("orig_map", {})
                    )
                    st.session_state.forward_map = fwd_map
                    st.session_state.orig_map = orig_map
                    st.session_state.last_round = round_num
                    st.session_state.converted = converted
                    st.success(f"✅ Round {round_num} conversion completed!")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        with col2:
            if st.button("🗑️ Clear Conversion Session"):
                flush_session()
                st.session_state.forward_map = {}
                st.session_state.orig_map = {}
                st.session_state.last_round = 0
                st.session_state.pop("converted", None)
                st.success("✅ Session cleared. Ready for a fresh round.")

    # -------------------------
    # Tab 2: Converted Data
    # -------------------------
    with tabs[1]:
        if "converted" in st.session_state:
            st.dataframe(st.session_state.converted, use_container_width=True)
            out_buffer = io.BytesIO()
            with pd.ExcelWriter(out_buffer, engine="openpyxl") as writer:
                st.session_state.converted.to_excel(writer, sheet_name=f"Round{round_num}", index=False)
            st.download_button(
                "⬇️ Download Converted Excel",
                data=out_buffer.getvalue(),
                file_name=f"converted_round{round_num}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("No converted data available. Please run a conversion first.")

    # -------------------------
    # Tab 3: Conversion Rules
    # -------------------------
    # -------------------------
# Tab 3: Conversion Rules (Professional Look)
# -------------------------
    with tabs[2]:
        st.markdown(
            """
            <div style="
                border-radius: 15px;
                padding: 25px;
                background-color: #ffffff;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
                margin-bottom: 20px;
            ">
            <h3 style='color:#4CAF50;'>⚙️ Conversion Rules Editor</h3>
            <p style='color:#555;'>Edit your JSON rules below. Ensure proper formatting before saving.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
        rules_text = st.text_area(
            "",
            value=json.dumps(config, indent=2),
            height=400,
            max_chars=None,
            help="Edit JSON rules carefully. Invalid JSON will not be saved.",
            placeholder="Paste or edit JSON rules here..."
        )
    
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("💾 Save Rules"):
                try:
                    new_cfg = json.loads(rules_text)
                    save_config(new_cfg)
                    st.success("✅ Rules updated successfully! Reload page to apply.")
                except Exception as e:
                    st.error(f"❌ Invalid JSON: {e}")
    
        with col2:
            if st.button("❌ Reset Editor"):
                st.experimental_rerun()


        st.markdown("</div>", unsafe_allow_html=True)


