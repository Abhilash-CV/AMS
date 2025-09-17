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

   # -------------------------
# Tab 3: Conversion Rules (Dashboard-style Professional)
# -------------------------
    with tabs[2]:
        # Custom card container with shadow and padding
        st.markdown(
            """
            <style>
            .rule-card {
                background-color: #ffffff;
                border-radius: 12px;
                padding: 25px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.12);
                margin-bottom: 20px;
                font-family: 'Courier New', monospace;
            }
            .rule-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }
            .rule-header h2 {
                margin: 0;
                color: #4CAF50;
            }
            .rule-buttons button {
                margin-left: 10px;
            }
            .rule-textarea {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                font-family: monospace;
                width: 100%;
                min-height: 350px;
                resize: vertical;
            }
            </style>
            """, unsafe_allow_html=True
        )
    
        st.markdown('<div class="rule-card">', unsafe_allow_html=True)
    
        # Header with title and info
        st.markdown(
            """
            <div class="rule-header">
                <h2>⚙️ Conversion Rules Editor</h2>
                <span style="color:#888;">Edit JSON rules carefully</span>
            </div>
            """, unsafe_allow_html=True
        )
    
        # JSON Textarea
        rules_text = st.text_area(
            "",
            value=json.dumps(config, indent=2),
            height=400,
            max_chars=None,
            placeholder="Paste or edit JSON rules here...",
            help="JSON must be valid. Use double quotes for strings and no trailing commas."
        )
    
        # Real-time validation
        try:
            json.loads(rules_text)
            st.success("✅ JSON is valid")
            valid_json = True
        except Exception as e:
            st.error(f"❌ Invalid JSON: {e}")
            valid_json = False
    
        # Buttons aligned horizontally
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("💾 Save Rules") and valid_json:
                new_cfg = json.loads(rules_text)
                save_config(new_cfg)
                st.success("✅ Rules saved successfully! Reload page to apply.")
        with col2:
            if st.button("❌ Reset Editor"):
                st.experimental_rerun()
    
        # Advanced instructions
        with st.expander("ℹ️ Advanced Instructions"):
            st.markdown("""
            - JSON keys must match the expected schema.
            - Always use double quotes for strings.
            - Avoid trailing commas.
            - Make a backup before editing critical rules.
            """)
    
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

