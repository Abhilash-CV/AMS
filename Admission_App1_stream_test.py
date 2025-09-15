# admission_app_stream_fixed.py
import io
import re
import sqlite3
from datetime import datetime


import pandas as pd
import plotly.express as px
import streamlit as st

import streamlit as st
import hashlib

# --- Password Hashing ---
USER_CREDENTIALS = {
    "Admin": hashlib.sha256("admin123".encode()).hexdigest(),
    "user1": hashlib.sha256("password1".encode()).hexdigest(),
}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Session State Initialization ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "login_error" not in st.session_state:
    st.session_state.login_error = ""

import streamlit as st
import base64

# Helper function to convert image to base64 (so it works everywhere)
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()


# --- Login Action ---
def do_login(username, password):
    hashed = hash_password(password)
    if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == hashed:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.login_error = ""
    else:
        st.session_state.login_error = "❌ Invalid username or password"

# --- Logout Action ---
def do_logout():
    st.session_state.logged_in = False
    st.session_state.username = ""

# --- Login Page ---
def login_page():
    col1, col2, col3 = st.columns([2, 5, 3])

    with col3:  # Right side (login form)
        st.header("🔐 Login")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.session_state.login_error:
            st.error(st.session_state.login_error)

        st.button("Login", key="login_btn", on_click=do_login, args=(username, password))

    with col2:  # Middle column (image)
        #st.image("images/cee.png", width=300)  # Adjust width as needed
        img_base64 = get_base64_image("images/cee1.png")
        st.markdown(
            f"""
            <style>
            .spin-image {{
                animation: spin 4s linear infinite;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            </style>
            <img class="spin-image" src="data:image/png;base64,{img_base64}" width="300">
            """,
            unsafe_allow_html=True
        )









# -------------------------
# Configuration
# -------------------------
DB_FILE = "admission.db"
PROGRAM_OPTIONS = ["LLB5", "LLB3", "PGN", "PG Homeo", "Engineering"]
YEAR_OPTIONS = ["2023", "2024", "2025", "2026"]

st.set_page_config(
    page_title="Admission Management System",
    layout="wide",
    page_icon="🏫",
)
# Initialize global dfs to avoid NameError
df_seat = pd.DataFrame()
df_course = pd.DataFrame()
df_Candidate = pd.DataFrame()
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
            conn.commit()
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
        for k, v in replace_where.items():
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

import uuid

def filter_and_sort_dataframe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    if df is None or df.empty:
        st.write(f"⚠️ No data available for {table_name}")
        return df

    year = st.session_state.get("year", "")
    program = st.session_state.get("program", "")
    base_key = f"{table_name}_{year}_{program}"

    with st.expander(f"🔎 Filter & Sort ({table_name})", expanded=False):
        # --- Global search ---
        search_key = f"{base_key}_search_{uuid.uuid4().hex[:6]}"  # unique key each time
        search_text = st.text_input(
            f"🔍 Global Search ({table_name})",
            value="",
            key=search_key
        ).lower().strip()

        mask = pd.Series(True, index=df.index)
        if search_text:
            mask &= df.apply(lambda row: row.astype(str).str.lower().str.contains(search_text).any(), axis=1)

        # --- Column-wise filters ---
        for col in df.columns:
            unique_vals = sorted([str(x) for x in df[col].dropna().unique()])
            options = ["(All)"] + unique_vals

            col_key = f"{base_key}_{col}_filter_{uuid.uuid4().hex[:6]}"  # unique key
            selected_vals = st.multiselect(
                f"Filter {col}",
                options,
                default=["(All)"],
                key=col_key
            )

            if "(All)" not in selected_vals:
                mask &= df[col].astype(str).isin(selected_vals)

        filtered = df[mask]

    filtered = filtered.reset_index(drop=True)
    filtered.index = filtered.index + 1

    total = len(df)
    count = len(filtered)
    percent = (count / total * 100) if total > 0 else 0
    st.markdown(f"**📊 Showing {count} of {total} records ({percent:.1f}%)**")

    return filtered


    return filtered
if not st.session_state.logged_in:
    login_page()
else:
    #st.sidebar.write(f"👋 Logged in as: {st.session_state.username.capitalize()}!")
    #st.success(f"👋 Welcome, {st.session_state.username.capitalize}!")
    st.success(f"👋 Welcome, {st.session_state.username.capitalize()}!")
    st.button("Logout", on_click=do_logout)
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
       # ["Dashboard", "Course Master", "College Master", "College Course Master", "Seat Matrix", "Candidate Details", "Allotment", "Vacancy"],
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
            ["Dashboard", "Course Master", "College Master", "College Course Master",
             "Seat Matrix", "CandidateDetails", "Allotment", "Vacancy"],
            icons=[
                "house",          # Dashboard
                "journal-bookmark",  # Course Master
                "buildings",      # ✅ Valid icon for CollegeMaster
                "collection",     # CollegeCourseMaster
                "grid-3x3-gap",   # SeatMatrix
                "people",         # CandidateDetails
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
        df_course = load_table("Course Master", year, program)
        df_col = load_table("College Master")
        df_Candidate = load_table("Candidate Details", year, program)
        df_seat = load_table("Seat Matrix", year, program)
    
        st.title("🎯 Admission Dashboard")
        st.markdown(f"**Year:** {year} | **Program:** {program}")
    
        # --- KPI Cards ---
        st.subheader("📊 Key Metrics")
        kpi_cols = st.columns(4)
    
        total_courses = len(df_course)
        total_colleges = len(df_col)
        total_Candidates = len(df_Candidate)
        total_seats = int(df_seat["Seats"].sum()) if not df_seat.empty and "Seats" in df_seat.columns else 0
    
        kpi_data = [
            {"icon": "🏫", "title": "Courses", "value": total_courses, "color": "#FF6B6B"},
            {"icon": "🏛️", "title": "Colleges", "value": total_colleges, "color": "#4ECDC4"},
            {"icon": "👨‍🎓", "title": "Candidates", "value": total_Candidates, "color": "#556270"},
            {"icon": "💺", "title": "Seats", "value": total_seats, "color": "#C7F464"},
        ]
    
        # Function to render small colored KPI card
        def kpi_card(col, icon, title, value, color="#000000"):
            col.markdown(
                f"""
                <div style="
                    background-color:{color}40;  /* light transparent background */
                    padding:8px;
                    border-radius:10px;
                    text-align:center;
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
    
        # Candidates by Quota (Mini Pie)
        if not df_Candidate.empty and "Quota" in df_Candidate.columns:
            quota_count = df_Candidate["Quota"].value_counts().reset_index()
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
       # st.subheader("📋 Quick Overview")
        #summary_df = pd.DataFrame({
            #"Metric": ["Courses", "Colleges", "Candidates", "Seats"],
           # "Count": [total_courses, total_colleges, total_Candidates, total_seats]
      #  })
       # st.table(summary_df)
    
    
    elif page == "Course Master":
        st.header("📚 Course Master")
        df_course = load_table("Course Master", year, program)
        uploaded = st.file_uploader("Upload Course Master", type=["xlsx", "xls", "csv"])
        if uploaded:
            df_new = pd.read_excel(uploaded) if uploaded.name.endswith(".xlsx") else pd.read_csv(uploaded)
            df_new = clean_columns(df_new)
            df_new["AdmissionYear"] = year
            df_new["Program"] = program
            save_table("Course Master", df_new, replace_where={"AdmissionYear": year, "Program": program})
            df_course = load_table("Course Master", year, program)
        download_button_for_df(df_course, f"Course Master_{year}_{program}")
        df_course_filtered = filter_and_sort_dataframe(df_course, "Course Master")
        edited_course = st.data_editor(df_course_filtered, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Save Course Master"):
            if "AdmissionYear" not in edited_course.columns:
                edited_course["AdmissionYear"] = year
            if "Program" not in edited_course.columns:
                edited_course["Program"] = program
            save_table("Course Master", edited_course, replace_where={"AdmissionYear": year, "Program": program})
    
    elif page == "Seat Matrix":
        st.header("📊 Seat Matrix")
    
        # Create sub-tabs for Government, Private, Minority, and All
        seat_tabs = st.tabs(["🏛️ Government", "🏢 Private", "🕌 Minority", "📑 All Seat Types"])
    
        for seat_type, tab in zip(["Government", "Private", "Minority"], seat_tabs[:3]):
            with tab:
                st.subheader(f"{seat_type} Seat Matrix")
    
                # Load only selected seat type
                df_seat = load_table("Seat Matrix", year, program)
                df_seat = df_seat[df_seat["SeatType"] == seat_type] if "SeatType" in df_seat.columns else df_seat
    
                # Upload
                uploaded = st.file_uploader(f"Upload {seat_type} Seat Matrix", type=["xlsx", "xls", "csv"], key=f"upl_seat_{seat_type}_{year}_{program}")
                if uploaded:
                    df_new = pd.read_excel(uploaded) if uploaded.name.endswith(".xlsx") else pd.read_csv(uploaded)
                    df_new = clean_columns(df_new)
                    df_new["AdmissionYear"] = year
                    df_new["Program"] = program
                    df_new["SeatType"] = seat_type  # Add seat type column
                    save_table("Seat Matrix", df_new, replace_where={"AdmissionYear": year, "Program": program, "SeatType": seat_type})
                    df_seat = load_table("Seat Matrix", year, program)
                    df_seat = df_seat[df_seat["SeatType"] == seat_type]
    
                # Download + Edit
                download_button_for_df(df_seat, f"SeatMatrix_{seat_type}_{year}_{program}")
                df_seat_filtered = filter_and_sort_dataframe(df_seat, "Seat Matrix")
                edited_seat = st.data_editor(df_seat_filtered, num_rows="dynamic", use_container_width=True, key=f"data_editor_seat_{seat_type}_{year}_{program}")
    
                # Save
                if st.button(f"💾 Save {seat_type} Seat Matrix", key=f"save_seat_matrix_{seat_type}_{year}_{program}"):
                    if "AdmissionYear" not in edited_seat.columns:
                        edited_seat["AdmissionYear"] = year
                    if "Program" not in edited_seat.columns:
                        edited_seat["Program"] = program
                    if "SeatType" not in edited_seat.columns:
                        edited_seat["SeatType"] = seat_type
                    save_table("Seat Matrix", edited_seat, replace_where={"AdmissionYear": year, "Program": program, "SeatType": seat_type})
                    st.success(f"✅ {seat_type} Seat Matrix saved!")
                    st.rerun()
    
                # Flush Danger Zone
                with st.expander(f"🗑️ Danger Zone: {seat_type} Seat Matrix"):
                    st.error(f"⚠️ This will delete {seat_type} Seat Matrix data for AdmissionYear={year} & Program={program}!")
                    confirm_key = f"flush_confirm_seat_{seat_type}_{year}_{program}"
                    if confirm_key not in st.session_state:
                        st.session_state[confirm_key] = False
    
                    st.session_state[confirm_key] = st.checkbox(
                        f"Yes, delete {seat_type} Seat Matrix permanently.",
                        value=st.session_state[confirm_key],
                        key=f"flush_seat_confirm_{seat_type}_{year}_{program}"
                    )
    
                    if st.session_state[confirm_key]:
                        if st.button(f"🚨 Flush {seat_type} Seat Matrix", key=f"flush_seat_btn_{seat_type}_{year}_{program}"):
                            save_table("Seat Matrix", pd.DataFrame(), replace_where={"AdmissionYear": year, "Program": program, "SeatType": seat_type})
                            st.success(f"✅ {seat_type} Seat Matrix cleared!")
                            st.session_state[confirm_key] = False
                            st.rerun()
    
        # ---------- ALL SEAT TYPES TAB ----------
        with seat_tabs[3]:
            st.subheader("📑 All Seat Types (Combined View)")
            df_all = load_table("Seat Matrix", year, program)
    
            # Show all data without filtering SeatType
            download_button_for_df(df_all, f"SeatMatrix_ALL_{year}_{program}")
            df_all_filtered = filter_and_sort_dataframe(df_all, "Seat Matrix")
            edited_all = st.data_editor(df_all_filtered, num_rows="dynamic", use_container_width=True, key=f"data_editor_seat_all_{year}_{program}")
    
            if st.button("💾 Save All Seat Types", key=f"save_seat_matrix_all_{year}_{program}"):
                if "AdmissionYear" not in edited_all.columns:
                    edited_all["AdmissionYear"] = year
                if "Program" not in edited_all.columns:
                    edited_all["Program"] = program
                # Ensure SeatType exists for all rows (optional but recommended)
                if "SeatType" not in edited_all.columns:
                    st.warning("⚠️ 'SeatType' column missing! Please add it manually before saving.")
                else:
                    save_table("Seat Matrix", edited_all, replace_where={"AdmissionYear": year, "Program": program})
                    st.success("✅ All Seat Types saved successfully!")
                    st.rerun()
    
            with st.expander("🗑️ Danger Zone: ALL Seat Types"):
                st.error(f"⚠️ This will delete ALL Seat Matrix data for AdmissionYear={year} & Program={program}!")
                confirm_key = f"flush_confirm_seat_all_{year}_{program}"
                if confirm_key not in st.session_state:
                    st.session_state[confirm_key] = False
    
                st.session_state[confirm_key] = st.checkbox(
                    f"Yes, delete ALL Seat Types permanently.",
                    value=st.session_state[confirm_key],
                    key=f"flush_seat_confirm_all_{year}_{program}"
                )
    
                if st.session_state[confirm_key]:
                    if st.button("🚨 Flush ALL Seat Matrix", key=f"flush_seat_btn_all_{year}_{program}"):
                        save_table("Seat Matrix", pd.DataFrame(), replace_where={"AdmissionYear": year, "Program": program})
                        st.success(f"✅ ALL Seat Types cleared for AdmissionYear={year} & Program={program}!")
                        st.session_state[confirm_key] = False
                        st.rerun()

    
    elif page == "CandidateDetails":
        st.header("👨‍🎓 Candidate Details")
        
        # Load data
        df_stu = load_table("Candidate Details", year, program)
    
        # File uploader
        uploaded = st.file_uploader("Upload Candidate Details", type=["xlsx", "xls", "csv"])
        if uploaded:
            df_new = pd.read_excel(uploaded) if uploaded.name.endswith(".xlsx") else pd.read_csv(uploaded)
            df_new = clean_columns(df_new)
            df_new["AdmissionYear"] = year
            df_new["Program"] = program
            save_table("CandidateDetails", df_new, replace_where={"AdmissionYear": year, "Program": program})
            df_stu = load_table("Candidate Details", year, program)
    
        # Download button
        download_button_for_df(df_stu, f"Candidate Details_{year}_{program}")
    
        # Tabs for sub-views
        tab1, tab2, tab3, tab4 = st.tabs(["All Candidates", "By Quota", "By College", "By Program"])
    
        with tab1:
            st.subheader("All Candidates")
            st.data_editor(df_stu, num_rows="dynamic", use_container_width=True)
    
        with tab2:
            st.subheader("By Quota")
            if "Quota" in df_stu.columns:
                quota_count = df_stu["Quota"].value_counts().reset_index()
                quota_count.columns = ["Quota", "Count"]
                st.table(quota_count)
                fig = px.pie(
                    quota_count,
                    names="Quota",
                    values="Count",
                    title="Candidate Distribution by Quota",
                    hole=0.4
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Quota column not found!")
    
        with tab3:
            st.subheader("By College")
            if "College" in df_stu.columns:
                college_count = df_stu["College"].value_counts().reset_index()
                college_count.columns = ["College", "Count"]
                st.table(college_count)
                fig = px.bar(
                    college_count,
                    x="College",
                    y="Count",
                    color="Count",
                    title="Candidates per College"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("College column not found!")
    
        with tab4:
            st.subheader("By Program")
            if "Program" in df_stu.columns:
                program_count = df_stu["Program"].value_counts().reset_index()
                program_count.columns = ["Program", "Count"]
                st.table(program_count)
                fig = px.bar(
                    program_count,
                    x="Program",
                    y="Count",
                    color="Count",
                    title="Candidates per Program"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Program column not found!")
    
    
    
    elif page == "College Master":
        st.header("🏫 College Master")
        df_col = load_table("College Master")
        df_col_filtered = filter_and_sort_dataframe(df_col, "College Master")
        st.data_editor(df_col_filtered, num_rows="dynamic", use_container_width=True)
    
    elif page == "College Course Master":
        st.header("🏫📚 College Course Master")
        df_cc = load_table("College Course Master")
        uploaded = st.file_uploader("Upload CollegeC ourseMaster", type=["xlsx", "xls", "csv"])
        if uploaded:
            df_new = pd.read_excel(uploaded) if uploaded.name.endswith(".xlsx") else pd.read_csv(uploaded)
            df_new = clean_columns(df_new)
            df_new["AdmissionYear"] = year
            df_new["Program"] = program
            save_table("CollegeCourse Master", df_new, replace_where={"AdmissionYear": year, "Program": program})
            df_cc = load_table("College Course Master", year, program)
        download_button_for_df(df_cc, f"College Course Master{year}_{program}")
        df_cc_filtered = filter_and_sort_dataframe(df_cc, "College Course Master")
        edited_cc = st.data_editor(df_cc_filtered, num_rows="dynamic", use_container_width=True)
        if st.button("💾 Save College Course Master"):
            if "AdmissionYear" not in edited_cc.columns:
                edited_cc["AdmissionYear"] = year
            if "Program" not in edited_cc.columns:
                edited_cc["Program"] = program
            save_table("College Course Master", edited_cc, replace_where={"AdmissionYear": year, "Program": program})
        
    
    elif page == "Allotment":
        st.header("Allotment")
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
    
    # Candidates by Quota
    if not df_Candidate.empty and "Quota" in df_Candidate.columns:
        quota_count = df_Candidate["Quota"].value_counts().reset_index()
        quota_count.columns = ["Quota", "Count"]
        fig2 = px.pie(quota_count, names="Quota", values="Count", title="Candidate Distribution by Quota", hole=0.4)
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
    for name, df in [("Course Master", df_course), ("Candidate Details", df_Candidate), ("College Master", df_col), ("Seat Matrix", df_seat)]:
        with st.expander(f"{name} Preview"):
            st.dataframe(df)
            download_button_for_df(df, f"{name}_{year}_{program}")
    
    # Main Tabs for CRUD + Uploads
    st.title("Admission Management System")
    st.caption(f"Year: **{year}**, Program: **{program}")
    
    tabs = st.tabs(["Course Master", "College Master", "College Course Master", "Seat Matrix", "Candidate Details", "Allotment", "Vacancy"])
    
    # ---------- CourseMaster (year+program scoped) ----------
    with tabs[0]:
        st.subheader("📚 Course Master")
    
        # Load table data for selected year & program
        df_course = load_table("Course Master", year, program)
    
        # File uploader
        upload_key = f"upl_course_master_{year}_{program}"
        uploaded = st.file_uploader(
            "Upload Course Master (Excel/CSV)",
            type=["xlsx", "xls", "csv"],
            key=upload_key
        )
        if uploaded:
            try:
                if uploaded.name.lower().endswith('.csv'):
                    df_new = pd.read_csv(uploaded)
                else:
                    df_new = pd.read_excel(uploaded)
    
                df_new = clean_columns(df_new)
                df_new["AdmissionYear"] = year
                df_new["Program"] = program
    
                # Save with replacement for same year+program
                save_table("Course Master", df_new, replace_where={"AdmissionYear": year, "Program": program})
                df_course = load_table("Course Master", year, program)
                st.success("✅ Course Master uploaded successfully!")
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
        # Download + Filter + Edit
        download_button_for_df(df_course, f"Course Master_{year}_{program}")
        st.caption(f"Showing rows for **AdmissionYear={year} & Program={program}**")
    
        df_course_filtered = filter_and_sort_dataframe(df_course, "Course Master")
        edited_course = st.data_editor(
            df_course_filtered,
            num_rows="dynamic",
            use_container_width=True,
            key=f"data_editor_course_master_{year}_{program}",
        )
    
        if st.button("💾 Save Course Master", key=f"save_course_master_{year}_{program}"):
            if "AdmissionYear" not in edited_course.columns:
                edited_course["AdmissionYear"] = year
            if "Program" not in edited_course.columns:
                edited_course["Program"] = program
            save_table("Course Master", edited_course, replace_where={"AdmissionYear": year, "Program": program})
            st.success("✅ Course Master saved!")
            df_course = load_table("Course Master", year, program)
    # ---------- Course Master Danger Zone ----------
        with st.expander("🗑️ Danger Zone: Course Master"):
            st.error("⚠️ This action will permanently delete ALL Course Master data!")
            confirm_key = f"flush_confirm_course_{year}_{program}"
            if confirm_key not in st.session_state:
                st.session_state[confirm_key] = False
        
            st.session_state[confirm_key] = st.checkbox(
                "Yes, I understand this will delete all Course Master permanently.",
                value=st.session_state[confirm_key],
                key=f"flush_course_confirm_{year}_{program}"
            )
        
            if st.session_state[confirm_key]:
                if st.button("🚨 Flush All Course Master Data", key=f"flush_course_btn_{year}_{program}"):
                    save_table("Course Master", pd.DataFrame(), replace_where=None)
                    st.success("✅ All Course Master data cleared!")
                    st.session_state[confirm_key] = False
                    st.rerun()



    

    
        
        
    # ---------- CollegeMaster (global) ----------
    with tabs[1]:
        st.subheader("🏫 College Master")
        df_col = load_table("College Master")
        uploaded = st.file_uploader("Upload College Master (Excel/CSV)", type=["xlsx", "xls", "csv"], key="upl_CollegeMaster_global")
        if uploaded:
            try:
                if uploaded.name.lower().endswith('.csv'):
                    df_new = pd.read_csv(uploaded)
                else:
                    df_new = pd.read_excel(uploaded)
                df_new = clean_columns(df_new)
                save_table("College Master", df_new, replace_where=None)
                df_col = load_table("College Master")
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
        df_col_filtered = filter_and_sort_dataframe(df_col, "College Master")
        edited_col = st.data_editor(df_col_filtered, num_rows="dynamic", use_container_width=True, key="data_editor_CollegeMaster_global")
        if st.button("💾 Save College Master", key="save_CollegeMaster_global"):
            save_table("College Master", edited_col, replace_where=None)
            df_col = load_table("College Master")
    
        with st.expander("🗑️ Danger Zone: College Master"):
            st.error("⚠️ This action will permanently delete ALL College Master data!")
            confirm_key = "flush_confirm_college"
            if confirm_key not in st.session_state:
                st.session_state[confirm_key] = False
        
            st.session_state[confirm_key] = st.checkbox(
                "Yes, I understand this will delete all College Master permanently.",
                value=st.session_state[confirm_key],
                key="flush_college_confirm"
            )
        
            if st.session_state[confirm_key]:
                if st.button("🚨 Flush All College Master Data", key="flush_college_btn"):
                    save_table("College Master", pd.DataFrame(), replace_where=None)
                    st.success("✅ All College Master data cleared!")
                    st.session_state[confirm_key] = False
                    st.rerun()

    # ---------- College Course Master (global) ----------
    with tabs[2]:
        st.subheader("🏫📚 College Course Master")
        df_cc = load_table("College Course Master")
        uploaded = st.file_uploader("Upload College Course Master (Excel/CSV)", type=["xlsx", "xls", "csv"], key="upl_CollegeCourseMaster_global")
        if uploaded:
            try:
                if uploaded.name.lower().endswith('.csv'):
                    df_new = pd.read_csv(uploaded)
                else:
                    df_new = pd.read_excel(uploaded)
                df_new = clean_columns(df_new)
                save_table("College Course Master", df_new, replace_where=None)
                df_cc = load_table("College Course Master")
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
        df_cc_filtered = filter_and_sort_dataframe(df_cc, "College Course Master")
        edited_cc = st.data_editor(df_cc_filtered, num_rows="dynamic", use_container_width=True, key=f"data_editor_CollegeCourseMaster_global")
        if st.button("💾 Save College Course Master", key="save_CollegeCourseMaster_global"):
            save_table("College Course Master", edited_cc, replace_where=None)
            df_cc = load_table("College Course Master")
    
        with st.expander("🗑️ Danger Zone: College Course Master"):
            st.error("⚠️ This action will permanently delete ALL College Course Master data!")
            confirm_key = "flush_confirm_college_course"
            if confirm_key not in st.session_state:
                st.session_state[confirm_key] = False
        
            st.session_state[confirm_key] = st.checkbox(
                "Yes, I understand this will delete all College Course Master permanently.",
                value=st.session_state[confirm_key],
                key="flush_college_course_confirm"
            )
        
            if st.session_state[confirm_key]:
                if st.button("🚨 Flush All College Course Master Data", key="flush_college_course_btn"):
                    save_table("College Course Master", pd.DataFrame(), replace_where=None)
                    st.success("✅ All College Course Master data cleared!")
                    st.session_state[confirm_key] = False
                    st.rerun()

    
    # ---------- SeatMatrix (year+program scoped) ----------
    with tabs[3]:
        st.subheader("📊 Seat Matrix")
    
        # Load data
        df_seat = load_table("Seat Matrix", year, program)
    
        # Upload Section
        upload_key = f"upl_seat_matrix_{year}_{program}"
        uploaded = st.file_uploader(
            "Upload Seat Matrix (Excel/CSV)",
            type=["xlsx", "xls", "csv"],
            key=upload_key
        )
        if uploaded:
            try:
                if uploaded.name.lower().endswith('.csv'):
                    df_new = pd.read_csv(uploaded)
                else:
                    df_new = pd.read_excel(uploaded)
    
                df_new = clean_columns(df_new)
                df_new["AdmissionYear"] = year
                df_new["Program"] = program
    
                save_table("Seat Matrix", df_new, replace_where={"AdmissionYear": year, "Program": program})
                st.success("✅ Seat Matrix uploaded successfully!")
                st.rerun()  # <-- force refresh after upload
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
        # Download & Edit
        download_button_for_df(df_seat, f"SeatMatrix_{year}_{program}")
        st.caption(f"Showing rows for **AdmissionYear={year} & Program={program}**")
    
        df_seat_filtered = filter_and_sort_dataframe(df_seat, "Seat Matrix")
        edited_seat = st.data_editor(
            df_seat_filtered,
            num_rows="dynamic",
            use_container_width=True,
            key=f"data_editor_seat_matrix_{year}_{program}"
        )
    
        if st.button("💾 Save Seat Matrix", key=f"save_seat_matrix_{year}_{program}"):
            if "AdmissionYear" not in edited_seat.columns:
                edited_seat["AdmissionYear"] = year
            if "Program" not in edited_seat.columns:
                edited_seat["Program"] = program
    
            save_table("Seat Matrix", edited_seat, replace_where={"AdmissionYear": year, "Program": program})
            st.success("✅ Seat Matrix saved successfully!")
            st.rerun()  # <-- force refresh after save
    
        with st.expander("🗑️ Danger Zone: Seat Matrix"):
            st.error("⚠️ This action will permanently delete ALL Seat Matrix data!")
            confirm_key = f"flush_confirm_seat_{year}_{program}"
            if confirm_key not in st.session_state:
                st.session_state[confirm_key] = False
        
            st.session_state[confirm_key] = st.checkbox(
                "Yes, I understand this will delete all Seat Matrix permanently.",
                value=st.session_state[confirm_key],
                key=f"flush_seat_confirm_{year}_{program}"
            )
        
            if st.session_state[confirm_key]:
                if st.button("🚨 Flush All Seat Matrix Data", key=f"flush_seat_btn_{year}_{program}"):
                    save_table("Seat Matrix", pd.DataFrame(), replace_where=None)
                    st.success("✅ All Seat Matrix data cleared!")
                    st.session_state[confirm_key] = False
                    st.rerun()


    
    # ---------- CandidateDetails (year+program scoped) ----------
    with tabs[4]:
        st.subheader("👨‍🎓 Candidate Details (Year+Program)")
        df_stu = load_table("Candidate Details", year, program)
        uploaded = st.file_uploader("Upload CandidateDetails (Excel/CSV)", type=["xlsx", "xls", "csv"], key=f"upl_CandidateDetails_{year}_{program}")
        if uploaded:
            try:
                if uploaded.name.lower().endswith('.csv'):
                    df_new = pd.read_csv(uploaded)
                else:
                    df_new = pd.read_excel(uploaded)
                df_new = clean_columns(df_new)
                df_new["AdmissionYear"] = year
                df_new["Program"] = program
                save_table("Candidate Details", df_new, replace_where={"AdmissionYear": year, "Program": program})
                df_stu = load_table("Candidate Details", year, program)
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
        download_button_for_df(df_stu, f"CandidateDetails_{year}_{program}")
        st.write(f"Showing rows for AdmissionYear={year} & Program={program}")
        df_stu_filtered = filter_and_sort_dataframe(df_stu, "CandidateDetails")
        edited_stu = st.data_editor(df_stu_filtered, num_rows="dynamic", use_container_width=True, key=f"data_editor_CandidateDetails_{year}_{program}")
        if st.button("💾 Save CandidateDetails (Year+Program Scoped)", key=f"save_CandidateDetails_{year}_{program}"):
            if "AdmissionYear" not in edited_stu.columns:
                edited_stu["AdmissionYear"] = year
            if "Program" not in edited_stu.columns:
                edited_stu["Program"] = program
            save_table("CandidateDetails", edited_stu, replace_where={"AdmissionYear": year, "Program": program})
            df_stu = load_table("CandidateDetails", year, program)
    
        with st.expander("🗑️ Danger Zone: Candidate Details"):
            st.error("⚠️ This action will permanently delete ALL Candidate Details data!")
            confirm_key = f"flush_confirm_candidate_{year}_{program}"
            if confirm_key not in st.session_state:
                st.session_state[confirm_key] = False
        
            st.session_state[confirm_key] = st.checkbox(
                "Yes, I understand this will delete all Candidate Details permanently.",
                value=st.session_state[confirm_key],
                key=f"flush_candidate_confirm_{year}_{program}"
            )
        
            if st.session_state[confirm_key]:
                if st.button("🚨 Flush All Candidate Details Data", key=f"flush_candidate_btn_{year}_{program}"):
                    save_table("Candidate Details", pd.DataFrame(), replace_where=None)
                    st.success("✅ All Candidate Details data cleared!")
                    st.session_state[confirm_key] = False
                    st.rerun()
    # ---------- Allotment (global) ----------
    with tabs[5]:
        st.subheader("Allotment ")
        df_allot = load_table("Allotment")
        if df_allot.empty:
            st.info("No allotment data found yet.")
        else:
            download_button_for_df(df_allot, "Allotment")
            st.dataframe(df_allot, use_container_width=True)
    
    # ---------- Vacancy (skeleton) ----------
    with tabs[6]:
        st.subheader("Vacancy ")
        st.info("Vacancy calculation will be added later. Upload/edit SeatMatrix and Allotment to prepare for vacancy calculation.")
    
    # Footer





