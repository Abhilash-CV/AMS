# seat_conversion_logic.py
import os
import json
import math
import pandas as pd

CONFIG_FILE = "config.json"

# ---------------------------
# Configuration
# ---------------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
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
# Session Initialization
# ---------------------------
def init_session():
    import streamlit as st
    if "forward_map" not in st.session_state:
        st.session_state.forward_map = {}
    if "orig_map" not in st.session_state:
        st.session_state.orig_map = {}
    if "last_round" not in st.session_state:
        st.session_state.last_round = 0

# ---------------------------
# Helper Functions
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

# ---------------------------
# Seat Conversion Core Logic
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
    forward_map = forward_map or {}
    orig_map = orig_map or {}

    rows = []
    for _, r in df.iterrows():
        stream = r["Stream"]
        insttype = r["InstType"]
        course = r["Course"]
        college = r["College"]
        cat = r["Category"]
        seats = r["Seats"]

        # Store original category mapping
        key = f"{stream}{insttype}{course}{college}"
        if key not in orig_map:
            orig_map[key] = cat

        if cat in config["no_conversion"]:
            rows.append({"Stream": stream, "InstType": insttype, "Course": course,
                         "College": college, "Category": cat, "Seats": seats})
            continue

        if cat in config["direct_to_sm"]:
            rows.append({"Stream": stream, "InstType": insttype, "Course": course,
                         "College": college, "Category": "SM", "Seats": seats,
                         "ConvertedFrom": cat})
            continue

        # Swap categories
        swapped = False
        for pair in config["swap_pairs"]:
            if cat in pair:
                other = pair[0] if cat == pair[1] else pair[1]
                rows.append({"Stream": stream, "InstType": insttype, "Course": course,
                             "College": college, "Category": other, "Seats": seats,
                             "ConvertedFrom": cat})
                swapped = True
                break
        if swapped:
            continue

        # Ladder conversions
        if cat in config["ladders"]:
            ladder = config["ladders"][cat]
            for c in ladder:
                rows.append({"Stream": stream, "InstType": insttype, "Course": course,
                             "College": college, "Category": c, "Seats": seats,
                             "ConvertedFrom": cat})
            continue

        # Direct to MP
        if cat in config["direct_to_mp"]:
            mp_rows = distribute_to_mp(seats, cat, config)
            for m in mp_rows:
                rows.append({"Stream": stream, "InstType": insttype, "Course": course,
                             "College": college, "Category": m["Category"], "Seats": m["Seats"],
                             "ConvertedFrom": cat})
            continue

        # Fallback: keep as is
        rows.append({"Stream": stream, "InstType": insttype, "Course": course,
                     "College": college, "Category": cat, "Seats": seats})

    df_out = pd.DataFrame(rows)
    return df_out, forward_map, orig_map

def process_excel(file, config, round_num, forward_map=None, orig_map=None):
    df = pd.read_excel(file, engine="openpyxl")
    if df.shape[1] < 2:
        raise ValueError("Input Excel must have at least 2 columns")

    code_col = df.columns[0]
    seats_col = df.columns[1]
    df_codes = df[[code_col, seats_col]].copy()
    df_codes.columns = ["Code", "Seats"]
    parsed = df_codes["Code"].apply(parse_code).apply(pd.Series)
    df_full = pd.concat([parsed, df_codes["Seats"].astype(int)], axis=1)
    initial = df_full[["Stream", "InstType", "Course", "College", "Category", "Seats"]].copy()

    converted, forward_map, orig_map = convert_seats(initial, config, forward_map, orig_map)
    converted["Round"] = round_num
    return converted, forward_map, orig_map
