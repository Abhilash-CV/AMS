# seat_conversion_streamlit.py
import os
import json
import math
import io
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------
# Config / Session Files
# ---------------------------
CONFIG_FILE = "config.json"
SESSION_FILE = "session_state.json"

# ---------------------------
# Config management
# ---------------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # default config
    return {
        "no_conversion": ["MG"],
        "direct_to_sm": ["EZ","EW", "MU", "BX", "LA", "BH", "DV", "VK", "KN", "KU"],
        "swap_pairs": [["PI", "PT"]],
        "ladders": {
            "SC": ["ST", "OE", "SM"],
            "ST": ["SC", "OE", "SM"],
            "DK": ["HR", "SD", "XS"],
            "HR": ["SD", "XS"],
            "OE": ["SM"],
            "SD": ["XS"]
        },
        "direct_to_mp": ["XS", "PD"],
        "mp_distribution": {
            "SM": 0.50, "EWS": 0.10,
            "EZ": 0.09, "MU": 0.08, "BH": 0.03, "LA": 0.03,
            "DV": 0.02, "VK": 0.02, "KN": 0.01, "BX": 0.01, "KU": 0.01,
            "SC": 0.08, "ST": 0.02
        }
    }

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

# ---------------------------
# Session management
# ---------------------------
def load_session():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "forward_map" not in data:
                    data["forward_map"] = {}
                if "orig_map" not in data:
                    data["orig_map"] = {}
                return data
        except Exception:
            pass
    return {"forward_map": {}, "orig_map": {}, "last_round": 0}

def save_session(data):
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def flush_session():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

# ---------------------------
# Seat Conversion Logic
# ---------------------------
def distribute_to_mp(seats, source_cat, config, carry_forward=None):
    """
    Distribute total seats into MP categories using Hamilton rounding and carry-forward.
    carry_forward: dict used to track fractional seat remainders between programs
    """
    if carry_forward is None:
        carry_forward = {}

    DEFAULT_MP = {
        "SM": 0.50, "EWS": 0.10,
        "EZ": 0.09, "MU": 0.08, "BH": 0.03, "LA": 0.03,
        "DV": 0.02, "VK": 0.02, "KN": 0.01, "BX": 0.01, "KU": 0.01,
        "SC": 0.08, "ST": 0.02
    }

    mp_rules = config.get("mp_distribution") or DEFAULT_MP
    total = sum(mp_rules.values())
    pct = {k: v / total for k, v in mp_rules.items()}

    # Add carry-forward from previous call
    effective = {cat: pct[cat] * seats + carry_forward.get(cat, 0) for cat in pct.keys()}

    # Floor allocation
    alloc = {cat: int(math.floor(val)) for cat, val in effective.items()}
    assigned = sum(alloc.values())
    diff = int(round(seats - assigned))

    # Hamilton (largest remainder) for remaining seats
    remainders = sorted(
        [(cat, effective[cat] - alloc[cat]) for cat in pct.keys()],
        key=lambda x: -x[1]
    )
    for cat, _ in remainders[:diff]:
        alloc[cat] += 1

    # Compute carry-forward for next call
    next_carry = {cat: effective[cat] - alloc[cat] for cat in pct.keys()}

    # Build result
    rows = []
    for cat, val in alloc.items():
        if val > 0:
            rows.append({"Category": cat, "Seats": int(val), "ConvertedFrom": source_cat})

    return rows, next_carry

def convert_seats(df, config, forward_map=None, orig_map=None):
    df = df.copy()
    df["Category"] = df["Category"].astype(str).str.strip().str.upper()
    df["Seats"] = pd.to_numeric(df["Seats"], errors="coerce").fillna(0).astype(int)

    ladders = {k.strip().upper(): [x.strip().upper() for x in v] for k, v in config.get("ladders", {}).items()}
    direct_to_mp = [c.strip().upper() for c in config.get("direct_to_mp", [])]
    direct_to_sm = [c.strip().upper() for c in config.get("direct_to_sm", [])]
    swap_pairs = [(a.strip().upper(), b.strip().upper()) for a, b in config.get("swap_pairs", [])]
    no_conversion = [c.strip().upper() for c in config.get("no_conversion", [])]

    if forward_map is None:
        forward_map = {}
    if orig_map is None:
        orig_map = {}

    results = []
    group_keys = ["Stream", "InstType", "Course", "College"]
    grouped = df.groupby(group_keys, sort=False)

    for group_vals, group in grouped:
        stream, inst, course, college = group_vals
        seats_by_cat = group.groupby("Category", sort=False)["Seats"].sum().to_dict()
        handled = set()
        converted_targets = set()
        orig_cats = list(group["Category"].unique())

        # Preserve original category
        for cat in orig_cats:
            key = f"{stream}-{inst}-{course}-{college}-{cat}"
            if key not in orig_map:
                orig_map[key] = cat

        # OE -> SM
        if seats_by_cat.get("OE", 0) > 0 and seats_by_cat.get("SM", 0) == 0:
            oe_seats = seats_by_cat["OE"]
            results.append({
                "Stream": stream, "InstType": inst, "Course": course, "College": college,
                "OriginalCategory": orig_map.get(f"{stream}-{inst}-{course}-{college}-OE", "OE"),
                "Category": "SM", "Seats": oe_seats,
                "ConvertedFrom": "OE", "ConversionFlag": "Y", "ConversionReason": "OE_to_SM"
            })
            handled.add("OE")
            seats_by_cat["OE"] = 0

        # SD -> XS
        if seats_by_cat.get("SD", 0) > 0 and seats_by_cat.get("XS", 0) == 0:
            sd_seats = seats_by_cat["SD"]
            results.append({
                "Stream": stream, "InstType": inst, "Course": course, "College": college,
                "OriginalCategory": orig_map.get(f"{stream}-{inst}-{course}-{college}-SD", "SD"),
                "Category": "XS", "Seats": sd_seats,
                "ConvertedFrom": "SD", "ConversionFlag": "Y", "ConversionReason": "SD_to_XS"
            })
            handled.add("SD")
            seats_by_cat["SD"] = 0

        # Direct -> MP
        # Direct -> MP (with Hamilton rounding + carry-forward)
        mp_carry = {}
        for cat in direct_to_mp:
            seats = seats_by_cat.get(cat, 0)
            if seats > 0:
                rows, mp_carry = distribute_to_mp(seats, cat, config, carry_forward=mp_carry)
                for r in rows:
                    results.append({
                        "Stream": stream, "InstType": inst, "Course": course, "College": college,
                        "OriginalCategory": orig_map.get(f"{stream}-{inst}-{course}-{college}-{cat}", cat),
                        "Category": r["Category"], "Seats": r["Seats"],
                        "ConvertedFrom": cat, "ConversionFlag": "Y", "ConversionReason": "DirectToMP"
                    })
                handled.add(cat)
                seats_by_cat[cat] = 0


        # Ladder conversions
        for src_cat in orig_cats:
            if src_cat in handled:
                continue
            src_seats = seats_by_cat.get(src_cat, 0)
            if src_seats <= 0:
                continue
            if src_cat in ladders:
                chosen = src_cat
                for nxt in ladders[src_cat]:
                    if forward_map.get(nxt) == src_cat:
                        continue
                    if src_cat == "SC" and nxt == "ST" and seats_by_cat.get("ST", 0) > 0:
                        continue
                    if src_cat == "ST" and nxt == "SC" and seats_by_cat.get("SC", 0) > 0:
                        continue
                    if seats_by_cat.get(nxt, 0) == 0:
                        chosen = nxt
                        break
                if chosen != src_cat:
                    forward_map[src_cat] = chosen
                    results.append({
                        "Stream": stream, "InstType": inst, "Course": course, "College": college,
                        "OriginalCategory": orig_map.get(f"{stream}-{inst}-{course}-{college}-{src_cat}", src_cat),
                        "Category": chosen, "Seats": src_seats,
                        "ConvertedFrom": src_cat, "ConversionFlag": "Y",
                        "ConversionReason": f"{src_cat}_to_{chosen}"
                    })
                    seats_by_cat[chosen] = seats_by_cat.get(chosen, 0) + src_seats
                    seats_by_cat[src_cat] = 0
                    handled.add(src_cat)
                    converted_targets.add(chosen)

        # Direct -> SM after ladders
        for cat in direct_to_sm:
            if cat in handled:
                continue
            seats = seats_by_cat.get(cat, 0)
            if seats > 0:
                results.append({
                    "Stream": stream, "InstType": inst, "Course": course, "College": college,
                    "OriginalCategory": orig_map.get(f"{stream}-{inst}-{course}-{college}-{cat}", cat),
                    "Category": "SM", "Seats": seats,
                    "ConvertedFrom": cat, "ConversionFlag": "Y", "ConversionReason": "DirectToSM"
                })
                handled.add(cat)
                seats_by_cat[cat] = 0

        # Swap pairs
        for a, b in swap_pairs:
            a_seats = seats_by_cat.get(a, 0)
            b_seats = seats_by_cat.get(b, 0)
            if a_seats > 0 and b_seats > 0:
                results.append({
                    "Stream": stream, "InstType": inst, "Course": course, "College": college,
                    "OriginalCategory": orig_map.get(f"{stream}-{inst}-{course}-{college}-{a}", a),
                    "Category": b, "Seats": a_seats,
                    "ConvertedFrom": a, "ConversionFlag": "Y", "ConversionReason": f"{a}_to_{b}"
                })
                handled.add(a)
                seats_by_cat[a] = 0

        # Remaining categories
        for cat in orig_cats:
            if cat in handled or cat in converted_targets:
                continue
            results.append({
                "Stream": stream, "InstType": inst, "Course": course, "College": college,
                "OriginalCategory": orig_map.get(f"{stream}-{inst}-{course}-{college}-{cat}", cat),
                "Category": cat,
                "Seats": seats_by_cat.get(cat, 0),
                "ConvertedFrom": "", "ConversionFlag": "N",
                "ConversionReason": "NoRule_keep" if cat not in no_conversion else "NoConversion"
            })

    out_df = pd.DataFrame(results)
    columns_order = ["Stream", "InstType", "Course", "College",
                     "OriginalCategory", "Category", "Seats",
                     "ConvertedFrom", "ConversionFlag", "ConversionReason"]
    out_df = out_df[[c for c in columns_order if c in out_df.columns]]
    return out_df, forward_map, orig_map

# ---------------------------
# Process Excel
# ---------------------------
def process_excel(input_file, output_file, config, round_num, forward_map=None, orig_map=None):
    df = pd.read_excel(input_file, engine="openpyxl")

    work_df = df.rename(columns={
        "CounselGroup": "Stream",
        "CollegeType": "InstType",
        "CollegeCode": "College",
        "CourseCode": "Course",
        "Category": "Category",
        "Seat": "Seats"
    })

    converted, forward_map, orig_map = convert_seats(
        work_df[["Stream", "InstType", "Course", "College", "Category", "Seats"]],
        config,
        forward_map=forward_map,
        orig_map=orig_map
    )
    converted["Round"] = round_num

    # Summary
    converted_summary = converted.rename(columns={
        "Stream": "CounselGroup",
        "InstType": "CollegeType",
        "College": "CollegeCode",
        "Course": "CourseCode",
        "Seats": "Seat"
    })
    summary_cols = ["CounselGroup","CollegeType","CourseCode","CollegeCode","OriginalCategory","Category","Seat"]
    for col in summary_cols:
        if col not in converted_summary.columns:
            converted_summary[col] = ""
    converted_summary = converted_summary[summary_cols]

    # Save Excel
    output_file = Path(output_file)
    mode = 'w' if not output_file.exists() else 'a'
    with pd.ExcelWriter(output_file, engine="openpyxl", mode=mode) as writer:
        df.to_excel(writer, sheet_name="InputData", index=False)
        converted.to_excel(writer, sheet_name=f"ConvertedRound{round_num}", index=False)
        converted_summary.to_excel(writer, sheet_name=f"SummaryRound{round_num}", index=False)

    return converted_summary, converted, forward_map, orig_map

# ---------------------------
# Streamlit UI
# ---------------------------
def seat_conversion_ui():
    st.title("🎯 Seat Conversion Tool")
    st.caption("Apply conversion rules round by round")

    config = load_config()
    session = load_session()
    current_round = session.get("last_round", 0) + 1
    st.info(f"**Current Round:** {current_round}")

    uploaded_file = st.file_uploader("📂 Upload Input Excel", type=["xlsx", "xls"])
    if uploaded_file:
        try:
            df_preview = pd.read_excel(uploaded_file, engine="openpyxl")
        except Exception:
            uploaded_file.seek(0)
            df_preview = pd.read_excel(uploaded_file, engine="xlrd")
        st.dataframe(df_preview.head())

    col1, col2, col3 = st.columns(3)
    with col1: run = st.button("▶️ Run Conversion")
    with col2: edit = st.button("🧩 Edit Rules")
    with col3: reset = st.button("♻️ Flush Session")

    if edit:
        with st.expander("Edit Conversion Rules", expanded=True):
            no_conversion = st.text_input("No Conversion", ",".join(config.get("no_conversion", [])))
            direct_to_sm = st.text_input("Direct → SM", ",".join(config.get("direct_to_sm", [])))
            direct_to_mp = st.text_input("Direct → MP", ",".join(config.get("direct_to_mp", [])))
            ladders_raw = "; ".join([f"{k}:{','.join(v)}" for k, v in config.get("ladders", {}).items()])
            ladders_text = st.text_area("Ladders", ladders_raw)

            if st.button("💾 Save Rules"):
                try:
                    new_cfg = {
                        "no_conversion": [x.strip().upper() for x in no_conversion.split(",") if x.strip()],
                        "direct_to_sm": [x.strip().upper() for x in direct_to_sm.split(",") if x.strip()],
                        "direct_to_mp": [x.strip().upper() for x in direct_to_mp.split(",") if x.strip()],
                        "ladders": {}
                    }
                    for item in ladders_text.split(";"):
                        if ":" in item:
                            k, v = item.split(":")
                            new_cfg["ladders"][k.strip().upper()] = [x.strip().upper() for x in v.split(",") if x.strip()]
                    if "mp_distribution" in config:
                        new_cfg["mp_distribution"] = config["mp_distribution"]
                    save_config(new_cfg)
                    st.success("✅ Rules saved successfully")
                except Exception as e:
                    st.error(f"❌ Error saving rules: {e}")

    if reset:
        flush_session()
        st.warning("Session data cleared. Round reset to 1.")

    if run:
        if uploaded_file is None:
            st.error("Please upload an input Excel file first.")
        else:
            uploaded_file.seek(0)
            excel_buffer = io.BytesIO(uploaded_file.read())
            out_file = f"converted_round{current_round}.xlsx"
            forward_map = session.get("forward_map", {})
            orig_map = session.get("orig_map", {})

            try:
                converted_summary, converted_detailed, new_forward_map, new_orig_map = process_excel(
                    excel_buffer, out_file, config, current_round,
                    forward_map=forward_map, orig_map=orig_map
                )

                # Ensure all strings are upper case
                for col in ["Category","OriginalCategory","ConvertedFrom","ConversionReason"]:
                    if col in converted_summary.columns:
                        converted_summary[col] = converted_summary[col].astype(str).str.upper()

                # Update session
                session["forward_map"] = new_forward_map
                session["orig_map"] = new_orig_map
                session["last_round"] = current_round
                session["last_input_file"] = uploaded_file.name
                session["last_output_file"] = out_file
                save_session(session)

                st.success(f"✅ Round {current_round} conversion complete")
                st.download_button(
                    "⬇️ Download Converted Excel",
                    data=open(out_file, "rb").read(),
                    file_name=os.path.basename(out_file),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.dataframe(converted_summary.head())

            except Exception as e:
                st.error(f"❌ Error: {e}")

    # ---------------------------
# Previous Rounds Selector with Download
# ---------------------------
    st.markdown("### ⏮️ View & Download Previous Rounds")
    converted_files = sorted([f for f in os.listdir() if f.startswith("converted_round") and f.endswith(".xlsx")])
    
    if converted_files:
        selected_file = st.selectbox("Select a round to preview/download", [""] + converted_files)
        if selected_file:
            try:
                xls = pd.ExcelFile(selected_file, engine="openpyxl")
                # Try to load Summary sheet first
                summary_sheets = [s for s in xls.sheet_names if "Summary" in s or "ConvertedRound" in s]
                sheet_to_load = summary_sheets[-1] if summary_sheets else xls.sheet_names[0]
                df_prev = pd.read_excel(xls, sheet_name=sheet_to_load)
                
                st.markdown(f"**Preview of {selected_file} ({sheet_to_load})**")
                st.dataframe(df_prev.head())
    
                # Download button for the selected round
                with open(selected_file, "rb") as f:
                    excel_bytes = f.read()
                st.download_button(
                    label=f"⬇️ Download {selected_file}",
                    data=excel_bytes,
                    file_name=os.path.basename(selected_file),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"❌ Could not load file: {e}")
    else:
        st.info("No previous converted rounds found.")

        # ---------------------------
# Previous Rounds Selector
# ---------------------------



if __name__ == "__main__":
    seat_conversion_ui()
