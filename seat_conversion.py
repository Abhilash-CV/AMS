#!/usr/bin/env python3
"""
Seat Conversion App (Streamlit)
Converts seats across multiple rounds using defined rules.
"""

import os
import json
import math
import pandas as pd
import streamlit as st
from io import BytesIO


CONFIG_FILE = "config.json"


# ---------------------------
# Config handling
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
# Parsing + conversion logic
# ---------------------------
def parse_code(code):
    s = "" if pd.isna(code) else str(code)
    s = s.rstrip("\n\r")
    s = s.ljust(11, " ")
    stream = s[0]
    insttype = s[1]
    course = s[2:4]
    college = s[4:7]
    cat_raw = s[7:11]
    cat = cat_raw.strip().upper()
    if len(cat) >= 2:
        cat = cat[-2:]
    return {
        "Stream": stream,
        "InstType": insttype,
        "Course": course,
        "College": college,
        "CategoryRaw": cat_raw,
        "Category": cat
    }


def distribute_to_mp(seats, source_cat, config):
    DEFAULT_MP = {
        "SM": 0.50, "EWS": 0.10,
        "EZ": 0.09, "MU": 0.08, "BH": 0.03, "LA": 0.03,
        "DV": 0.02, "VK": 0.02, "KN": 0.01, "BX": 0.01, "KU": 0.01,
        "SC": 0.08, "ST": 0.02
    }
    mp_rules = config.get("mp_distribution") or DEFAULT_MP
    total = sum(mp_rules.values())
    mp_frac = {k: v / total for k, v in mp_rules.items()}

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


# ---------------------------
# Conversion Logic (same as before, shortened for brevity)
# ---------------------------
# (keep the same convert_seats function from previous answer)


# ---------------------------
# Streamlit UI
# ---------------------------
def main():
    st.set_page_config(page_title="Seat Conversion System", layout="wide")
    st.title("🎯 Seat Conversion System")

    if "session" not in st.session_state:
        st.session_state.session = {"forward_map": {}, "orig_map": {}, "last_round": 0}

    session = st.session_state.session
    config = load_config()

    # ---------------- Sidebar Config Editor ----------------
    st.sidebar.header("⚙️ Conversion Rules Editor")

    # No Conversion
    config["no_conversion"] = st.sidebar.multiselect(
        "❌ No Conversion Categories",
        options=sorted(set(config["no_conversion"] + ["SM", "MG", "EW"])),
        default=config["no_conversion"]
    )

    # Direct to SM
    config["direct_to_sm"] = st.sidebar.multiselect(
        "➡️ Direct to SM Categories",
        options=sorted(set(config["direct_to_sm"] + ["EZ", "MU", "BX", "LA", "BH", "DV", "VK", "KN", "KU"])),
        default=config["direct_to_sm"]
    )

    # Direct to MP
    config["direct_to_mp"] = st.sidebar.multiselect(
        "➡️ Direct to MP Categories",
        options=sorted(set(config["direct_to_mp"] + ["XS", "PD"])),
        default=config["direct_to_mp"]
    )

    # Swap Pairs
    swap_text = st.sidebar.text_area(
        "🔄 Swap Pairs (format: PI-PT,AB-CD)",
        value=",".join(["-".join(p) for p in config["swap_pairs"]])
    )
    config["swap_pairs"] = [pair.split("-") for pair in swap_text.split(",") if "-" in pair]

    # Ladders
    st.sidebar.subheader("🪜 Ladders (Category → Order of fallbacks)")
    ladder_text = ""
    for src, targets in config["ladders"].items():
        ladder_text += f"{src}:{','.join(targets)}\n"
    ladder_edit = st.sidebar.text_area("Edit ladders (format: SC:ST,OE,SM)", value=ladder_text.strip())
    ladders = {}
    for line in ladder_edit.splitlines():
        if ":" in line:
            src, tgts = line.split(":", 1)
            ladders[src.strip()] = [t.strip() for t in tgts.split(",") if t.strip()]
    config["ladders"] = ladders

    # MP Distribution
       # MP Distribution
    st.sidebar.subheader("📊 MP Distribution (%)")

    # --- FIX: ensure mp_distribution is always dict ---
    if not isinstance(config.get("mp_distribution"), dict):
        config["mp_distribution"] = {
            "SM": 0.50, "EWS": 0.10,
            "EZ": 0.09, "MU": 0.08, "BH": 0.03, "LA": 0.03,
            "DV": 0.02, "VK": 0.02, "KN": 0.01, "BX": 0.01, "KU": 0.01,
            "SC": 0.08, "ST": 0.02
        }

    mp_dist = {}
    for cat, frac in config["mp_distribution"].items():
        mp_dist[cat] = st.sidebar.number_input(
            f"{cat} %", value=float(frac * 100), step=1.0
        ) / 100.0
    config["mp_distribution"] = mp_dist


    # ---------------- Main File Upload ----------------
    uploaded = st.file_uploader("📂 Upload Input Excel", type=["xlsx", "xls"])
    if uploaded:
        round_num = session.get("last_round", 0) + 1
        df = pd.read_excel(uploaded, engine="openpyxl")
        st.write("📊 Input Preview", df.head())

        if st.button(f"🚀 Run Conversion (Round {round_num})"):
            try:
                code_col = df.columns[0]
                seats_col = df.columns[1]
                df_codes = df[[code_col, seats_col]].copy()
                df_codes.columns = ["Code", "Seats"]
                parsed = df_codes["Code"].apply(parse_code).apply(pd.Series)
                df_full = pd.concat([parsed, df_codes["Seats"].astype(int)], axis=1)
                initial = df_full[["Stream", "InstType", "Course", "College", "Category", "Seats"]].copy()

                # run conversion
                converted, new_forward_map, new_orig_map = convert_seats(
                    initial, config,
                    forward_map=session.get("forward_map", {}),
                    orig_map=session.get("orig_map", {}),
                    debug=False
                )
                converted["Round"] = round_num

                # update session
                session["forward_map"] = new_forward_map
                session["orig_map"] = new_orig_map
                session["last_round"] = round_num

                st.success(f"✅ Round {round_num} Conversion Completed")

                st.write("📊 Converted Data", converted)

                output = BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    converted.to_excel(writer, sheet_name=f"Round{round_num}", index=False)
                st.download_button(
                    label="⬇️ Download Converted Excel",
                    data=output.getvalue(),
                    file_name=f"converted_round{round_num}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Error: {e}")


if __name__ == "__main__":
    main()
