# admission_app_stream_fixed.py
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

def upload_and_preview(table_name: str, existing_df: pd.DataFrame, year_based: bool=False):
    uploaded = st.file_uploader(
        f"Upload {table_name} (Excel/CSV)",
        type=["xlsx", "csv"],
        key=f"uploader_{table_name}"
    )
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
    return clean_columns(df)

def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    return buffer.getvalue()

def download_button_for_df(df: pd.DataFrame, table_name: str):
    if df is None or df.empty:
        st.write("No data to download")
        return
    excel_bytes = df_to_excel_bytes(df)
    st.download_button(
        label=f"⬇️ Download {table_name}.xlsx",
        data=excel_bytes,
        file_name=f"{table_name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_{table_name}"
    )

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
            quoted_cols = [f'"{c}"' for c in df.columns]
            placeholders = ",".join(["?"] * len(df.columns))
            cur.executemany(
                f'INSERT INTO "{table}" ({",".join(quoted_cols)}) VALUES ({placeholders})',
                df.values.tolist()
            )
        conn.commit()
        st.success(f"Saved {len(df)} rows to {table} (filtered save)")
        return

    if df.empty:
        try:
            cur.execute(f'DELETE FROM "{table}"')
            conn.commit()
            st.success(f"Cleared all rows from {table}")
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
    quoted_cols = [f'"{c}"' for c in df.columns]
    placeholders = ",".join(["?"] * len(df.columns))
    cur.executemany(
        f'INSERT INTO "{table}" ({",".join(quoted_cols)}) VALUES ({placeholders})',
        df.values.tolist()
    )
    conn.commit()
    st.success(f"Saved {len(df)} rows to {table}")

def filter_and_sort_dataframe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    if df.empty:
        st.write(f"⚠️ No data available for {table_name}")
        return df
    with st.expander(f"🔎 Filter & Sort ({table_name})", expanded=False):
        search_text = st.text_input(f"🔍 Search", key=f"search_{table_name}").lower().strip()
        global_mask = df.apply(lambda row: True, axis=1)
        if search_text:
            global_mask = df.apply(lambda r: r.astype(str).str.lower().str.contains(search_text).any(), axis=1)

        column_masks = []
        for col in df.columns:
            unique_vals = sorted(df[col].dropna().unique())
            selected = st.multiselect(f"Filter {col}", ["(All)"]+list(unique_vals),
                                      default=["(All)"], key=f"filter_{table_name}_{col}")
            if "(All)" not in selected:
                column_masks.append(df[col].isin(selected))
        combined_mask = column_masks[0] if column_masks else global_mask
        for m in column_masks[1:]:
            combined_mask &= m
        filtered_df = df[global_mask & combined_mask]
        sort_col = st.selectbox("Sort by", ["(No Sort)"]+list(df.columns), key=f"sort_{table_name}")
        if sort_col != "(No Sort)":
            ascending = st.radio("Order", ["Ascending", "Descending"], horizontal=True, key=f"order_{table_name}")
            filtered_df = filtered_df.sort_values(by=sort_col, ascending=(ascending=="Ascending"))
    st.caption(f"📊 Showing {len(filtered_df)} of {len(df)} rows")
    return filtered_df

# -------------------------
# Sidebar
# -------------------------
with st.sidebar:
    st.header("Filters")
    st.session_state.year = st.selectbox("Admission Year", YEAR_OPTIONS, index=0)
    st.session_state.program = st.selectbox("Program", PROGRAM_OPTIONS, index=0)

st.title("Admission Management System")
st.caption(f"Year: **{st.session_state.year}**, Program: **{st.session_state.program}**")

tabs = st.tabs(["CourseMaster", "CollegeMaster", "CollegeCourseMaster", "SeatMatrix", "StudentDetails", "Allotment", "Vacancy"])

# ---------- CourseMaster ----------
with tabs[0]:
    st.subheader("📚 CourseMaster")
    df = load_table("CourseMaster")
    df = upload_and_preview("CourseMaster", df)
    download_button_for_df(df, "CourseMaster")
    df_filtered = filter_and_sort_dataframe(df, "CourseMaster")
    edited = st.data_editor(df_filtered, num_rows="dynamic", use_container_width=True, key="edit_course")
    if st.button("💾 Save CourseMaster", key="save_course"):
        save_table("CourseMaster", edited)

# ---------- CollegeMaster ----------
with tabs[1]:
    st.subheader("🏫 CollegeMaster")
    df = load_table("CollegeMaster")
    df = upload_and_preview("CollegeMaster", df)
    df_filtered = filter_and_sort_dataframe(df, "CollegeMaster")
    edited = st.data_editor(df_filtered, num_rows="dynamic", use_container_width=True, key="edit_college")
    if st.button("💾 Save CollegeMaster", key="save_college"):
        save_table("CollegeMaster", edited)

# ---------- CollegeCourseMaster ----------
with tabs[2]:
    st.subheader("🏫📚 CollegeCourseMaster")
    df = load_table("CollegeCourseMaster")
    df = upload_and_preview("CollegeCourseMaster", df)
    df_filtered = filter_and_sort_dataframe(df, "CollegeCourseMaster")
    edited = st.data_editor(df_filtered, num_rows="dynamic", use_container_width=True, key="edit_ccm")
    if st.button("💾 Save CollegeCourseMaster", key="save_ccm"):
        save_table("CollegeCourseMaster", edited)

# ---------- SeatMatrix ----------
with tabs[3]:
    st.subheader("SeatMatrix (Year+Program)")
    df = load_table("SeatMatrix")
    df = upload_and_preview("SeatMatrix", df, year_based=True)
    filtered = df[(df["AdmissionYear"]==st.session_state.year) & (df["Program"]==st.session_state.program)] if not df.empty else pd.DataFrame()
    download_button_for_df(filtered, f"SeatMatrix_{st.session_state.year}_{st.session_state.program}")
    edited = st.data_editor(filtered, num_rows="dynamic", use_container_width=True, key="edit_seat")
    if st.button("💾 Save SeatMatrix", key="save_seat"):
        save_table("SeatMatrix", edited, replace_where={"AdmissionYear": st.session_state.year, "Program": st.session_state.program})

# ---------- StudentDetails ----------
with tabs[4]:
    st.subheader("👨‍🎓 StudentDetails")
    df = load_table("StudentDetails")
    df = upload_and_preview("StudentDetails", df)
    df_filtered = filter_and_sort_dataframe(df, "StudentDetails")
    edited = st.data_editor(df_filtered, num_rows="dynamic", use_container_width=True, key="edit_students")
    if st.button("💾 Save StudentDetails", key="save_students"):
        save_table("StudentDetails", edited)

# ---------- Allotment ----------
with tabs[5]:
    st.subheader("Allotment (View)")
    df = load_table("Allotment")
    if df.empty:
        st.info("No data available.")
    else:
        download_button_for_df(df, "Allotment")
        st.dataframe(df, use_container_width=True)

# ---------- Vacancy ----------
with tabs[6]:
    st.subheader("Vacancy (Coming Soon)")
    st.info("Vacancy calculation will be added later.")
