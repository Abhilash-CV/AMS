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
import math

def distribute_to_mp(total_seats, config, carry_forward=None):
    if carry_forward is None:
        carry_forward = {}

    DEFAULT_MP = {
        "SM": 0.50, "EWS": 0.10, "EZ": 0.09, "MU": 0.08,
        "BH": 0.03, "LA": 0.03, "DV": 0.02, "VK": 0.02,
        "KN": 0.01, "BX": 0.01, "KU": 0.01, "SC": 0.08, "ST": 0.02
    }

    mp_rules = config.get("mp_distribution") if config else DEFAULT_MP
    if not mp_rules:
        mp_rules = DEFAULT_MP

    # normalize
    total_frac = sum(mp_rules.values())
    mp_frac = {k: (v / total_frac) for k, v in mp_rules.items()}

    # expected seats (float)
    effective = {cat: mp_frac[cat] * total_seats + float(carry_forward.get(cat, 0.0))
                 for cat in mp_frac.keys()}

    # floor allocation
    alloc = {cat: int(math.floor(effective[cat])) for cat in effective.keys()}

    # compute remainders
    remainders = sorted(
        [(cat, effective[cat] - alloc[cat]) for cat in effective.keys()],
        key=lambda x: (-x[1], x[0])
    )

    # assign remaining seats by largest remainder
    assigned = sum(alloc.values())
    remaining = total_seats - assigned
    for i in range(remaining):
        alloc[remainders[i % len(remainders)][0]] += 1

    # protect categories with expected >= 0.5 (ensure at least 1 seat)
    protected = set()
    for cat, val in effective.items():
        if val >= 0.5 and alloc.get(cat, 0) == 0 and sum(alloc.values()) < total_seats:
            alloc[cat] = 1
            protected.add(cat)


    # if totals overshoot because of protection, remove from non-protected smallest remainders
    while sum(alloc.values()) > total_seats:
        removed = False
        for cat, _ in reversed(remainders):
            if cat in protected:
                continue
            if alloc[cat] > 0:
                alloc[cat] -= 1
                removed = True
                break
        if not removed:
            # fallback: decrement any category >1
            for cat in reversed(sorted(alloc.keys())):
                if alloc[cat] > 1 and cat not in protected:
                    alloc[cat] -= 1
                    removed = True
                    break
            if not removed:
                break

    # final safeguard: if under-assigned, add to largest remainder (including protected)
    while sum(alloc.values()) < total_seats:
        for cat, _ in remainders:
            alloc[cat] += 1
            if sum(alloc.values()) >= total_seats:
                break

    next_carry = {cat: effective[cat] - alloc[cat] for cat in effective.keys()}
    rows = [{"Category": cat, "Seats": int(cnt), "ConvertedFrom": "MP_POOL"} for cat, cnt in alloc.items() if cnt > 0]

    # DEBUG (optional): print allocation when testing
    # print("[distribute_to_mp] total:", total_seats, "alloc:", alloc)

    return rows, next_carry




def _allocate_among_colleges(total_seats, college_shares):
    """
    Hamilton method allocation among colleges.
    college_shares: dict college -> non-negative number (proportional share)
    returns dict college -> int seats summing to total_seats
    """
    if total_seats <= 0:
        return {c: 0 for c in college_shares}
    total_share = sum(college_shares.values())
    if total_share <= 0:
        # equal split
        base = total_seats // len(college_shares)
        alloc = {c: base for c in college_shares}
        rem = total_seats - base * len(college_shares)
        cols = sorted(college_shares.keys())
        for i in range(rem):
            alloc[cols[i % len(cols)]] += 1
        return alloc

    effective = {c: (college_shares[c] / total_share) * total_seats for c in college_shares}
    floor_alloc = {c: int(math.floor(effective[c])) for c in college_shares}
    assigned = sum(floor_alloc.values())
    remaining = total_seats - assigned
    remainders = sorted([(c, effective[c] - floor_alloc[c]) for c in college_shares], key=lambda x: (-x[1], x[0]))
    for i in range(remaining):
        floor_alloc[remainders[i % len(remainders)][0]] += 1
    return floor_alloc


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

    # --- Group by Stream + CollegeType + Course (all colleges pooled) ---
    group_keys = ["Stream", "InstType", "Course"]
    grouped = df.groupby(group_keys, sort=False)

    for group_vals, group in grouped:
        stream, inst, course = group_vals
        seats_by_cat = group.groupby("Category")["Seats"].sum().to_dict()
        handled = set()
        converted_targets = set()

        # Preserve original categories
        for _, row in group.iterrows():
            key = f"{stream}-{inst}-{course}-{row['College']}-{row['Category']}"
            if key not in orig_map:
                orig_map[key] = row['Category']

        # --- Step 1: OE -> SM per college ---
        for _, row in group.iterrows():
            if row["Category"] == "OE" and row["Seats"] > 0:
                results.append({
                    "Stream": stream, "InstType": inst, "Course": course, "College": row["College"],
                    "OriginalCategory": orig_map.get(f"{stream}-{inst}-{course}-{row['College']}-OE", "OE"),
                    "Category": "SM", "Seats": row['Seats'],
                    "ConvertedFrom": "OE", "ConversionFlag": "Y", "ConversionReason": "OE_to_SM"
                })
                seats_by_cat["OE"] = seats_by_cat.get("OE", 0) - row['Seats']
                handled.add("OE")

        # --- Step 2: SD -> XS per college ---
        for _, row in group.iterrows():
            if row["Category"] == "SD" and row["Seats"] > 0:
                results.append({
                    "Stream": stream, "InstType": inst, "Course": course, "College": row["College"],
                    "OriginalCategory": orig_map.get(f"{stream}-{inst}-{course}-{row['College']}-SD", "SD"),
                    "Category": "XS", "Seats": row['Seats'],
                    "ConvertedFrom": "SD", "ConversionFlag": "Y", "ConversionReason": "SD_to_XS"
                })
                seats_by_cat["SD"] = seats_by_cat.get("SD", 0) - row['Seats']
                handled.add("SD")

        # --- Step 3: Direct -> MP using pooled Hamilton method ---
        mp_source_cats = [c for c in direct_to_mp if seats_by_cat.get(c, 0) > 0]
        if mp_source_cats:
            total_mp = sum(seats_by_cat[c] for c in mp_source_cats)
            rows, _ = distribute_to_mp(total_mp, config)

            # Build per-college source counts (sum of all mp_source_cats in that college)
            college_source_counts = {}
            for college, sub in group.groupby('College'):
                college_source_counts[college] = int(sub.loc[sub['Category'].isin(mp_source_cats), 'Seats'].sum())

            total_source_seats = sum(college_source_counts.values())
            if total_source_seats == 0:
                # nothing to distribute
                for _, row in group.iterrows():
                    if row['Category'] in mp_source_cats:
                        # keep as is (or mark no conversion)
                        results.append({
                            "Stream": stream, "InstType": inst, "Course": course, "College": row["College"],
                            "OriginalCategory": orig_map.get(f"{stream}-{inst}-{course}-{row['College']}-{row['Category']}", row['Category']),
                            "Category": row['Category'], "Seats": row['Seats'],
                            "ConvertedFrom": "", "ConversionFlag": "N",
                            "ConversionReason": "NoMPSourceSeats"
                        })
                for c in mp_source_cats:
                    handled.add(c)
            else:
                # For each target MP category (row in rows), allocate its seats among colleges by Hamilton using college_source_counts
                for r in rows:
                    target_cat = r['Category']
                    target_total = r['Seats']
                    alloc_by_college = _allocate_among_colleges(target_total, college_source_counts)
                    for college, allocated in alloc_by_college.items():
                        if allocated <= 0:
                            continue
                        results.append({
                        "Stream": stream, "InstType": inst, "Course": course, "College": college,
                        "OriginalCategory": ",".join(sorted(mp_source_cats)),  # show actual categories merged cleanly
                        "Category": target_cat, "Seats": allocated,
                        "ConvertedFrom": ",".join(sorted(mp_source_cats)),
                        "ConversionFlag": "Y", "ConversionReason": "DirectToMP"
                    })

                for c in mp_source_cats:
                    handled.add(c)

        # --- Step 4: Direct -> SM ---
        for _, row in group.iterrows():
            if row["Category"] in direct_to_sm and row["Category"] not in handled:
                results.append({
                    "Stream": stream, "InstType": inst, "Course": course, "College": row["College"],
                    "OriginalCategory": orig_map.get(f"{stream}-{inst}-{course}-{row['College']}-{row['Category']}", row["Category"]),
                    "Category": "SM", "Seats": row['Seats'],
                    "ConvertedFrom": row["Category"], "ConversionFlag": "Y", "ConversionReason": "DirectToSM"
                })
                handled.add(row["Category"])

        # --- Step 5: Ladder conversions ---
        for _, row in group.iterrows():
            cat = row["Category"]
            if cat in handled:
                continue
            seats = row["Seats"]
            if seats <= 0:
                continue
            if cat in ladders:
                chosen = ladders[cat][0]  # take first available ladder target
                results.append({
                    "Stream": stream, "InstType": inst, "Course": course, "College": row["College"],
                    "OriginalCategory": orig_map.get(f"{stream}-{inst}-{course}-{row['College']}-{cat}", cat),
                    "Category": chosen, "Seats": seats,
                    "ConvertedFrom": cat, "ConversionFlag":"Y", "ConversionReason": f"{cat}_to_{chosen}"
                })
                converted_targets.add(chosen)
            else:
                results.append({
                    "Stream": stream, "InstType": inst, "Course": course, "College": row["College"],
                    "OriginalCategory": orig_map.get(f"{stream}-{inst}-{course}-{row['College']}-{cat}", cat),
                    "Category": cat, "Seats": seats,
                    "ConvertedFrom": "", "ConversionFlag":"N",
                    "ConversionReason":"NoRule_keep" if cat not in no_conversion else "NoConversion"
                })

        # --- Step 6: Swap pairs ---
        for a, b in swap_pairs:
            a_seats = seats_by_cat.get(a, 0)
            b_seats = seats_by_cat.get(b, 0)
            if a_seats > 0 and b_seats > 0:
                for _, row in group.iterrows():
                    if row["Category"] == a:
                        results.append({
                            "Stream": stream, "InstType": inst, "Course": course, "College": row["College"],
                            "OriginalCategory": orig_map.get(f"{stream}-{inst}-{course}-{row['College']}-{a}", a),
                            "Category": b, "Seats": row['Seats'],
                            "ConvertedFrom": a, "ConversionFlag": "Y", "ConversionReason": f"{a}_to_{b}"
                        })
                handled.add(a)

    out_df = pd.DataFrame(results)
    columns_order = ["Stream","InstType","Course","College","OriginalCategory","Category","Seats","ConvertedFrom","ConversionFlag","ConversionReason"]
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
    mode = 'a' if output_file.exists() else 'w'

    if mode == 'a':
        with pd.ExcelWriter(output_file, engine="openpyxl", mode='a', if_sheet_exists='replace') as writer:
            df.to_excel(writer, sheet_name="InputData", index=False)
            converted.to_excel(writer, sheet_name=f"ConvertedRound{round_num}", index=False)
            converted_summary.to_excel(writer, sheet_name=f"SummaryRound{round_num}", index=False)
    else:
        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
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
                summary_sheets = [s for s in xls.sheet_names if "Summary" in s or "ConvertedRound" in s]
                sheet_to_load = summary_sheets[-1] if summary_sheets else xls.sheet_names[0]
                df_prev = pd.read_excel(xls, sheet_name=sheet_to_load)
                
                st.markdown(f"**Preview of {selected_file} ({sheet_to_load})**")
                st.dataframe(df_prev.head())
    
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

if __name__ == "__main__":
    seat_conversion_ui()
