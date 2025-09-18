# seat_conversion_ui.py
import io
import json
import pandas as pd
import streamlit as st
from seat_conversion_logic import load_config, save_config, init_session, process_excel, flush_session

def seat_conversion_ui():
    st.set_page_config(page_title="Seat Conversion Dashboard", layout="wide")
    st.subheader("🔄 Seat Conversion")

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
    from streamlit_ace import st_ace
    
    with tabs[2]:
        st.markdown("<h2 style='color:#4CAF50; margin-bottom:5px;'>⚙️ Conversion Rules Editor</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color:#555; margin-top:0;'>Each category is displayed in separate compact boxes with multi-column editable fields.</p>", unsafe_allow_html=True)
    
        new_config = {}
    
        for category, rules in config.items():
            # Card container
            st.markdown(
                f"""
                <div style="
                    border-radius:12px;
                    padding:15px 20px;
                    background-color:#ffffff;
                    box-shadow:0 6px 18px rgba(0,0,0,0.12);
                    margin-bottom:20px;
                    border-left:5px solid #4CAF50;
                ">
                    <h4 style='margin:0 0 5px 0; color:#4CAF50; font-size:16px;'>{category}</h4>
                </div>
                """, unsafe_allow_html=True
            )
    
            # Initialize category in new config
            new_config[category] = {}
    
            # If dict → multi-column editable fields
            if isinstance(rules, dict):
                keys = list(rules.keys())
                num_cols = 2  # Adjust for screen width
                cols = st.columns(num_cols, gap="small")
    
                for idx, key in enumerate(keys):
                    col = cols[idx % num_cols]
                    new_val = col.text_input(
                        label="",  # no label to reduce row height
                        value=str(rules[key]),
                        key=f"{category}_{key}",
                        placeholder=key
                    )
                    new_config[category][key] = new_val
    
            # If list/string → fixed-height textarea
            else:
                new_val = st.text_area(
                    label="",
                    value=json.dumps(rules, indent=2),
                    key=f"{category}_raw",
                    height=160,  # reduced height
                    placeholder=f"{category} content"
                )
                try:
                    new_config[category] = json.loads(new_val)
                except:
                    new_config[category] = new_val
    
        # Standardized Save / Reset buttons
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("💾 Save All Rules", key="save_btn"):
                save_config(new_config)
                st.success("✅ All rules saved successfully!")
        with col2:
            if st.button("❌ Reset Editor", key="reset_btn"):
                st.experimental_rerun()
    
        # Collapsible advanced instructions
        with st.expander("ℹ️ Advanced Instructions"):
            st.markdown("""
            - Dicts are displayed in multiple columns for readability.
            - Lists/strings are in a fixed-height textarea.
            - Compact layout reduces vertical scroll and standardizes row height.
            - Keep JSON formatting correct before saving.
            - Backup rules before editing critical categories.
            """)



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
