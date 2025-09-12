# admission_app_stream_v2.py
import re
import io
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime

# -------------------------
# CONFIG
# -------------------------
DB_FILE = "admission.db"
PROGRAM_OPTIONS = ["LLB5", "LLB3", "PGN", "Engineering"]
YEAR_OPTIONS = ["2023", "2024", "2025", "2026"]

st.set_page_config(page_title="Admission Management System", layout="wide")

# -------------------------
# DB CONNECTION & HELPERS
# -------------------------
@st.cache_resource
def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

@st.cache_resource
def cached_table_columns(table: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f'PRAGMA table_info("{table}")')
    return [r[1] for r in cur.fetchall()]

# -------------------------
# UTILITIES
# -------------------------
def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    cols, seen = [], {}
    for c in df.columns:
        s = str(c).strip()
        s = re.sub(r"[^\w]", "_", s)
        if s == "":
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

def pandas_dtype_to_sql(dtype) -> str:
    s = str(dtype).lower()
    if "int" in s:
        return "INTEGER"
    if "float" in s or "double" in s:
        return "REAL"
    return "TEXT"

def table_exists(table: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None

def ensure_table_and_columns(table: str, df: pd.DataFrame):
    conn = get_conn()
    cur = conn.cursor()
    existing = cached_table_columns(table) if table_exists(table) else []
    if not existing and (df is None or df.empty):
        return
    if not existing and df is not None:
        # create table from df
        col_defs = [f'"{col}" {pandas_dtype_to_sql(dtype)}' for col, dtype in zip(df.columns, df.dtypes)]
        create_stmt = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)})'
        cur.execute(create_stmt)
        conn.commit()
        existing = cached_table_columns(table)
    # add missing columns
    for col in (df.columns if df is not None else []):
        if col not in existing:
            cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{col}" TEXT')
            conn.commit()
            existing.append(col)
    # ensure AdmissionYear and Program
    for special in ("AdmissionYear", "Program"):
        if special not in existing:
            try:
                cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{special}" TEXT')
                conn.commit()
                existing.append(special)
            except Exception:
                pass

# -------------------------
# LOAD / SAVE TABLE
# -------------------------
def load_table(table: str, year: str = None, program: str = None) -> pd.DataFrame:
    conn = get_conn()
    ensure_table_and_columns(table, pd.DataFrame())
    if not table_exists(table):
        return pd.DataFrame()
    try:
        if year and program:
            df = pd.read_sql_query(f'SELECT * FROM "{table}" WHERE "AdmissionYear"=? AND "Program"=?', conn, params=(year, program))
        else:
            df = pd.read_sql_query(f'SELECT * FROM "{table}"', conn)
        return clean_columns(df)
    except Exception:
        return pd.DataFrame()

def save_table(table: str, df: pd.DataFrame, replace_where: dict = None):
    conn = get_conn()
    cur = conn.cursor()
    df = clean_columns(df) if df is not None else pd.DataFrame()
    if replace_where:
        # enforce year/program in df
        for k, v in replace_where.items():
            if k not in df.columns:
                df[k] = v
        ensure_table_and_columns(table, df)
        where_clause = ' AND '.join([f'"{k}"=?' for k in replace_where.keys()])
        params = tuple(replace_where.values())
        cur.execute(f'DELETE FROM "{table}" WHERE {where_clause}', params)
        if not df.empty:
            cols = [f'"{c}"' for c in df.columns]
            placeholders = ','.join(['?']*len(df.columns))
            insert_stmt = f'INSERT INTO "{table}" ({','.join(cols)}) VALUES ({placeholders})'
            cur.executemany(insert_stmt, df.values.tolist())
        conn.commit()
        st.success(f"✅ Saved {len(df)} rows to {table} (scoped to {replace_where})")
        return
    # Full overwrite
    cur.execute(f'DROP TABLE IF EXISTS "{table}"')
    if df is None or df.empty:
        conn.commit()
        st.success(f"✅ Cleared all rows from {table}")
        return
    col_defs = [f'"{col}" {pandas_dtype_to_sql(dtype)}' for col, dtype in zip(df.columns, df.dtypes)]
    cur.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)})')
    cols = [f'"{c}"' for c in df.columns]
    placeholders = ','.join(['?']*len(df.columns))
    cur.executemany(f'INSERT INTO "{table}" ({','.join(cols)}) VALUES ({placeholders})', df.values.tolist())
    conn.commit()
    st.success(f"✅ Saved {len(df)} rows to {table}")

# -------------------------
# DOWNLOAD / UPLOAD HELPERS
# -------------------------
def download_button_for_df(df: pd.DataFrame, name: str):
    if df is None or df.empty:
        st.warning("⚠️ No data to download.")
        return
    col1, col2 = st.columns(2)
    col1.download_button(label=f"⬇ Download {name} (CSV)", data=df.to_csv(index=False).encode('utf-8'), file_name=f"{name}.csv", mime="text/csv")
    try:
        import xlsxwriter
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Sheet1")
        col2.download_button(label=f"⬇ Download {name} (Excel)", data=buf.getvalue(), file_name=f"{name}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception:
        col2.warning("⚠️ Excel download unavailable (install xlsxwriter)")

def handle_upload(table, year, program, key_suffix, scoped=True):
    uploaded = st.file_uploader(f"Upload {table}", type=["xlsx","xls","csv"], key=f"upl_{table}_{key_suffix}")
    if uploaded:
        try:
            df_new = pd.read_csv(uploaded) if uploaded.name.lower().endswith('.csv') else pd.read_excel(uploaded)
            df_new = clean_columns(df_new)
            if scoped:
                df_new["AdmissionYear"] = year
                df_new["Program"] = program
                save_table(table, df_new, replace_where={"AdmissionYear": year, "Program": program})
            else:
                save_table(table, df_new, replace_where=None)
        except Exception as e:
            st.error(f"Error reading file: {e}")
    return load_table(table, year, program) if scoped else load_table(table)

def flush_table(table: str):
    if st.checkbox(f"Yes, flush ALL data for {table}?", key=f"flush_{table}_chk"):
        save_table(table, pd.DataFrame(), replace_where=None)
        st.success(f"✅ {table} cleared!")
        st.experimental_rerun()

# -------------------------
# FILTER & SORT
# -------------------------
def filter_and_sort_dataframe(df: pd.DataFrame, table_name: str, year=None, program=None) -> pd.DataFrame:
    if df is None or df.empty:
        st.write(f"⚠️ No data available for {table_name}")
        return df
    with st.expander(f"🔎 Filter & Sort ({table_name})", expanded=False):
        search_text = st.text_input(f"🔍 Global Search ({table_name})", key=f"{table_name}_search_{year}_{program}").lower().strip()
        mask = pd.Series(True, index=df.index)
        if search_text:
            mask &= df.apply(lambda row: row.astype(str).str.lower().str.contains(search_text).any(), axis=1)
        for col in df.columns:
            unique_vals = sorted(df[col].dropna().unique())
            selected_vals = st.multiselect(f"Filter {col}", ["(All)"]+list(unique_vals), default=["(All)"], key=f"{table_name}_{col}_filter_{year}_{program}")
            if "(All)" not in selected_vals:
                mask &= df[col].isin(selected_vals)
        return df[mask]

# -------------------------
# SIDEBAR
# -------------------------
with st.sidebar:
    st.header("Filters")
    if "year" not in st.session_state:
        st.session_state.year = YEAR_OPTIONS[-1]
    if "program" not in st.session_state:
        st.session_state.program = PROGRAM_OPTIONS[0]
    st.session_state.year = st.selectbox("Admission Year", YEAR_OPTIONS, index=YEAR_OPTIONS.index(st.session_state.year))
    st.session_state.program = st.selectbox("Program", PROGRAM_OPTIONS, index=PROGRAM_OPTIONS.index(st.session_state.program))

year = st.session_state.year
program = st.session_state.program

# -------------------------
# MAIN UI
# -------------------------
st.title("Admission Management System")
st.caption(f"Year: **{year}**, Program: **{program}**")
tabs = st.tabs(["CourseMaster", "CollegeMaster", "CollegeCourseMaster", "SeatMatrix", "StudentDetails", "Allotment", "Vacancy"])

# ---------- CourseMaster ----------
with tabs[0]:
    st.subheader("📚 CourseMaster (Year+Program)")
    df_course = handle_upload("CourseMaster", year, program, f"CourseMaster_{year}_{program}")
    download_button_for_df(df_course, f"CourseMaster_{year}_{program}")
    st.write(f"Showing rows for AdmissionYear={year} & Program={program}")
    edited_course = st.data_editor(filter_and_sort_dataframe(df_course, "CourseMaster", year, program), num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save CourseMaster", key="save_course_btn"):
        if "AdmissionYear" not in edited_course.columns:
            edited_course["AdmissionYear"] = year
        if "Program" not in edited_course.columns:
            edited_course["Program"] = program
        save_table("CourseMaster", edited_course, replace_where={"AdmissionYear": year, "Program": program})

# ---------- CollegeMaster ----------
with tabs[1]:
    st.subheader("🏫 CollegeMaster (Global)")
    df_col = handle_upload("CollegeMaster", year, program, "CollegeMaster_global", scoped=False)
    download_button_for_df(df_col, "CollegeMaster")
    edited_col = st.data_editor(filter_and_sort_dataframe(df_col, "CollegeMaster"), num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save CollegeMaster", key="save_col_btn"):
        save_table("CollegeMaster", edited_col, replace_where=None)

# ---------- CollegeCourseMaster ----------
with tabs[2]:
    st.subheader("🏫📚 CollegeCourseMaster (Global)")
    df_cc = handle_upload("CollegeCourseMaster", year, program, "CollegeCourseMaster_global", scoped=False)
    download_button_for_df(df_cc, "CollegeCourseMaster")
    edited_cc = st.data_editor(filter_and_sort_dataframe(df_cc, "CollegeCourseMaster"), num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save CollegeCourseMaster", key="save_cc_btn"):
        save_table("CollegeCourseMaster", edited_cc, replace_where=None)
    with st.expander("🗑️ Danger Zone: CollegeCourseMaster"):
        flush_table("CollegeCourseMaster")

# ---------- SeatMatrix ----------
with tabs[3]:
    st.subheader("SeatMatrix (Year+Program)")
    df_seat = handle_upload("SeatMatrix", year, program, f"SeatMatrix_{year}_{program}")
    download_button_for_df(df_seat, f"SeatMatrix_{year}_{program}")
    edited_seat = st.data_editor(filter_and_sort_dataframe(df_seat, "SeatMatrix", year, program), num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save SeatMatrix", key="save_seat_btn"):
        if "AdmissionYear" not in edited_seat.columns:
            edited_seat["AdmissionYear"] = year
        if "Program" not in edited_seat.columns:
            edited_seat["Program"] = program
        save_table("SeatMatrix", edited_seat, replace_where={"AdmissionYear": year, "Program": program})

# ---------- StudentDetails ----------
with tabs[4]:
    st.subheader("👨‍🎓 StudentDetails (Year+Program)")
    df_stu = handle_upload("StudentDetails", year, program, f"StudentDetails_{year}_{program}")
    download_button_for_df(df_stu, f"StudentDetails_{year}_{program}")
    edited_stu = st.data_editor(filter_and_sort_dataframe(df_stu, "StudentDetails", year, program), num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save StudentDetails", key="save_stu_btn"):
        if "AdmissionYear" not in edited_stu.columns:
            edited_stu["AdmissionYear"] = year
        if "Program" not in edited_stu.columns:
            edited_stu["Program"] = program
        save_table("StudentDetails", edited_stu, replace_where={"AdmissionYear": year, "Program": program})
    with st.expander("🗑️ Danger Zone: StudentDetails"):
        flush_table("StudentDetails")

# ---------- Allotment ----------
with tabs[5]:
    st.subheader("Allotment (Global)")
    df_allot = load_table("Allotment")
    if df_allot.empty:
        st.info("No allotment data found yet.")
    else:
        download_button_for_df(df_allot, "Allotment")
        st.dataframe(df_allot, use_container_width=True)

# ---------- Vacancy ----------
with tabs[6]:
    st.subheader("Vacancy (skeleton)")
    st.info("Vacancy calculation will be added later. Upload/edit SeatMatrix and Allotment to prepare for vacancy calculation.")
