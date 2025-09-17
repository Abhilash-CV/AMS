# seat_conversion_ui.py
import io
import json
import pandas as pd
import streamlit as st
from seat_conversion_logic import load_config, save_config, init_session, process_excel, flush_session

def seat_conversion_ui():
    st.set_page_config(page_title="Seat Conversion Dashboard", layout="wide")
    st.title("🎯 Seat Conversion Dashboard")

    # -------------------------
    # Initialize session & config
    # -------------------------
    init_session()
    config = load_config()
    current_round = st.session_state.get("last_round", 0) + 1
    st.info(f"📝 Current Round: {current_round}")

    # -------------------------
    # Tabs
    # -------------------------
    tabs = st.tabs(["📂 Upload & Convert", "📊 Converted Data", "⚙️ Conversion Rules", "🕘 Conversion History"])

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
                        uploaded, config, current_round,
                        forward_map=st.session_state.get("forward_map", {}),
                        orig_map=st.session_state.get("orig_map", {})
                    )
                    # Update session state
                    st.session_state.forward_map = fwd_map
                    st.session_state.orig_map = orig_map
                    st.session_state.last_round = current_round
                    st.session_state.converted = converted.copy()  # Latest conversion

                    # Save history
                    if "history" not in st.session_state:
                        st.session_state.history = {}
                    st.session_state.history[current_round] = converted.copy()

                    st.success(f"✅ Round {current_round} conversion completed!")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

        with col2:
            if st.button("🗑️ Clear Conversion Session"):
                flush_session()
                st.session_state.forward_map = {}
                st.session_state.orig_map = {}
                st.session_state.last_round = 0
                st.session_state.pop("converted", None)
                st.session_state.pop("history", None)
                st.success("✅ Session cleared. Ready for fresh round.")

    # -------------------------
    # Tab 2: Converted Data
    # -------------------------
    with tabs[1]:
        # Show latest converted data
        if "converted" in st.session_state and st.session_state.converted is not None:
            st.subheader(f"📊 Converted Data - Round {st.session_state.get('last_round', current_round)}")
            st.dataframe(
                st.session_state.converted.style.highlight_max(axis=0, color="#dff0d8"),
                use_container_width=True
            )

            out_buffer = io.BytesIO()
            with pd.ExcelWriter(out_buffer, engine="openpyxl") as writer:
                st.session_state.converted.to_excel(writer, sheet_name=f"Round{st.session_state.last_round}", index=False)
            st.download_button(
                "⬇️ Download Converted Excel",
                data=out_buffer.getvalue(),
                file_name=f"converted_round{st.session_state.last_round}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("No converted data available. Run a conversion first.")

    # -------------------------
    # Tab 3: Conversion Rules (Dashboard Style)
    # -------------------------
    # Tab 3: Conversion Rules (Professional Dashboard Style)
    with tabs[2]:
        # Card container with shadow and padding
        st.markdown(
            """
            <style>
            .rule-card {
                background-color: #ffffff;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.12);
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
            .rule-buttons {
                display: flex;
                gap: 10px;
                margin-top: 15px;
            }
            .rule-textarea textarea {
                background-color: #f5f7fa !important;
                border: 1px solid #ddd !important;
                border-radius: 8px !important;
                font-family: monospace !important;
                padding: 15px !important;
                width: 100% !important;
                min-height: 400px !important;
                resize: vertical;
            }
            </style>
            """, unsafe_allow_html=True
        )
    
        st.markdown('<div class="rule-card">', unsafe_allow_html=True)
    
        # Header
        st.markdown(
            """
            <div class="rule-header">
                <h2>⚙️ Conversion Rules Editor</h2>
                <span style="color:#888;">Edit JSON rules carefully</span>
            </div>
            """, unsafe_allow_html=True
        )
    
        # JSON textarea
        rules_text = st.text_area(
            "",
            value=json.dumps(config, indent=2),
            height=400,
            placeholder="Paste or edit JSON rules here...",
            help="JSON must be valid to save.",
            key="rules_editor"
        )
    
        # Real-time validation
        try:
            json.loads(rules_text)
            st.success("✅ JSON is valid")
            valid_json = True
        except Exception as e:
            st.error(f"❌ Invalid JSON: {e}")
            valid_json = False
    
        # Action buttons in horizontal layout
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("💾 Save Rules") and valid_json:
                new_cfg = json.loads(rules_text)
                save_config(new_cfg)
                st.success("✅ Rules saved successfully! Reload page to apply.")
        with col2:
            if st.button("❌ Reset Editor"):
                st.experimental_rerun()
    
        # Advanced instructions collapsible
        with st.expander("ℹ️ Advanced Instructions"):
            st.markdown("""
            - JSON keys must match schema.
            - Always use double quotes for strings.
            - Avoid trailing commas.
            - Backup rules before editing critical ones.
            """)
    
        st.markdown('</div>', unsafe_allow_html=True)


    # -------------------------
    # Tab 4: Conversion History
    # -------------------------
    with tabs[3]:
        if "history" in st.session_state and st.session_state.history:
            rounds = sorted(st.session_state.history.keys(), reverse=True)
            selected_round = st.selectbox("Select Round", rounds, index=0)
            df_round = st.session_state.history[selected_round]
            st.subheader(f"📊 Conversion History - Round {selected_round}")
            st.dataframe(df_round.style.highlight_max(axis=0, color="#dff0d8"), use_container_width=True)

            # Download button for selected round
            out_buffer = io.BytesIO()
            with pd.ExcelWriter(out_buffer, engine="openpyxl") as writer:
                df_round.to_excel(writer, sheet_name=f"Round{selected_round}", index=False)
            st.download_button(
                f"⬇️ Download Round {selected_round}",
                data=out_buffer.getvalue(),
                file_name=f"converted_round{selected_round}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("No conversion history available yet.")
