# admission_app_stream_fixed.py
import io
import re
import sqlite3
from datetime import datetime


import pandas as pd
import plotly.express as px
import streamlit as st

# -------------------------
# Configuration
# -------------------------
DB_FILE = "admission.db"
PROGRAM_OPTIONS = ["LLB5", "LLB3", "PGN", "Engineering"]
YEAR_OPTIONS = ["2023", "2024", "2025", "2026"]

st.set_page_config(
    page_title="Admission Management System",
    layout="wide",
    page_icon="🏫",
)
# Initialize global dfs to avoid NameError
df_seat = pd.DataFrame()
df_course = pd.DataFrame()
df_student = pd.DataFrame()
df_col = pd.DataFrame()

# -------------------------
# DB Helpers
# -------------------------
@st.cache_resource
def get_conn():
    """Return a SQLite connection. Cached to avoid reopening on every interaction."""
    return sqlite3.connect(DB_FILE, check_same_thread=False)


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
        if s in seen: {kpi['color']}
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
    Ensure table exists. If missing, create one. If df provided and non-empty, create schema from df.
    If df is empty and table missing, create a minimal table with AdmissionYear and Program so
    subsequent filtered queries won't fail.
    Also adds missing columns (as TEXT) when df has columns not present in table.
    """
    conn = get_conn()
    cur = conn.cursor()
    existing = get_table_columns(table)

    # Create table if it doesn't exist
    if not existing:
        if df is None or df.empty:
            # Create minimal table so filtered SELECTs work later
            cur.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ("AdmissionYear" TEXT, "Program" TEXT)')
            conn.commit() {kpi['color']}
            existing = get_table_columns(table)
        else:
            # Create using df schema
            col_defs = []
            for col, dtype in zip(df.columns, df.dtypes):
                col_defs.append(f'"{col}" {pandas_dtype_to_sql(dtype)}')
            # Ensure AdmissionYear/Program present in created table
            if "AdmissionYear" not in df.columns:
                col_defs.append('"AdmissionYear" TEXT')
            if "Program" not in df.columns:
                col_defs.append('"Program" TEXT')
            create_stmt = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)})'
            cur.execute(create_stmt)
            conn.commit()
            existing = get_table_columns(table)

    # Add missing columns from df as TEXT
    if df is not None:
        for col in df.columns:
            if col not in existing:
                try:
                    cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{col}" TEXT')
                    conn.commit()
                    existing.append(col)
                except Exception:
                    # ignore failures to add columns
                    pass

    # Ensure AdmissionYear and Program exist
    for special in ("AdmissionYear", "Program"):
        if special not in existing:
            try:
                cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{special}" TEXT')
                conn.commit()
                existing.append(special)
            except Exception:
                pass


# -------------------------
# Load / Save helpers
# -------------------------

def load_table(table: str, year: str = None, program: str = None) -> pd.DataFrame:
    conn = get_conn()
    cur = conn.cursor()
    if not table_exists(table):
        # ensure minimal table so UI does not break
        ensure_table_and_columns(table, pd.DataFrame())
        return pd.DataFrame()

    # Ensure special columns exist for safe queries
    ensure_table_and_columns(table, pd.DataFrame())

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


def save_table(table: str, df: pd.DataFrame, replace_where: dict = None):
    """
    Save DataFrame into SQLite.
    If replace_where is provided, delete only matching rows and insert df rows (scoped save).
    If replace_where is None, drop and recreate table from df (full overwrite).
    """
    conn = get_conn()
    cur = conn.cursor()
    df = clean_columns(df) if df is not None else pd.DataFrame()

    if replace_where:
        # ensure the replace keys exist in df
        for k, v in replace_where.items(): {kpi['color']}
            if k not in df.columns:
                df[k] = v

        ensure_table_and_columns(table, df)

        # Delete existing rows matching replace_where
        where_clause = " AND ".join([f'"{k}"=?' for k in replace_where.keys()])
        params = tuple(replace_where.values())
        try:
            cur.execute(f'DELETE FROM "{table}" WHERE {where_clause}', params)
        except Exception:
            pass

        # Insert df rows
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

    # Full overwrite
    try:
        cur.execute(f'DROP TABLE IF EXISTS "{table}"')
    except Exception:
        pass

    if df is None or df.empty:
        conn.commit()
        st.success(f"✅ Cleared all rows from {table}")
        return

    # create table with df schema
    col_defs = []
    for col, dtype in zip(df.columns, df.dtypes):
        col_defs.append(f'"{col}" {pandas_dtype_to_sql(dtype)}')
    create_stmt = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)})'
    cur.execute(create_stmt)

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
# UI Helpers
# -------------------------
import random
import string

def download_button_for_df(df: pd.DataFrame, name: str):
    """Show download buttons for DataFrame as CSV and Excel (Excel only if xlsxwriter available).
    Adds a random suffix to keys to avoid duplicate element errors if called multiple times.
    """
    if df is None or df.empty:
        st.warning("⚠️ No data to download.")
        return
 {kpi['color']}
    # Generate a short random key suffix to ensure uniqueness even if name repeats
    rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

    col1, col2 = st.columns(2)
    csv_data = df.to_csv(index=False).encode("utf-8")
    col1.download_button(
        label=f"⬇ Download {name} (CSV)",
        data=csv_data,
        file_name=f"{name}.csv",
        mime="text/csv",
        key=f"download_csv_{name}_{rand_suffix}",  # ✅ unique key with random suffix
        use_container_width=True
    )
    try:
        import xlsxwriter
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Sheet1")
        col2.download_button(
            label=f"⬇ Download {name} (Excel)",
            data=excel_buffer.getvalue(),
            file_name=f"{name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_xlsx_{name}_{rand_suffix}",  # ✅ unique key with random suffix
            use_container_width=True
        )
    except Exception:
        col2.warning("⚠️ Excel download unavailable (install xlsxwriter)")



import random, string

import streamlit as st
import pandas as pd
import hashlib

# Track call count per table to avoid duplicates
if "filter_call_count" not in st.session_state:
    st.session_state.filter_call_count = {}

def safe_key(*args):
    """Generate a deterministic short hash key from multiple strings/values."""
    s = "_".join(str(a) for a in args)
    return hashlib.md5(s.encode()).hexdigest()[:10]

def filter_and_sort_dataframe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    if df is None or df.empty:
        st.write(f"⚠️ No data available for {table_name}")
        return df

    year = st.session_state.get("year", "")
    program = st.session_state.get("program", "")

    # Increment call counter per table
    count = st.session_state.filter_call_count.get(table_name, 0) + 1
    st.session_state.filter_call_count[table_name] = count

    unique_prefix = f"{table_name}_{year}_{program}_{count}"

    # ---------- Filters UI ----------
    with st.expander(f"🔎 Filter & Sort ({table_name})", expanded=False):
        # Global search
        search_key = f"{unique_prefix}_search"
        search_text = st.text_input(
            f"🔍 Global Search ({table_name})",
            key=search_key
        ).lower().strip()

        mask = pd.Series(True, index=df.index)
        if search_text:
            mask &= df.apply(
                lambda row: row.astype(str).str.lower().str.contains(search_text).any(),
                axis=1
            )

        # Column filters
        for col in df.columns:
            options = ["(All)"] + sorted([str(x) for x in df[col].dropna().unique()])
            col_key = f"{unique_prefix}_{col}_filter"
            selected_vals = st.multiselect(
                f"Filter {col}",
                options,
                default=["(All)"],
                key=col_key
            )
            if selected_vals and "(All)" not in selected_vals:
                mask &= df[col].astype(str).isin(selected_vals)

        # Clear filters button
        clear_key = f"{unique_prefix}_clear"
        if st.button(f"Clear Filters ({table_name})", key=clear_key):
            # Remove global search and column filters for this unique_prefix
            st.session_state.pop(search_key, None)
            for col in df.columns:
                st.session_state.pop(f"{unique_prefix}_{col}_filter", None)
            st.experimental_rerun()

    # ---------- Apply mask ----------
    filtered = df[mask]

    # ---------- Reset index starting from 1 ----------
    filtered = filtered.reset_index(drop=True)
    filtered.index = filtered.index + 1

    # ---------- Display filtered row count ----------
    total = len(df)
    count = len(filtered)
    percent = (count / total * 100) if total > 0 else 0
    st.info(f"📊 Showing **{count} / {total}** records ({percent:.1f}%)")

    return filtered


# -------------------------
# Sidebar Filters & Navigation
# -------------------------
st.sidebar.title("Filters & Navigation")
if "year" not in st.session_state:
    st.session_state.year = YEAR_OPTIONS[-1]
if "program" not in st.session_state:
    st.session_state.program = PROGRAM_OPTIONS[0]

st.session_state.year = st.sidebar.selectbox("Admission Year", YEAR_OPTIONS, index=YEAR_OPTIONS.index(st.session_state.year))
st.session_state.program = st.sidebar.selectbox("Program", PROGRAM_OPTIONS, index=PROGRAM_OPTIONS.index(st.session_state.program))

year = st.session_state.year
program = st.session_state.program

# Sidebar navigation
from streamlit_extras.switch_page_button import switch_page
#page = st.sidebar.selectbox(
  #  "📂 Navigate",
   # ["Dashboard", "CourseMaster", "CollegeMaster", "CollegeCourseMaster", "SeatMatrix", "StudentDetails", "Allotment", "Vacancy"],
   # key="nav_page"
#)
from streamlit_option_menu import option_menu

# ✅ Install once (if not installed)
# pip install streamlit-option-menu

from streamlit_option_menu import option_menu

# Sidebar Navigation with Icons
from streamlit_option_menu import option_menu

with st.sidebar:
    st.markdown("## 📂 Navigation")
    page = option_menu(
        None,
        ["Dashboard", "CourseMaster", "CollegeMaster", "CollegeCourseMaster",
         "SeatMatrix", "StudentDetails", "Allotment", "Vacancy"],
        icons=[
            "house",          # Dashboard
            "journal-bookmark",  # CourseMaster
            "buildings",      # ✅ Valid icon for CollegeMaster
            "collection",     # CollegeCourseMaster
            "grid-3x3-gap",   # SeatMatrix
            "people",         # StudentDetails
            "clipboard-check",# Allotment
            "exclamation-circle"  # Vacancy
        ],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "5px", "background-color": "#f8f9fa"},
            "icon": {"color": "#2C3E50", "font-size": "18px"},
            "nav-link": {
                "font-size": "12px",
                "text-align": "left",
                "margin": "0px",
                "--hover-color": "#e1eafc",
            },
            "nav-link-selected": {"background-color": "#4CAF50", "color": "white"},
        }
    )


# -------------------------
# Conditional Page Rendering
# -------------------------
if page == "Dashboard":
    # --- Load Data ---
    df_course = load_table("CourseMaster", year, program)
    df_col = load_table("CollegeMaster")
    df_student = load_table("StudentDetails", year, program)
    df_seat = load_table("SeatMatrix", year, program)

    st.title("🎯 Admission Dashboard")
    st.markdown(f"**Year:** {year} | **Program:** {program}")

    # --- KPI Cards ---
    st.subheader("📊 Key Metrics")
    kpi_cols = st.columns(4)

    total_courses = len(df_course)
    total_colleges = len(df_col)
    total_students = len(df_student)
    total_seats = int(df_seat["Seats"].sum()) if not df_seat.empty and "Seats" in df_seat.columns else 0

    kpi_data = [
        {"icon": "🏫", "title": "Courses", "value": total_courses, "color": "#FF6B6B"},
        {"icon": "🏛️", "title": "Colleges", "value": total_colleges, "color": "#4ECDC4"},
        {"icon": "👨‍🎓", "title": "Students", "value": total_students, "color": "#556270"},
        {"icon": "💺", "title": "Seats", "value": total_seats, "color": "#C7F464"},
    ]

    # Function to render small colored KPI card
    def kpi_card(col, icon, title, value, color="#000000"):
    col.markdown(
        f"""
        <div style="
            background-color: {color};  /* use the color passed to function */
            padding:8px;
            border-radius:10px;
            text-align:center;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
            margin-bottom:5px;
        ">
            <div style="font-size:16px; font-weight:bold">{icon}</div>
            <div style="font-size:14px; color:#333">{title}</div>
            <div style="font-size:20px; font-weight:bold">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    for col, kpi in zip(kpi_cols, kpi_data):
        kpi_card(col, kpi["icon"], kpi["title"], kpi["value"], kpi["color"])

    # --- Charts Section ---
    st.subheader("📈 Visual Analytics")
    chart_col1, chart_col2 = st.columns(2)

    # Seats by Category (Mini Bar)
    if not df_seat.empty and "Category" in df_seat.columns and "Seats" in df_seat.columns:
        seat_cat = df_seat.groupby("Category")["Seats"].sum().reset_index()
        fig_seats = px.bar(
            seat_cat,
            x="Category",
            y="Seats",
            text="Seats",
            color="Seats",
            color_continuous_scale="Viridis",
            template="plotly_white",
            height=300
        )
        fig_seats.update_traces(textposition="outside", marker_line_width=1)
        chart_col1.plotly_chart(fig_seats, use_container_width=True)

    # Students by Quota (Mini Pie)
    if not df_student.empty and "Quota" in df_student.columns:
        quota_count = df_student["Quota"].value_counts().reset_index()
        quota_count.columns = ["Quota", "Count"]
        fig_quota = px.pie(
            quota_count,
            names="Quota",
            values="Count",
            hole=0.5,
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Set3,
            height=300
        )
        chart_col2.plotly_chart(fig_quota, use_container_width=True)

    # Courses per College (Compact Bar)
    if not df_course.empty and "College" in df_course.columns:
        st.subheader("🏫 Courses per College")
        col_course_count = df_course["College"].value_counts().reset_index()
        col_course_count.columns = ["College", "Courses"]
        fig_col_course = px.bar(
            col_course_count,
            x="College",
            y="Courses",
            text="Courses",
            color="Courses",
            template="plotly_white",
            color_continuous_scale="Plasma",
            height=300
        )
        fig_col_course.update_traces(textposition="outside", marker_line_width=1)
        st.plotly_chart(fig_col_course, use_container_width=True)

    # --- Summary Table ---
    st.subheader("📋 Quick Overview")
    summary_df = pd.DataFrame({
        "Metric": ["Courses", "Colleges", "Students", "Seats"],
        "Count": [total_courses, total_colleges, total_students, total_seats]
    })
    st.table(summary_df)


elif page == "CourseMaster":
    st.header("📚 CourseMaster")
    df_course = load_table("CourseMaster", year, program)
    uploaded = st.file_uploader("Upload CourseMaster", type=["xlsx", "xls", "csv"])
    if uploaded:
        df_new = pd.read_excel(uploaded) if uploaded.name.endswith(".xlsx") else pd.read_csv(uploaded)
        df_new = clean_columns(df_new)
        df_new["AdmissionYear"] = year
        df_new["Program"] = program
        save_table("CourseMaster", df_new, replace_where={"AdmissionYear": year, "Program": program})
        df_course = load_table("CourseMaster", year, program)
    download_button_for_df(df_course, f"CourseMaster_{year}_{program}")
    df_course_filtered = filter_and_sort_dataframe(df_course, "CourseMaster")
    edited_course = st.data_editor(df_course_filtered, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save CourseMaster"):
        if "AdmissionYear" not in edited_course.columns:
            edited_course["AdmissionYear"] = year
        if "Program" not in edited_course.columns:
            edited_course["Program"] = program
        save_table("CourseMaster", edited_course, replace_where={"AdmissionYear": year, "Program": program})

elif page == "SeatMatrix":
    st.header("SeatMatrix")
    df_seat = load_table("SeatMatrix", year, program)
    uploaded = st.file_uploader("Upload SeatMatrix", type=["xlsx", "xls", "csv"])
    if uploaded:
        df_new = pd.read_excel(uploaded) if uploaded.name.endswith(".xlsx") else pd.read_csv(uploaded)
        df_new = clean_columns(df_new)
        df_new["AdmissionYear"] = year
        df_new["Program"] = program
        save_table("SeatMatrix", df_new, replace_where={"AdmissionYear": year, "Program": program})
        df_seat = load_table("SeatMatrix", year, program)
    download_button_for_df(df_seat, f"SeatMatrix_{year}_{program}")
    df_seat_filtered = filter_and_sort_dataframe(df_seat, "SeatMatrix")
    edited_seat = st.data_editor(df_seat_filtered, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save SeatMatrix"):
        if "AdmissionYear" not in edited_seat.columns:
            edited_seat["AdmissionYear"] = year
        if "Program" not in edited_seat.columns:
            edited_seat["Program"] = program
        save_table("SeatMatrix", edited_seat, replace_where={"AdmissionYear": year, "Program": program})

elif page == "StudentDetails":
    st.header("👨‍🎓 StudentDetails")
    df_stu = load_table("StudentDetails", year, program)
    uploaded = st.file_uploader("Upload StudentDetails", type=["xlsx", "xls", "csv"])
    if uploaded:
        df_new = pd.read_excel(uploaded) if uploaded.name.endswith(".xlsx") else pd.read_csv(uploaded)
        df_new = clean_columns(df_new)
        df_new["AdmissionYear"] = year
        df_new["Program"] = program
        save_table("StudentDetails", df_new, replace_where={"AdmissionYear": year, "Program": program})
        df_stu = load_table("StudentDetails", year, program)
    download_button_for_df(df_stu, f"StudentDetails_{year}_{program}")
    df_stu_filtered = filter_and_sort_dataframe(df_stu, "StudentDetails")
    edited_stu = st.data_editor(df_stu_filtered, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save StudentDetails"):
        if "AdmissionYear" not in edited_stu.columns:
            edited_stu["AdmissionYear"] = year
        if "Program" not in edited_stu.columns:
            edited_stu["Program"] = program
        save_table("StudentDetails", edited_stu, replace_where={"AdmissionYear": year, "Program": program})

elif page == "CollegeMaster":
    st.header("🏫 CollegeMaster")
    df_col = load_table("CollegeMaster")
    df_col_filtered = filter_and_sort_dataframe(df_col, "CollegeMaster")
    st.data_editor(df_col_filtered, num_rows="dynamic", use_container_width=True)

elif page == "CollegeCourseMaster":
    st.header("🏫📚 CollegeCourseMaster")
    df_cc = load_table("CollegeCourseMaster")
    uploaded = st.file_uploader("Upload CollegeCourseMaster", type=["xlsx", "xls", "csv"])
    if uploaded:
        df_new = pd.read_excel(uploaded) if uploaded.name.endswith(".xlsx") else pd.read_csv(uploaded)
        df_new = clean_columns(df_new)
        df_new["AdmissionYear"] = year
        df_new["Program"] = program
        save_table("CollegeCourseMaster", df_new, replace_where={"AdmissionYear": year, "Program": program})
        df_cc = load_table("CollegeCourseMaster", year, program)
    download_button_for_df(df_cc, f"CollegeCourseMaster{year}_{program}")
    df_cc_filtered = filter_and_sort_dataframe(df_cc, "CollegeCourseMaster")
    edited_cc = st.data_editor(df_cc_filtered, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save CollegeCourseMaster"):
        if "AdmissionYear" not in edited_cc.columns:
            edited_cc["AdmissionYear"] = year
        if "Program" not in edited_cc.columns:
            edited_cc["Program"] = program
        save_table("CollegeCourseMaster", edited_cc, replace_where={"AdmissionYear": year, "Program": program})
    

elif page == "Allotment":
    st.header("Allotment (Global)")
    df_allot = load_table("Allotment")
    if df_allot.empty:
        st.info("No allotment data found yet.")
    else:
        download_button_for_df(df_allot, "Allotment")
        st.dataframe(df_allot, use_container_width=True)

elif page == "Vacancy":
    st.header("Vacancy")
    st.info("Vacancy calculation will be added later.")

# ... repeat for other pages

# Seats by Category
if not df_seat.empty and "Category" in df_seat.columns and "Seats" in df_seat.columns:
    seat_cat = df_seat.groupby("Category")["Seats"].sum().reset_index()
    fig1 = px.bar(seat_cat, x="Category", y="Seats", color="Seats", title="Seats by Category")
    chart_col1.plotly_chart(fig1, use_container_width=True)

# Students by Quota
if not df_student.empty and "Quota" in df_student.columns:
    quota_count = df_student["Quota"].value_counts().reset_index()
    quota_count.columns = ["Quota", "Count"]
    fig2 = px.pie(quota_count, names="Quota", values="Count", title="Student Distribution by Quota", hole=0.4)
    chart_col2.plotly_chart(fig2, use_container_width=True)

# College-wise Courses
if not df_course.empty and "College" in df_course.columns:
    col_course_count = df_course["College"].value_counts().reset_index()
    col_course_count.columns = ["College", "Count"]
    fig3 = px.bar(col_course_count, x="College", y="Count", color="Count", title="Courses per College")
    st.plotly_chart(fig3, use_container_width=True)

# -------------------------
# Pages (Tabs)
# -------------------------
st.subheader("📚 Data Tables")
for name, df in [("CourseMaster", df_course), ("StudentDetails", df_student), ("CollegeMaster", df_col), ("SeatMatrix", df_seat)]:
    with st.expander(f"{name} Preview"):
        st.dataframe(df)
        download_button_for_df(df, f"{name}_{year}_{program}")

# Main Tabs for CRUD + Uploads
st.title("Admission Management System")
st.caption(f"Year: **{year}**, Program: **{program}")

tabs = st.tabs(["CourseMaster", "CollegeMaster", "CollegeCourseMaster", "SeatMatrix", "StudentDetails", "Allotment", "Vacancy"])

# ---------- CourseMaster (year+program scoped) ----------
with tabs[0]:
    st.subheader("📚 CourseMaster")
    df_course = load_table("CourseMaster", year, program)

    uploaded_course_key = f"upl_CourseMaster_{year}_{program}"
    uploaded = st.file_uploader("Upload CourseMaster (Excel/CSV)", type=["xlsx", "xls", "csv"], key=uploaded_course_key)
    if uploaded:
        try:
            if uploaded.name.lower().endswith('.csv'):
                df_new = pd.read_csv(uploaded)
            else:
                df_new = pd.read_excel(uploaded)
            df_new = clean_columns(df_new)
            df_new["AdmissionYear"] = year
            df_new["Program"] = program
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
        key=f"data_editor_CourseMaster_{year}_{program}",
    )
    if st.button("💾 Save CourseMaster (Year+Program Scoped)", key=f"save_CourseMaster_{year}_{program}"):
        if "AdmissionYear" not in edited_course.columns:
            edited_course["AdmissionYear"] = year
        if "Program" not in edited_course.columns:
            edited_course["Program"] = program
        save_table("CourseMaster", edited_course, replace_where={"AdmissionYear": year, "Program": program})
        df_course = load_table("CourseMaster", year, program)

# ---------- CollegeMaster (global) ----------
with tabs[1]:
    st.subheader("🏫 CollegeMaster")
    df_col = load_table("CollegeMaster")
    uploaded = st.file_uploader("Upload CollegeMaster (Excel/CSV)", type=["xlsx", "xls", "csv"], key="upl_CollegeMaster_global")
    if uploaded:
        try:
            if uploaded.name.lower().endswith('.csv'):
                df_new = pd.read_csv(uploaded)
            else:
                df_new = pd.read_excel(uploaded)
            df_new = clean_columns(df_new)
            save_table("CollegeMaster", df_new, replace_where=None)
            df_col = load_table("CollegeMaster")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    df_col_filtered = filter_and_sort_dataframe(df_col, "CollegeMaster")
    edited_col = st.data_editor(df_col_filtered, num_rows="dynamic", use_container_width=True, key="data_editor_CollegeMaster_global")
    if st.button("💾 Save College Master", key="save_CollegeMaster_global"):
        save_table("CollegeMaster", edited_col, replace_where=None)
        df_col = load_table("CollegeMaster")

    with st.expander("🗑️ Danger Zone: CollegeMaster"):
        st.error("⚠️ This action will permanently delete ALL CollegeMaster data!")
        if st.button("🚨 Flush All CollegeMaster Data", key="flush_col_btn"):
            st.session_state["confirm_flush_col"] = True
        if st.session_state.get("confirm_flush_col", False):
            confirm = st.checkbox("Yes, I understand this will delete all CollegeMaster permanently.", key="flush_col_confirm")
            if confirm:
                save_table("CollegeMaster", pd.DataFrame(), replace_where=None)
                st.success("✅ All CollegeMaster data cleared!")
                st.session_state["confirm_flush_col"] = False
                st.experimental_rerun()

# ---------- CollegeCourseMaster (global) ----------
with tabs[2]:
    st.subheader("🏫📚 CollegeCourseMaster")
    df_cc = load_table("CollegeCourseMaster")
    uploaded = st.file_uploader("Upload CollegeCourseMaster (Excel/CSV)", type=["xlsx", "xls", "csv"], key="upl_CollegeCourseMaster_global")
    if uploaded:
        try:
            if uploaded.name.lower().endswith('.csv'):
                df_new = pd.read_csv(uploaded)
            else:
                df_new = pd.read_excel(uploaded)
            df_new = clean_columns(df_new)
            save_table("CollegeCourseMaster", df_new, replace_where=None)
            df_cc = load_table("CollegeCourseMaster")
        except Exception as e:
            st.error(f"Error reading file: {e}")

    df_cc_filtered = filter_and_sort_dataframe(df_cc, "CollegeCourseMaster")
    edited_cc = st.data_editor(df_cc_filtered, num_rows="dynamic", use_container_width=True, key=f"data_editor_CollegeCourseMaster_global")
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
    st.subheader("SeatMatrix")
    df_seat = load_table("SeatMatrix", year, program)
    uploaded = st.file_uploader("Upload SeatMatrix (Excel/CSV)", type=["xlsx", "xls", "csv"], key=f"upl_SeatMatrix_{year}_{program}")
    if uploaded:
        try:
            if uploaded.name.lower().endswith('.csv'):
                df_new = pd.read_csv(uploaded)
            else:
                df_new = pd.read_excel(uploaded)
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
    edited_seat = st.data_editor(df_seat_filtered, num_rows="dynamic", use_container_width=True, key=f"data_editor_SeatMatrix_{year}_{program}")
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
            if uploaded.name.lower().endswith('.csv'):
                df_new = pd.read_csv(uploaded)
            else:
                df_new = pd.read_excel(uploaded)
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
    edited_stu = st.data_editor(df_stu_filtered, num_rows="dynamic", use_container_width=True, key=f"data_editor_StudentDetails_{year}_{program}")
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

# ---------- Vacancy (skeleton) ----------
with tabs[6]:
    st.subheader("Vacancy (skeleton)")
    st.info("Vacancy calculation will be added later. Upload/edit SeatMatrix and Allotment to prepare for vacancy calculation.")

# Footer
st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

































