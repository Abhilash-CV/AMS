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
# Download helper (CSV + Excel fallback)
# -------------------------
def download_button_for_df(df: pd.DataFrame, name: str):
    """Show download buttons for DataFrame as CSV and Excel (Excel only if xlsxwriter available)."""
    if df is None or df.empty:
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
    # Excel (try, else show warning in place)
    try:
        import xlsxwriter  # noqa: F401
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
    except Exception:
        col2.warning("⚠️ Excel download unavailable (install xlsxwriter)")

# -------------------------
# DB Connection helper
# -------------------------
@st.cache_resource
def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

# -------------------------
# Utilities
# -------------------------
def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names by replacing spaces/symbols and ensuring uniqueness."""
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

def get_table_columns(table: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(f'PRAGMA table_info("{table}")')
        return [r[1] for r in cur.fetchall()]
    except Exception:
        return []

def ensure_table_and_columns(table: str, df: pd.DataFrame):
    """
    Ensure table exists (create from df if missing) and add missing columns (ALTER TABLE ADD COLUMN).
    If df is empty and table doesn't exist, nothing is created.
    """
    conn = get_conn()
    cur = conn.cursor()
    existing = get_table_columns(table)
    if not existing:
        # create only when df is non-empty (we can't infer schema from empty df)
        if df is None or df.empty:
            # still ensure AdmissionYear/Program columns when table is created later
            return
        # create with df's columns
        col_defs = []
        for col, dtype in zip(df.columns, df.dtypes):
            col_defs.append(f'"{col}" {pandas_dtype_to_sql(dtype)}')
        create_stmt = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)})'
        cur.execute(create_stmt)
        conn.commit()
        existing = get_table_columns(table)

    # Add missing columns (safe: uses TEXT for new columns)
    for col in (df.columns if df is not None else []):
        if col not in existing:
            cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{col}" TEXT')
            conn.commit()
            existing.append(col)

    # Ensure AdmissionYear and Program columns exist (use TEXT)
    for special in ("AdmissionYear", "Program"):
        if special not in existing:
            try:
                cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{special}" TEXT')
                conn.commit()
                existing.append(special)
            except Exception:
                pass

# -------------------------
# Load table (SQL-level year+program filtering)
# -------------------------
def load_table(table: str, year: str = None, program: str = None) -> pd.DataFrame:
    conn = get_conn()
    cur = conn.cursor()
    # If table doesn't exist, return empty df
    if not table_exists(table):
        return pd.DataFrame()
    # ensure special columns exist so queries won't fail
    ensure_table_and_columns(table, pd.DataFrame())  # no df => only ensure AdmissionYear/Program exist
    try:
        if year is not None and program is not None:
            query = f'SELECT * FROM "{table}" WHERE "AdmissionYear"=? AND "Program"=?'
            df = pd.read_sql_query(query, conn, params=(year, program))
        else:
            df = pd.read_sql_query(f'SELECT * FROM "{table}"', conn)
        df = clean_columns(df)
        return df
    except Exception:
        return pd.DataFrame()

# -------------------------
# Save table (smart: add missing columns; preserve other year/program rows)
# -------------------------
def save_table(table: str, df: pd.DataFrame, replace_where: dict = None):
    """
    If replace_where is provided (e.g., {"AdmissionYear": year, "Program": program}),
    delete only matching rows for that filter and insert df rows.
    It will add missing columns to the existing table (ALTER TABLE ADD COLUMN) instead of dropping table,
    so other year/program rows are preserved.
    If replace_where is None -> full overwrite: drop and recreate table from df.
    """
    conn = get_conn()
    cur = conn.cursor()
    df = clean_columns(df) if df is not None else pd.DataFrame()

    if replace_where:
        # Ensure AdmissionYear & Program present in df
        for k, v in replace_where.items():
            if k not in df.columns:
                df[k] = v

        # Ensure table exists and add missing columns to avoid schema mismatch
        ensure_table_and_columns(table, df)

        # Delete existing rows matching replace_where
        where_clause = " AND ".join([f'"{k}"=?' for k in replace_where.keys()])
        params = tuple(replace_where.values())
        try:
            cur.execute(f'DELETE FROM "{table}" WHERE {where_clause}', params)
        except Exception:
            # If table doesn't exist (rare), ensure_table_and_columns will have created it; continue
            pass

        # Prepare insert using only df.columns (which have been added to table)
        if not df.empty:
            quoted_columns = [f'"{c}"' for c in df.columns]
            placeholders = ",".join(["?"] * len(df.columns))
            insert_stmt = f'INSERT INTO "{table}" ({",".join(quoted_columns)}) VALUES ({placeholders})'
            try:
                cur.executemany(insert_stmt, df.values.tolist())
            except Exception as e:
                conn.rollback()
                st.error(f"Error inserting rows into {table}: {e}")
                return
        conn.commit()
        st.success(f"✅ Saved {len(df)} rows to {table} (scoped to {replace_where})")
        return

    # Full overwrite mode: drop & recreate table
    try:
        cur.execute(f'DROP TABLE IF EXISTS "{table}"')
    except Exception:
        pass

    if df is None or df.empty:
        conn.commit()
        st.success(f"✅ Cleared all rows from {table}")
        return

    # create table
    col_defs = []
    for col, dtype in zip(df.columns, df.dtypes):
        col_defs.append(f'"{col}" {pandas_dtype_to_sql(dtype)}')
    create_stmt = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)})'
    cur.execute(create_stmt)
    # insert rows
    quoted_columns = [f'"{c}"' for c in df.columns]
    placeholders = ",".join(["?"] * len(df.columns))
    insert_stmt = f'INSERT INTO "{table}" ({",".join(quoted_columns)}) VALUES ({placeholders})'
    try:
        cur.executemany(insert_stmt, df.values.tolist())
        conn.commit()
        st.success(f"✅ Saved {len(df)} rows to {table}")
    except Exception as e:
        conn.rollback()
        st.error(f"Error saving {table}: {e}")

# -------------------------
# Simple filter & sort UI helper
# -------------------------
def filter_and_sort_dataframe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    if df is None or df.empty:
        st.write(f"⚠️ No data available for {table_name}")
        return df
    with st.expander(f"🔎 Filter & Sort ({table_name})", expanded=False):
        search_text = st.text_input(f"🔍 Global Search ({table_name})", key=f"{table_name}_search_{st.session_state.year}_{st.session_state.program}").lower().strip()
        mask = pd.Series(True, index=df.index)
        if search_text:
            mask &= df.apply(lambda row: row.astype(str).str.lower().str.contains(search_text).any(), axis=1)
        for col in df.columns:
            unique_vals = sorted(df[col].dropna().unique())
            selected_vals = st.multiselect(
                f"Filter {col}",
                ["(All)"]+list(unique_vals),
                default=["(All)"],
                key=f"{table_name}_{col}_filter_{st.session_state.year}_{st.session_state.program}"
            )
            if "(All)" not in selected_vals:
                mask &= df[col].isin(selected_vals)
        filtered = df[mask]
    return filtered

# -------------------------
# Sidebar: Year + Program
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
# Main UI
# -------------------------
st.title("Admission Management System")
st.caption(f"Year: **{year}**, Program: **{program}**")

tabs = st.tabs(["CourseMaster", "CollegeMaster", "CollegeCourseMaster", "SeatMatrix", "StudentDetails", "Allotment", "Vacancy"])

# ---------- CourseMaster (year+program scoped) ----------
with tabs[0]:
    st.subheader("📚 CourseMaster (Year+Program)")
    # Load only the rows for the selected year+program
    df_course = load_table("CourseMaster", year, program)
    # Upload preview
    uploaded_course_key = f"upl_CourseMaster_{year}_{program}"
    uploaded = st.file_uploader("Upload CourseMaster (Excel/CSV)", type=["xlsx", "xls", "csv"], key=uploaded_course_key)
    if uploaded:
        try:
            df_new = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
            df_new = clean_columns(df_new)
            # enforce year+program columns
            df_new["AdmissionYear"] = year
            df_new["Program"] = program
            # Save (replace only for this year+program)
            save_table("CourseMaster", df_new, replace_where={"AdmissionYear": year, "Program": program})
            df_course = load_table("CourseMaster", year, program)
        except Exception as e:
            st.error(f"Error reading file: {e}")

    download_button_for_df(df_course, f"CourseMaster_{year}_{program}")
    st.write(f"Showing rows for AdmissionYear={year} & Program={program}")
    df_course_filtered = filter_and_sort_dataframe(df_course, "CourseMaster")
    edited_course = st.data_editor(
        df_course_filtered,
        num_rows="dynamic",
        use_container_width=True,
        key=f"data_editor_CourseMaster_{year}_{program}"
    )
    if st.button("💾 Save CourseMaster (Year+Program Scoped)", key=f"save_CourseMaster_{year}_{program}"):
        # ensure year+program present before saving
        if "AdmissionYear" not in edited_course.columns:
            edited_course["AdmissionYear"] = year
        if "Program" not in edited_course.columns:
            edited_course["Program"] = program
        save_table("CourseMaster", edited_course, replace_where={"AdmissionYear": year, "Program": program})
        df_course = load_table("CourseMaster", year, program)

# ---------- CollegeMaster (global) ----------
with tabs[1]:
    st.subheader("🏫 CollegeMaster (Global)")
    df_col = load_table("CollegeMaster")
    uploaded = st.file_uploader("Upload CollegeMaster (Excel/CSV)", type=["xlsx", "xls", "csv"], key="upl_CollegeMaster_global")
    if uploaded:
        try:
            df_new = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
            df_new = clean_columns(df_new)
            save_table("CollegeMaster", df_new, replace_where=None)
            df_col = load_table("CollegeMaster")
        except Exception as e:
            st.error(f"Error reading file: {e}")
    df_col_filtered = filter_and_sort_dataframe(df_col, "CollegeMaster")
    edited_col = st.data_editor(
        df_col_filtered,
        num_rows="dynamic",
        use_container_width=True,
        key=f"data_editor_CollegeMaster_global"
    )
    if st.button("💾 Save College Master", key="save_CollegeMaster_global"):
        save_table("CollegeMaster", edited_col, replace_where=None)
        df_col = load_table("CollegeMaster")

# ---------- CollegeCourseMaster (global) ----------
with tabs[2]:
    st.subheader("🏫📚 CollegeCourseMaster (Global)")
    df_cc = load_table("CollegeCourseMaster")
    uploaded = st.file_uploader("Upload CollegeCourseMaster (Excel/CSV)", type=["xlsx", "xls", "csv"], key="upl_CollegeCourseMaster_global")
    if uploaded:
        try:
            df_new = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
            df_new = clean_columns(df_new)
            save_table("CollegeCourseMaster", df_new, replace_where=None)
            df_cc = load_table("CollegeCourseMaster")
        except Exception as e:
            st.error(f"Error reading file: {e}")
    df_cc_filtered = filter_and_sort_dataframe(df_cc, "CollegeCourseMaster")
    edited_cc = st.data_editor(
        df_cc_filtered,
        num_rows="dynamic",
        use_container_width=True,
        key=f"data_editor_CollegeCourseMaster_global"
    )
    if st.button("💾 Save College Course Master", key="save_CollegeCourseMaster_global"):
        save_table("CollegeCourseMaster", edited_cc, replace_where=None)
        df_cc = load_table("CollegeCourseMaster")

    with st.expander("🗑️ Danger Zone: CollegeCourseMaster"):
        st.error("⚠️ This action will permanently delete ALL CollegeCourseMaster data!")
        if st.button("🚨 Flush All CollegeCourseMaster Data", key="flush_cc_btn"):
            st.session_state["confirm_flush_cc"] = True
        if st.session_state.get("confirm_flush_cc", False):
            confirm = st.checkbox("Yes, I understand this will delete all CollegeCourseMaster permanently.", key="flush_cc_confirm")
            if confirm:
                save_table("CollegeCourseMaster", pd.DataFrame(), replace_where=None)
                st.success("✅ All CollegeCourseMaster data cleared!")
                st.session_state["confirm_flush_cc"] = False
                st.experimental_rerun()

# ---------- SeatMatrix (year+program scoped) ----------
with tabs[3]:
    st.subheader("SeatMatrix (Year+Program)")
    df_seat = load_table("SeatMatrix", year, program)
    uploaded = st.file_uploader("Upload SeatMatrix (Excel/CSV)", type=["xlsx", "xls", "csv"], key=f"upl_SeatMatrix_{year}_{program}")
    if uploaded:
        try:
            df_new = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
            df_new = clean_columns(df_new)
            df_new["AdmissionYear"] = year
            df_new["Program"] = program
            save_table("SeatMatrix", df_new, replace_where={"AdmissionYear": year, "Program": program})
            df_seat = load_table("SeatMatrix", year, program)
        except Exception as e:
            st.error(f"Error reading file: {e}")

    download_button_for_df(df_seat, f"SeatMatrix_{year}_{program}")
    st.write(f"Showing rows for AdmissionYear={year} & Program={program}")
    df_seat_filtered = filter_and_sort_dataframe(df_seat, "SeatMatrix")
    edited_seat = st.data_editor(
        df_seat_filtered,
        num_rows="dynamic",
        use_container_width=True,
        key=f"data_editor_SeatMatrix_{year}_{program}"
    )
    if st.button("💾 Save SeatMatrix (Year+Program)", key=f"save_SeatMatrix_{year}_{program}"):
        if "AdmissionYear" not in edited_seat.columns:
            edited_seat["AdmissionYear"] = year
        if "Program" not in edited_seat.columns:
            edited_seat["Program"] = program
        save_table("SeatMatrix", edited_seat, replace_where={"AdmissionYear": year, "Program": program})
        df_seat = load_table("SeatMatrix", year, program)

# ---------- StudentDetails (year+program scoped) ----------
with tabs[4]:
    st.subheader("👨‍🎓 StudentDetails (Year+Program)")
    df_stu = load_table("StudentDetails", year, program)
    uploaded = st.file_uploader("Upload StudentDetails (Excel/CSV)", type=["xlsx", "xls", "csv"], key=f"upl_StudentDetails_{year}_{program}")
    if uploaded:
        try:
            df_new = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
            df_new = clean_columns(df_new)
            df_new["AdmissionYear"] = year
            df_new["Program"] = program
            save_table("StudentDetails", df_new, replace_where={"AdmissionYear": year, "Program": program})
            df_stu = load_table("StudentDetails", year, program)
        except Exception as e:
            st.error(f"Error reading file: {e}")

    download_button_for_df(df_stu, f"StudentDetails_{year}_{program}")
    st.write(f"Showing rows for AdmissionYear={year} & Program={program}")
    df_stu_filtered = filter_and_sort_dataframe(df_stu, "StudentDetails")
    edited_stu = st.data_editor(
        df_stu_filtered,
        num_rows="dynamic",
        use_container_width=True,
        key=f"data_editor_StudentDetails_{year}_{program}"
    )
    if st.button("💾 Save StudentDetails (Year+Program Scoped)", key=f"save_StudentDetails_{year}_{program}"):
        if "AdmissionYear" not in edited_stu.columns:
            edited_stu["AdmissionYear"] = year
        if "Program" not in edited_stu.columns:
            edited_stu["Program"] = program
        save_table("StudentDetails", edited_stu, replace_where={"AdmissionYear": year, "Program": program})
        df_stu = load_table("StudentDetails", year, program)

    with st.expander("🗑️ Danger Zone: StudentDetails"):
        st.error("⚠️ This action will permanently delete ALL StudentDetails data!")
        if st.button("🚨 Flush All StudentDetails Data", key="flush_stu_btn"):
            st.session_state["confirm_flush_stu"] = True
        if st.session_state.get("confirm_flush_stu", False):
            confirm = st.checkbox("Yes, delete ALL StudentDetails permanently.", key="flush_stu_confirm")
            if confirm:
                save_table("StudentDetails", pd.DataFrame(), replace_where=None)
                st.success("✅ All StudentDetails data cleared!")
                st.session_state["confirm_flush_stu"] = False
                st.experimental_rerun()

# ---------- Allotment (global) ----------
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
