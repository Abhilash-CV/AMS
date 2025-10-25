# seat_conversion_ui.py
import os
import json
import math
import pandas as pd
import streamlit as st
import tempfile



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
    return {
        "no_conversion": ["MG", "EW"],
        "direct_to_sm": ["EZ", "MU", "BX", "LA", "BH", "DV", "VK", "KN", "KU"],
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
# Conversion logic
# ---------------------------
def distribute_to_mp(seats, source_cat, config):
    DEFAULT_MP = {
        "SM": 0.50, "EWS": 0.10,
        "EZ": 0.09, "MU": 0.08, "BH": 0.03, "LA": 0.03,
        "DV": 0.02, "VK": 0.02, "KN": 0.01, "BX": 0.01, "KU": 0.01,
        "SC": 0.08, "ST": 0.02
    }
    mp_rules = config.get("mp_distribution") or DEFAULT_MP
    total = sum(mp_rules.values()) if isinstance(mp_rules, dict) else 0
    mp_frac = {k: v / total for k, v in mp_rules.items()} if total > 0 else DEFAULT_MP

    floats = {cat: seats * frac for cat, frac in mp_frac.items()}
    floors = {cat: int(math.floor(v)) for cat, v in floats.items()}
    allocated = sum(floors.values())
    extra = seats - allocated
    remainders = [(cat, floats[cat] - floors[cat]) for cat in mp_frac.keys()]
    remainders.sort(key=lambda x: (-x[1], list(mp_frac.keys()).index(x[0])))

    for i in range(extra):
        cat = remainders[i % len(remainders)][0]
        floors[cat] += 1

    rows = []
    for cat, cnt in floors.items():
        if cnt > 0:
            rows.append({"Category": cat, "Seats": int(cnt), "ConvertedFrom": source_cat})
    return rows


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

        # 1) OE -> SM
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

        # 2) SD -> XS
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

        # 3) Direct -> MP
        for cat in direct_to_mp:
            seats = seats_by_cat.get(cat, 0)
            if seats > 0:
                for r in distribute_to_mp(seats, cat, config):
                    results.append({
                        "Stream": stream, "InstType": inst, "Course": course, "College": college,
                        "OriginalCategory": orig_map.get(f"{stream}-{inst}-{course}-{college}-{cat}", cat),
                        "Category": r["Category"], "Seats": r["Seats"],
                        "ConvertedFrom": cat, "ConversionFlag": "Y", "ConversionReason": "DirectToMP"
                    })
                handled.add(cat)
                seats_by_cat[cat] = 0

        # 4) Ladder conversions
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

        # 5) Direct -> SM after ladders
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

        # 6) Swap pairs
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

        # 7) Remaining categories
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

    # rename columns
    work_df = df.rename(columns={
        "CounselGroup": "Stream",
        "CollegeType": "InstType",
        "CollegeCode": "College",
        "CourseCode": "Course",
        "Category": "Category",
        "Seat": "Seats"
    })

    work_df["Seats"] = pd.to_numeric(work_df["Seats"], errors="coerce").fillna(0).astype(int)
    work_df["Category"] = work_df["Category"].astype(str).str.strip().upper()

    converted, forward_map, orig_map = convert_seats(
        work_df[["Stream", "InstType", "Course", "College", "Category", "Seats"]],
        config,
        forward_map=forward_map,
        orig_map=orig_map
    )
    converted["Round"] = round_num

    # Summary 7-column
    summary_cols = [
        "Stream", "InstType", "Course", "College",
        "OriginalCategory", "Category", "Seats"
    ]
    converted_summary = converted.rename(columns={
        "Stream": "CounselGroup",
        "InstType": "CollegeType",
        "College": "CollegeCode",
        "Course": "CourseCode",
        "Seats": "Seat"
    })
    for col in summary_cols:
        if col not in converted_summary.columns:
            converted_summary[col] = ""
    converted_summary = converted_summary[summary_cols]

    # Save Excel
    from openpyxl import Workbook
    if not os.path.exists(output_file):
        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="InputData", index=False)
            converted_summary.to_excel(writer, sheet_name=f"ConvertedRound{round_num}", index=False)
    else:
        with pd.ExcelWriter(output_file, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            converted_summary.to_excel(writer, sheet_name=f"ConvertedRound{round_num}", index=False)

    return converted_summary, converted, forward_map, orig_map


# ---------------------------
# Streamlit UI
# ---------------------------
import os
import pandas as pd
import streamlit as st
import tempfile

from seat_conversion_ui import convert_seats, process_excel, load_config, load_session, save_session, flush_session, save_config

def seat_conversion_ui():
    st.title("🎯 Seat Conversion Tool")
    st.caption("Apply conversion rules round by round")

    # Load config and session
    config = load_config()
    session = load_session()
    current_round = session.get("last_round", 0) + 1
    st.info(f"**Current Round:** {current_round}")

    # Upload Excel
    uploaded_file = st.file_uploader("📂 Upload Input Excel", type=["xlsx", "xls"])
    if uploaded_file:
        try:
            df_preview = pd.read_excel(uploaded_file, engine="openpyxl")
        except Exception:
            # fallback for old .xls files
            df_preview = pd.read_excel(uploaded_file, engine="xlrd")
        st.dataframe(df_preview.head())

    # Buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        run = st.button("▶️ Run Conversion")
    with col2:
        edit = st.button("🧩 Edit Rules")
    with col3:
        reset = st.button("♻️ Flush Session")

    # Edit rules
    if edit:
        with st.expander("Edit Conversion Rules", expanded=True):
            st.markdown("**Modify rule lists below:**")
            no_conversion = st.text_input("No Conversion", ",".join(config.get("no_conversion", [])))
            direct_to_sm = st.text_input("Direct → SM", ",".join(config.get("direct_to_sm", [])))
            direct_to_mp = st.text_input("Direct → MP", ",".join(config.get("direct_to_mp", [])))
            ladders_raw = "; ".join([f"{k}:{','.join(v)}" for k, v in config.get("ladders", {}).items()])
            ladders_text = st.text_area("Ladders (SC:ST,OE,SM; ST:SC,OE,SM)", ladders_raw)

            if st.button("💾 Save Rules"):
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

    # Flush session
    if reset:
        flush_session()
        st.warning("Session data cleared. Round reset to 1.")

    # Run conversion
    if run:
        if uploaded_file is None:
            st.error("Please upload an input Excel file first.")
        else:
            try:
                # --- Save uploaded file to a Windows-safe temporary file ---
                file_ext = uploaded_file.name.split(".")[-1].lower()
                if file_ext not in ["xls", "xlsx"]:
                    st.error("Invalid file type. Please upload .xls or .xlsx file.")
                    return

                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    tmp.write(uploaded_file.read())
                    temp_input_path = tmp.name

                # Output file path
                out_file = f"converted_round{current_round}.xlsx"
                forward_map = session.get("forward_map", {})
                orig_map = session.get("orig_map", {})

                # --- Run conversion ---
                converted_summary, converted_detailed, new_forward_map, new_orig_map = process_excel(
                    temp_input_path, out_file, config, current_round,
                    forward_map=forward_map, orig_map=orig_map
                )

                # Clean up temp input
                os.remove(temp_input_path)

                # Update session
                session["forward_map"] = new_forward_map
                session["orig_map"] = new_orig_map
                session["last_round"] = current_round
                session["last_input_file"] = uploaded_file.name
                session["last_output_file"] = out_file
                save_session(session)

                st.success(f"✅ Round {current_round} conversion complete")

                # Download button
                with open(out_file, "rb") as f:
                    excel_bytes = f.read()
                st.download_button(
                    label="⬇️ Download Converted Excel",
                    data=excel_bytes,
                    file_name=os.path.basename(out_file),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                # Preview summary
                st.dataframe(converted_summary.head())

            except Exception as e:
                st.error(f"❌ Error: {e}")


