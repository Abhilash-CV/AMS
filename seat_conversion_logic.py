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
        orig_cats = list(group["Category"].unique())
        handled = set()
        converted_targets = set()

        group_prefix = f"{stream}-{inst}-{course}-{college}"

        for cat in orig_cats:
            k = f"{group_prefix}-{cat}"
            if k not in orig_map:
                orig_map[k] = cat

        # OE -> SM
        if seats_by_cat.get("OE", 0) > 0:
            oe_seats = seats_by_cat["OE"]
            source_key = f"{group_prefix}-OE"
            orig_cat_value = orig_map.get(source_key, "OE")
            results.append({
                "Stream": stream, "InstType": inst, "Course": course, "College": college,
                "OriginalCategory": orig_cat_value,
                "Category": "SM", "Seats": oe_seats,
                "ConvertedFrom": "OE", "ConversionFlag": "Y", "ConversionReason": "OE_to_SM"
            })
            targ_key = f"{group_prefix}-SM"
            if targ_key not in orig_map:
                orig_map[targ_key] = orig_cat_value
            handled.add("OE")
            seats_by_cat["OE"] = 0
            seats_by_cat["SM"] = seats_by_cat.get("SM", 0) + oe_seats

        # SD -> XS
        if seats_by_cat.get("SD", 0) > 0:
            sd_seats = seats_by_cat["SD"]
            source_key = f"{group_prefix}-SD"
            orig_cat_value = orig_map.get(source_key, "SD")
            results.append({
                "Stream": stream, "InstType": inst, "Course": course, "College": college,
                "OriginalCategory": orig_cat_value,
                "Category": "XS", "Seats": sd_seats,
                "ConvertedFrom": "SD", "ConversionFlag": "Y", "ConversionReason": "SD_to_XS"
            })
            targ_key = f"{group_prefix}-XS"
            if targ_key not in orig_map:
                orig_map[targ_key] = orig_cat_value
            handled.add("SD")
            seats_by_cat["SD"] = 0
            seats_by_cat["XS"] = seats_by_cat.get("XS", 0) + sd_seats

        # HR -> SD -> XS
        if seats_by_cat.get("HR", 0) > 0:
            hr_seats = seats_by_cat["HR"]
            source_key = f"{group_prefix}-HR"
            orig_cat_value = orig_map.get(source_key, "HR")
            results.append({
                "Stream": stream, "InstType": inst, "Course": course, "College": college,
                "OriginalCategory": orig_cat_value,
                "Category": "XS", "Seats": hr_seats,
                "ConvertedFrom": "HR", "ConversionFlag": "Y", "ConversionReason": "HR_to_SD_to_XS"
            })
            targ_key = f"{group_prefix}-XS"
            if targ_key not in orig_map:
                orig_map[targ_key] = orig_cat_value
            handled.add("HR")
            seats_by_cat["HR"] = 0
            seats_by_cat["XS"] = seats_by_cat.get("XS", 0) + hr_seats

        # Direct -> MP
        for cat in direct_to_mp:
            seats = seats_by_cat.get(cat, 0)
            if seats > 0:
                source_key = f"{group_prefix}-{cat}"
                src_orig = orig_map.get(source_key, cat)
                for r in distribute_to_mp(seats, cat, config):
                    results.append({
                        "Stream": stream, "InstType": inst, "Course": course, "College": college,
                        "OriginalCategory": src_orig,
                        "Category": r["Category"], "Seats": r["Seats"],
                        "ConvertedFrom": cat, "ConversionFlag": "Y", "ConversionReason": "DirectToMP"
                    })
                    targ_key = f"{group_prefix}-{r['Category']}"
                    if targ_key not in orig_map:
                        orig_map[targ_key] = src_orig
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
                    source_key = f"{group_prefix}-{src_cat}"
                    src_orig = orig_map.get(source_key, src_cat)
                    results.append({
                        "Stream": stream, "InstType": inst, "Course": course, "College": college,
                        "OriginalCategory": src_orig,
                        "Category": chosen, "Seats": src_seats,
                        "ConvertedFrom": src_cat, "ConversionFlag": "Y",
                        "ConversionReason": f"{src_cat}_to_{chosen}"
                    })
                    targ_key = f"{group_prefix}-{chosen}"
                    if targ_key not in orig_map:
                        orig_map[targ_key] = src_orig
                    seats_by_cat[chosen] = seats_by_cat.get(chosen, 0) + src_seats
                    seats_by_cat[src_cat] = 0
                    handled.add(src_cat)
                    converted_targets.add(chosen)

        # Direct -> SM
        for cat in direct_to_sm:
            if cat in handled:
                continue
            seats = seats_by_cat.get(cat, 0)
            if seats > 0:
                source_key = f"{group_prefix}-{cat}"
                src_orig = orig_map.get(source_key, cat)
                results.append({
                    "Stream": stream, "InstType": inst, "Course": course, "College": college,
                    "OriginalCategory": src_orig,
                    "Category": "SM", "Seats": seats,
                    "ConvertedFrom": cat, "ConversionFlag": "Y", "ConversionReason": "DirectToSM"
                })
                targ_key = f"{group_prefix}-SM"
                if targ_key not in orig_map:
                    orig_map[targ_key] = src_orig
                handled.add(cat)
                seats_by_cat[cat] = 0

        # Swap pairs
        for a, b in swap_pairs:
            a_seats = seats_by_cat.get(a, 0)
            b_seats = seats_by_cat.get(b, 0)
            if a_seats > 0 and b_seats > 0:
                source_key = f"{group_prefix}-{a}"
                src_orig = orig_map.get(source_key, a)
                results.append({
                    "Stream": stream, "InstType": inst, "Course": course, "College": college,
                    "OriginalCategory": src_orig,
                    "Category": b, "Seats": a_seats,
                    "ConvertedFrom": a, "ConversionFlag": "Y", "ConversionReason": f"{a}_to_{b}"
                })
                targ_key = f"{group_prefix}-{b}"
                if targ_key not in orig_map:
                    orig_map[targ_key] = src_orig
                handled.add(a)
                seats_by_cat[a] = 0

        # Remaining categories
        for cat in orig_cats:
            if cat in handled or cat in converted_targets:
                continue
            key = f"{group_prefix}-{cat}"
            orig_value = orig_map.get(key, cat)
            results.append({
                "Stream": stream, "InstType": inst, "Course": course, "College": college,
                "OriginalCategory": orig_value,
                "Category": cat,
                "Seats": seats_by_cat.get(cat, 0),
                "ConvertedFrom": "", "ConversionFlag": "N",
                "ConversionReason": "NoConversion" if cat in no_conversion else "NoRule_keep"
            })

    out_df = pd.DataFrame(results)
    columns_order = ["Stream", "InstType", "Course", "College",
                     "OriginalCategory", "Category", "Seats",
                     "ConvertedFrom", "ConversionFlag", "ConversionReason"]
    out_df = out_df[[c for c in columns_order if c in out_df.columns]]
    return out_df, forward_map, orig_map
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
