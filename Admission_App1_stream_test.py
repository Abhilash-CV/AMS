# admission_app_stream_final.py
import re
import io
import sqlite3
import pandas as pd
import streamlit as st

DB_FILE = "admission.db"
PROGRAM_OPTIONS = ["LLB5", "LLB3", "PGN", "Engineering"]
YEAR_OPTIONS = ["2023", "2024", "2025", "2026"]

st.set_page_config(page_title="Admission Management System", layout="wide")

# -------------------------
# DB Connection helper
# -------------------------
@st.cache_resource
def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None:
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

def load_table(table: str) -> pd.DataFrame:
    conn = get_conn()
    try:
        df = pd.read_sql(f'SELECT * FROM "{table}"', conn)
        return clean_columns(df)
    except Exception:
        return pd.DataFrame()

def save_table(table: str, df: pd.DataFrame, replace_where: dict = None):
    conn = get_conn()
    cur = conn.cursor()
    df = clean_columns(df) if df is not None else pd.DataFrame()

    if replace_where:
        if not df.empty:
            col_defs = []
            for col, dtype in zip(df.columns, df.dtypes):
                if "int" in str(dtype): t = "INTEGER"
                elif "float" in str(dtype): t = "REAL"
                else: t = "TEXT"
                col_defs.append(f'"{col}" {t}')
            cur.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)})')
        where_clause = " AND ".join([f'"{k}"=?' for k in replace_where.keys()])
        cur.execute(f'DELETE FROM "{table}" WHERE {where_clause}', tuple(replace_where.values()))
        if not df.empty:
            placeholders = ",".join(["?"] * len(df.columns))
            cur.executemany(
                f'INSERT INTO "{table}" ({",".join([f"{c}" for c in df.columns])}) VALUES ({placeholders})',
                df.values.tolist()
            )
        conn.commit()
        st.success(f"✅ Saved {len(df)} rows to {table}")
        return

    if df.empty:
        try:
            cur.execute(f'DELETE FROM "{table}"')
            conn.commit()
            st.success(f"✅ Cleared all rows from {table}")
        except Exception:
            st.info(f"No table {table} existed.")
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
        f'INSERT INTO "{table}" ({",".join([f"{c}" for c in df.columns])}) VALUES ({placeholders})',
        df.values.tolist()
    )
    conn.commit()
    st.success(f"✅ Saved {len(df)} rows to {table}")

def upload_and_preview(table_name: str, existing_df: pd.DataFrame, year_based: bool=False):
    uploaded = st.file_uploader(
        f"Upload {table_name} (Excel/CSV)",
        type=["xlsx", "csv"],
        key=f"upload_{table_name}"
    )
    df = existing_df.copy() if existing_df is not None else pd.DataFrame()
    if uploaded:
        try:
            if uploaded.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            st.success(f"📥 Loaded {len(df)} rows from {uploaded.name}")
        except Exception as e:
            st.error(f"Error reading file: {e}")
            return existing_df
    if year_based:
        if "AdmissionYear" not in df.columns:
            df["AdmissionYear"] = st.session_state.year
        if "Program" not in df.columns:
            df["Program"] = st.session_state.program
    return clean_columns(df)

def filter_and_sort_dataframe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    if df.empty:
        return df
    with st.expander(f"🔎 Filter & Sort ({table_name})"):
        search = st.text_input("Global Search", key=f"search_{table_name}").strip().lower()
        mask = pd.Series(True, index=df.index)
        if search:
            mask &= df.apply(lambda row: row.astype(str).str.lower().str.contains(search).any(), axis=1)

        for col in df.columns:
            unique_vals = sorted(df[col].dropna().unique())
            selected = st.multiselect(f"Filter {col}", ["(All)"]+list(unique_vals),
                                      default=["(All)"], key=f"filter_{table_name}_{col}")
            if "(All)" not in selected:
                mask &= df[col].isin(selected)

        df_filtered = df[mask]
        sort_col = st.selectbox("Sort by", ["(No Sort)"]+list(df.columns), key=f"sort_{table_name}")
        if sort_col != "(No Sort)":
            ascending = st.radio("Order", ["Ascending", "Descending"], horizontal=True, key=f"order_{table_name}")
            df_filtered = df_filtered.sort_values(by=sort_col, ascending=(ascending == "Ascending"))
    st.caption(f"📊 Showing {len(df_filtered)} of {len(df)} rows")
    return df_filtered

# -------------------------
# Sidebar: Year + Program
# -------------------------
with st.sidebar:
    st.header("Filters")
    st.session_state.year = st.selectbox("Admission Year", YEAR_OPTIONS, index=0)
    st.session_state.program = st.selectbox("Program", PROGRAM_OPTIONS, index=0)

st.title("Admission Management System")
st.caption(f"Year: **{st.session_state.year}**, Program: **{st.session_state.program}**")

tabs = st.tabs(["CourseMaster", "CollegeMaster", "CollegeCourseMaster", "SeatMatrix", "StudentDetails", "Allotment"])

# ---------- CourseMaster ----------
with tabs[0]:
    df = load_table("CourseMaster")
    df = upload_and_preview("CourseMaster", df)
    df_filtered = filter_and_sort_dataframe(df, "CourseMaster")
    edited = st.data_editor(df_filtered, num_rows="dynamic", use_container_width=True, key="edit_course")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save CourseMaster", key="save_course"):
            save_table("CourseMaster", edited)
    with col2:
        if st.button("🗑️ Flush CourseMaster", key="flush_course"):
            save_table("CourseMaster", pd.DataFrame(columns=df.columns))

# ---------- CollegeMaster ----------
with tabs[1]:
    df = load_table("CollegeMaster")
    df = upload_and_preview("CollegeMaster", df)
    df_filtered = filter_and_sort_dataframe(df, "CollegeMaster")
    edited = st.data_editor(df_filtered, num_rows="dynamic", use_container_width=True, key="edit_college")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save CollegeMaster", key="save_college"):
            save_table("CollegeMaster", edited)
    with col2:
        if st.button("🗑️ Flush CollegeMaster", key="flush_college"):
            save_table("CollegeMaster", pd.DataFrame(columns=df.columns))

# ---------- CollegeCourseMaster ----------
with tabs[2]:
    df = load_table("CollegeCourseMaster")
    df = upload_and_preview("CollegeCourseMaster", df)
    df_filtered = filter_and_sort_dataframe(df, "CollegeCourseMaster")
    edited = st.data_editor(df_filtered, num_rows="dynamic", use_container_width=True, key="edit_ccm")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save CollegeCourseMaster", key="save_ccm"):
            save_table("CollegeCourseMaster", edited)
    with col2:
        if st.button("🗑️ Flush CollegeCourseMaster", key="flush_ccm"):
            save_table("CollegeCourseMaster", pd.DataFrame(columns=df.columns))

# ---------- SeatMatrix ----------
with tabs[3]:
    df = load_table("SeatMatrix")
    df = upload_and_preview("SeatMatrix", df, year_based=True)
    filtered = df[(df["AdmissionYear"]==st.session_state.year) & (df["Program"]==st.session_state.program)] if not df.empty else pd.DataFrame()
    filtered = filter_and_sort_dataframe(filtered, "SeatMatrix")
    edited = st.data_editor(filtered, num_rows="dynamic", use_container_width=True, key="edit_seat")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save SeatMatrix", key="save_seat"):
            save_table("SeatMatrix", edited, replace_where={"AdmissionYear": st.session_state.year, "Program": st.session_state.program})
    with col2:
        if st.button("🗑️ Flush SeatMatrix (Year+Program)", key="flush_seat"):
            save_table("SeatMatrix", pd.DataFrame(columns=filtered.columns), replace_where={"AdmissionYear": st.session_state.year, "Program": st.session_state.program})

# ---------- StudentDetails ----------
with tabs[4]:
    df = load_table("StudentDetails")
    df = upload_and_preview("StudentDetails", df)
    df_filtered = filter_and_sort_dataframe(df, "StudentDetails")
    edited = st.data_editor(df_filtered, num_rows="dynamic", use_container_width=True, key="edit_students")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save StudentDetails", key="save_students"):
            save_table("StudentDetails", edited)
    with col2:
        if st.button("🗑️ Flush StudentDetails", key="flush_students"):
            save_table("StudentDetails", pd.DataFrame(columns=df.columns))

# ---------- Allotment ----------
with tabs[5]:
    df = load_table("Allotment")
    if df.empty:
        st.info("No allotment data available.")
    else:
        st.dataframe(df, use_container_width=True)
