# admission_app_stream.py
import re
import io
import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime

# -------------------------
# GLOBAL CONFIG
# -------------------------
DB_FILE = "admission.db"
PROGRAM_OPTIONS = ["LLB5", "LLB3", "PGN", "Engineering"]
YEAR_OPTIONS = ["2023", "2024", "2025", "2026"]

st.set_page_config(page_title="Admission Management System", layout="wide")

# -------------------------
# Download helper
# -------------------------
def download_button_for_df(df: pd.DataFrame, name: str):
    """Show download buttons for DataFrame as CSV and Excel."""
    if df.empty:
        st.warning("⚠️ No data to download.")
        return
    col1, col2 = st.columns(2)
    csv_data = df.to_csv(index=False).encode("utf-8")
    col1.download_button(
        label=f"⬇ Download {name} (CSV)",
        data=csv_data,
        file_name=f"{name}.csv",
        mime="text/csv",
        use_container_width=True
    )

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    col2.download_button(
        label=f"⬇ Download {name} (Excel)",
        data=excel_buffer.getvalue(),
        file_name=f"{name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# -------------------------
# DB Connection helper
# -------------------------
@st.cache_resource
def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

# -------------------------
# Utility: clean column names
# -------------------------
def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names by replacing spaces/symbols and ensuring uniqueness."""
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

# -------------------------
# Load table safely
# -------------------------
def load_table(table: str) -> pd.DataFrame:
    conn = get_conn()
    try:
        df = pd.read_sql(f'SELECT * FROM "{table}"', conn)
        df = clean_columns(df)
    except Exception:
        df = pd.DataFrame()
    return df

# -------------------------
# Upload preview helper
# -------------------------
def upload_and_preview(table_name: str, existing_df: pd.DataFrame, year_based: bool = False):
    uploaded = st.file_uploader(f"Upload {table_name} (Excel/CSV)", type=["xlsx", "csv"], key=f"upl_{table_name}_{st.session_state.year}_{st.session_state.program}")
    df = existing_df.copy() if existing_df is not None else pd.DataFrame()
    if uploaded:
        try:
            if uploaded.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            st.success(f"Loaded {len(df)} rows from {uploaded.name}")
        except Exception as e:
            st.error(f"Error reading file: {e}")
            return existing_df
    if year_based:
        if "AdmissionYear" not in df.columns:
            df["AdmissionYear"] = st.session_state.year
        if "Program" not in df.columns:
            df["Program"] = st.session_state.program
    df = clean_columns(df)
    if uploaded:
        st.info(f"Cleaned column names: {', '.join(df.columns)}")
    return df

# -------------------------
# Save table safely (replace by Year+Program if specified)
# -------------------------
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
        st.success(f"✅ Saved {len(df)} rows to {table} (Year+Program scoped)")
        return

    # Full table overwrite
    cur.execute(f'DROP TABLE IF EXISTS "{table}"')
    if not df.empty:
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

# -------------------------
# Filter & sort helper
# -------------------------
def filter_and_sort_dataframe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    if df.empty:
        st.write(f"⚠️ No data available for {table_name}")
        return df
    with st.expander(f"🔎 Filter & Sort ({table_name})", expanded=False):
        search_text = st.text_input(f"🔍 Global Search ({table_name})", key=f"{table_name}_search_{st.session_state.year}_{st.session_state.program}").lower().strip()
        mask = pd.Series(True, index=df.index)
        if search_text:
            mask &= df.apply(lambda row: row.astype(str).str.lower().str.contains(search_text).any(), axis=1)
        for col in df.columns:
            unique_vals = sorted(df[col].dropna().unique())
            selected_vals = st.multiselect(f"Filter {col}", ["(All)"]+list(unique_vals),
                                           default=["(All)"], key=f"{table_name}_{col}_{st.session_state.year}_{st.session_state.program}")
            if "(All)" not in selected_vals:
                mask &= df[col].isin(selected_vals)
        filtered = df[mask]
    return filtered

# -------------------------
# Sidebar
# -------------------------
with st.sidebar:
    st.header("Filters")
    if "year" not in st.session_state: st.session_state.year = YEAR_OPTIONS[0]
    if "program" not in st.session_state: st.session_state.program = PROGRAM_OPTIONS[0]
    st.session_state.year = st.selectbox("Admission Year", YEAR_OPTIONS, index=YEAR_OPTIONS.index(st.session_state.year))
    st.session_state.program = st.selectbox("Program", PROGRAM_OPTIONS, index=PROGRAM_OPTIONS.index(st.session_state.program))

# -------------------------
# Main UI
# -------------------------
st.title("Admission Management System")
st.caption(f"Year: **{st.session_state.year}**, Program: **{st.session_state.program}**")

tabs = st.tabs(["CourseMaster", "CollegeMaster", "CollegeCourseMaster", "SeatMatrix", "StudentDetails", "Allotment", "Vacancy"])

# ---------- CourseMaster ----------
with tabs[0]:
    df_course_all = load_table("CourseMaster")
    df_course_all = upload_and_preview("CourseMaster", df_course_all, year_based=True)
    ay, pr = st.session_state.year, st.session_state.program
    df_course = df_course_all[(df_course_all.get("AdmissionYear", ay)==ay) & (df_course_all.get("Program", pr)==pr)] if not df_course_all.empty else pd.DataFrame()
    download_button_for_df(df_course, f"CourseMaster_{ay}_{pr}")
    df_filtered = filter_and_sort_dataframe(df_course, "CourseMaster")
    edited = st.data_editor(df_filtered, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save CourseMaster (Year+Program Scoped)"):
        edited["AdmissionYear"] = ay
        edited["Program"] = pr
        save_table("CourseMaster", edited, replace_where={"AdmissionYear": ay, "Program": pr})

# ---------- SeatMatrix ----------
with tabs[3]:
    df_seat_all = load_table("SeatMatrix")
    df_seat_all = upload_and_preview("SeatMatrix", df_seat_all, year_based=True)
    ay, pr = st.session_state.year, st.session_state.program
    df_seat = df_seat_all[(df_seat_all.get("AdmissionYear", ay)==ay) & (df_seat_all.get("Program", pr)==pr)] if not df_seat_all.empty else pd.DataFrame()
    download_button_for_df(df_seat, f"SeatMatrix_{ay}_{pr}")
    df_filtered = filter_and_sort_dataframe(df_seat, "SeatMatrix")
    edited = st.data_editor(df_filtered, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save SeatMatrix (Year+Program)"):
        edited["AdmissionYear"] = ay
        edited["Program"] = pr
        save_table("SeatMatrix", edited, replace_where={"AdmissionYear": ay, "Program": pr})

# ---------- StudentDetails ----------
with tabs[4]:
    df_stu_all = load_table("StudentDetails")
    df_stu_all = upload_and_preview("StudentDetails", df_stu_all, year_based=True)
    ay, pr = st.session_state.year, st.session_state.program
    df_stu = df_stu_all[(df_stu_all.get("AdmissionYear", ay)==ay) & (df_stu_all.get("Program", pr)==pr)] if not df_stu_all.empty else pd.DataFrame()
    download_button_for_df(df_stu, f"StudentDetails_{ay}_{pr}")
    df_filtered = filter_and_sort_dataframe(df_stu, "StudentDetails")
    edited = st.data_editor(df_filtered, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save StudentDetails (Year+Program Scoped)"):
        edited["AdmissionYear"] = ay
        edited["Program"] = pr
        save_table("StudentDetails", edited, replace_where={"AdmissionYear": ay, "Program": pr})
