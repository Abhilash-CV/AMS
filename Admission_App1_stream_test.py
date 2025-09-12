import re
import io
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime

DB_FILE = "admission.db"
PROGRAM_OPTIONS = ["LLB5", "LLB3", "PGN", "Engineering"]
YEAR_OPTIONS = ["2023", "2024", "2025", "2026"]

st.set_page_config(page_title="Admission Management System", layout="wide")

# ---------------------------
# DB Helpers
# ---------------------------
def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [re.sub(r"\s+", "_", c.strip()) for c in df.columns]
    return df

def save_table(table: str, df: pd.DataFrame, replace_where: dict = None):
    conn = get_conn()
    cur = conn.cursor()
    df = clean_columns(df) if df is not None else pd.DataFrame()

    if replace_where:
        # Ensure replace_where keys exist as columns
        for k, v in replace_where.items():
            if k not in df.columns:
                df[k] = v

        # --- Check existing schema ---
        cur.execute(f"PRAGMA table_info('{table}')")
        existing_cols = [row[1] for row in cur.fetchall()]
        if existing_cols:
            missing_cols = [k for k in replace_where.keys() if k not in existing_cols]
            if missing_cols:
                # Drop table if schema mismatch (auto-migrate)
                cur.execute(f'DROP TABLE IF EXISTS "{table}"')
                existing_cols = []

        # Recreate table if not exists
        if not existing_cols and not df.empty:
            col_defs = []
            for col, dtype in zip(df.columns, df.dtypes):
                if "int" in str(dtype): t = "INTEGER"
                elif "float" in str(dtype): t = "REAL"
                else: t = "TEXT"
                col_defs.append(f'"{col}" {t}')
            cur.execute(f'CREATE TABLE "{table}" ({", ".join(col_defs)})')

        # Delete rows matching year+program
        where_clause = " AND ".join([f'"{k}"=?' for k in replace_where.keys()])
        cur.execute(f'DELETE FROM "{table}" WHERE {where_clause}', tuple(replace_where.values()))

        if not df.empty:
            placeholders = ",".join(["?"] * len(df.columns))
            cur.executemany(
                f'INSERT INTO "{table}" ({",".join(df.columns)}) VALUES ({placeholders})',
                df.values.tolist()
            )
        conn.commit()
        return

    # Full replace (no replace_where)
    if df.empty:
        try:
            cur.execute(f'DELETE FROM "{table}"')
            conn.commit()
        except Exception:
            pass
        return

    cur.execute(f'DROP TABLE IF EXISTS "{table}"')
    col_defs = []
    for col, dtype in zip(df.columns, df.dtypes):
        if "int" in str(dtype): t = "INTEGER"
        elif "float" in str(dtype): t = "REAL"
        else: t = "TEXT"
        col_defs.append(f'"{col}" {t}')
    cur.execute(f'CREATE TABLE "{table}" ({", ".join(col_defs)})')
    placeholders = ",".join(["?"] * len(df.columns))
    cur.executemany(
        f'INSERT INTO "{table}" ({",".join(df.columns)}) VALUES ({placeholders})',
        df.values.tolist()
    )
    conn.commit()

def load_table(table: str, year=None, program=None):
    conn = get_conn()
    try:
        if year and program:
            query = f'SELECT * FROM "{table}" WHERE "AdmissionYear"=? AND "Program"=?'
            df = pd.read_sql_query(query, conn, params=(year, program))
        else:
            df = pd.read_sql_query(f'SELECT * FROM "{table}"', conn)
    except Exception:
        return pd.DataFrame()
    return clean_columns(df)

def filter_and_sort_dataframe(df, table):
    if df.empty:
        return df
    return df.sort_values(by=df.columns[0], ascending=True)

# ---------------------------
# UI - Sidebar
# ---------------------------
st.sidebar.header("Admission Config")
year = st.sidebar.selectbox("Select Admission Year", YEAR_OPTIONS, key="year")
program = st.sidebar.selectbox("Select Program", PROGRAM_OPTIONS, key="program")

# ---------------------------
# Tabs
# ---------------------------
tabs = st.tabs([
    "Overview", "SeatMatrix", "CandidateList", "Allotments", "StudentDetails"
])

# ---------- Overview ----------
with tabs[0]:
    st.write("Welcome to the Admission Management System.")
    st.write(f"Currently viewing **{year}/{program}** data.")

# ---------- SeatMatrix ----------
with tabs[1]:
    df_all = load_table("SeatMatrix", year, program)

    uploaded = st.file_uploader(
        "Upload SeatMatrix (Excel/CSV)",
        type=["xlsx", "csv"],
        key="upload_SeatMatrix"
    )
    if uploaded:
        try:
            if uploaded.name.lower().endswith(".csv"):
                df_new = pd.read_csv(uploaded)
            else:
                df_new = pd.read_excel(uploaded)

            df_new = clean_columns(df_new)
            df_new["AdmissionYear"] = year
            df_new["Program"] = program

            save_table("SeatMatrix", df_new, replace_where={"AdmissionYear": year, "Program": program})
            df_all = load_table("SeatMatrix", year, program)
            st.success(f"✅ Uploaded and saved {len(df_new)} rows for {year}/{program}")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    df_filtered = filter_and_sort_dataframe(df_all, "SeatMatrix")
    edited = st.data_editor(df_filtered, num_rows="dynamic", use_container_width=True, key="edit_seatmatrix")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save SeatMatrix", key="save_seatmatrix"):
            save_table("SeatMatrix", edited, replace_where={"AdmissionYear": year, "Program": program})
            df_all = load_table("SeatMatrix", year, program)
            st.success(f"✅ Saved edits for {year}/{program}")
    with col2:
        if st.button("🗑️ Flush SeatMatrix (Year+Program)", key="flush_seatmatrix"):
            save_table("SeatMatrix", pd.DataFrame(columns=df_all.columns),
                       replace_where={"AdmissionYear": year, "Program": program})
            df_all = load_table("SeatMatrix", year, program)
            st.success(f"✅ Flushed data for {year}/{program}")

# ---------- CandidateList ----------
with tabs[2]:
    st.info("CandidateList management coming soon.")

# ---------- Allotments ----------
with tabs[3]:
    st.info("Allotment management coming soon.")

# ---------- StudentDetails ----------
with tabs[4]:
    df_all = load_table("StudentDetails", year, program)

    uploaded = st.file_uploader(
        "Upload StudentDetails (Excel/CSV)",
        type=["xlsx", "csv"],
        key="upload_StudentDetails"
    )
    if uploaded:
        try:
            if uploaded.name.lower().endswith(".csv"):
                df_new = pd.read_csv(uploaded)
            else:
                df_new = pd.read_excel(uploaded)

            df_new = clean_columns(df_new)
            df_new["AdmissionYear"] = year
            df_new["Program"] = program

            save_table("StudentDetails", df_new, replace_where={"AdmissionYear": year, "Program": program})
            df_all = load_table("StudentDetails", year, program)
            st.success(f"✅ Uploaded and saved {len(df_new)} rows for {year}/{program}")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    df_filtered = filter_and_sort_dataframe(df_all, "StudentDetails")
    edited = st.data_editor(df_filtered, num_rows="dynamic", use_container_width=True, key="edit_students")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save StudentDetails", key="save_students"):
            save_table("StudentDetails", edited, replace_where={"AdmissionYear": year, "Program": program})
            df_all = load_table("StudentDetails", year, program)
            st.success(f"✅ Saved edits for {year}/{program}")
    with col2:
        if st.button("🗑️ Flush StudentDetails (Year+Program)", key="flush_students"):
            save_table("StudentDetails", pd.DataFrame(columns=df_all.columns),
                       replace_where={"AdmissionYear": year, "Program": program})
            df_all = load_table("StudentDetails", year, program)
            st.success(f"✅ Flushed data for {year}/{program}")
