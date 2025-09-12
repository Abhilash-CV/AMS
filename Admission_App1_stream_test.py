import re
import sqlite3
import pandas as pd
import streamlit as st

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
    if df is None or df.empty:
        return pd.DataFrame()
    cols, seen = [], {}
    for c in df.columns:
        s = str(c).strip()
        s = re.sub(r"[^\w]", "_", s)
        if not s:
            s = "Unnamed"
        if s in seen:
            seen[s] += 1
            s = f"{s}_{seen[s]}"
        else:
            seen[s] = 0
        cols.append(s)
    df = df.copy()
    df.columns = cols
    return df

def ensure_columns_exist(table: str):
    """Guarantee AdmissionYear & Program exist in table schema."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(f'PRAGMA table_info("{table}")')
        cols = [r[1] for r in cur.fetchall()]
        if "AdmissionYear" not in cols:
            cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "AdmissionYear" TEXT')
        if "Program" not in cols:
            cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "Program" TEXT')
        conn.commit()
    except sqlite3.OperationalError:
        pass  # table may not exist yet

def ensure_table_exists(table: str, df: pd.DataFrame):
    if df.empty:
        return
    conn = get_conn()
    cur = conn.cursor()
    col_defs = []
    for col, dtype in zip(df.columns, df.dtypes):
        if "int" in str(dtype): t = "INTEGER"
        elif "float" in str(dtype): t = "REAL"
        else: t = "TEXT"
        col_defs.append(f'"{col}" {t}')
    cur.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)})')
    conn.commit()
    ensure_columns_exist(table)

def save_table(table: str, df: pd.DataFrame, replace_where: dict = None):
    df = clean_columns(df)
    conn = get_conn()
    cur = conn.cursor()

    # Ensure Year + Program are present
    if replace_where:
        for k, v in replace_where.items():
            if k not in df.columns:
                df[k] = v

    ensure_table_exists(table, df)

    if replace_where:
        where_clause = " AND ".join([f'"{k}"=?' for k in replace_where.keys()])
        cur.execute(f'DELETE FROM "{table}" WHERE {where_clause}', tuple(replace_where.values()))
    else:
        cur.execute(f'DELETE FROM "{table}"')  # full wipe if no filter

    if not df.empty:
        placeholders = ",".join(["?"] * len(df.columns))
        cur.executemany(
            f'INSERT INTO "{table}" ({",".join([f"{c}" for c in df.columns])}) VALUES ({placeholders})',
            df.values.tolist()
        )
    conn.commit()

def load_table(table: str, year=None, program=None):
    ensure_columns_exist(table)
    conn = get_conn()
    try:
        if year and program:
            query = f'SELECT * FROM "{table}" WHERE "AdmissionYear"=? AND "Program"=?'
            return pd.read_sql(query, conn, params=(year, program))
        return pd.read_sql(f'SELECT * FROM "{table}"', conn)
    except Exception:
        return pd.DataFrame()

# ---------------------------
# Sidebar State
# ---------------------------
if "year" not in st.session_state:
    st.session_state.year = YEAR_OPTIONS[-1]
if "program" not in st.session_state:
    st.session_state.program = PROGRAM_OPTIONS[0]

st.sidebar.header("Filters")
st.session_state.year = st.sidebar.selectbox("Admission Year", YEAR_OPTIONS, index=YEAR_OPTIONS.index(st.session_state.year))
st.session_state.program = st.sidebar.selectbox("Program", PROGRAM_OPTIONS, index=PROGRAM_OPTIONS.index(st.session_state.program))

year, program = st.session_state.year, st.session_state.program

st.title("Admission Management System")
st.caption(f"Currently viewing data for **{year}/{program}**")

tabs = st.tabs(["SeatMatrix", "StudentDetails"])

# ---------- SeatMatrix ----------
with tabs[0]:
    df = load_table("SeatMatrix", year, program)

    uploaded = st.file_uploader("Upload SeatMatrix", type=["xlsx", "csv"], key=f"seat_upload_{year}_{program}")
    if uploaded:
        try:
            df_new = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
            df_new = clean_columns(df_new)
            df_new["AdmissionYear"] = year
            df_new["Program"] = program
            save_table("SeatMatrix", df_new, replace_where={"AdmissionYear": year, "Program": program})
            df = load_table("SeatMatrix", year, program)  # 🔑 reload fresh
            st.success(f"✅ Uploaded and saved {len(df_new)} rows for {year}/{program}")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    st.dataframe(df, use_container_width=True)

    if st.button("🗑️ Flush SeatMatrix (Year+Program)"):
        save_table("SeatMatrix", pd.DataFrame(columns=df.columns), replace_where={"AdmissionYear": year, "Program": program})
        df = load_table("SeatMatrix", year, program)  # 🔑 reload fresh
        st.success(f"✅ Flushed SeatMatrix for {year}/{program}")

# ---------- StudentDetails ----------
with tabs[1]:
    df = load_table("StudentDetails", year, program)

    uploaded = st.file_uploader("Upload StudentDetails", type=["xlsx", "csv"], key=f"students_upload_{year}_{program}")
    if uploaded:
        try:
            df_new = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
            df_new = clean_columns(df_new)
            df_new["AdmissionYear"] = year
            df_new["Program"] = program
            save_table("StudentDetails", df_new, replace_where={"AdmissionYear": year, "Program": program})
            df = load_table("StudentDetails", year, program)  # 🔑 reload fresh
            st.success(f"✅ Uploaded and saved {len(df_new)} rows for {year}/{program}")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    st.dataframe(df, use_container_width=True)

    if st.button("🗑️ Flush StudentDetails (Year+Program)"):
        save_table("StudentDetails", pd.DataFrame(columns=df.columns), replace_where={"AdmissionYear": year, "Program": program})
        df = load_table("StudentDetails", year, program)  # 🔑 reload fresh
        st.success(f"✅ Flushed StudentDetails for {year}/{program}")
