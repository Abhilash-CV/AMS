# admission_app_stream.py
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
#@st.cache_resource
@st.cache
def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

# -------------------------
# Utility: clean column names
# -------------------------
def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names:
      - trim
      - replace whitespace/colons/other non-word chars with '_'
      - guarantee unique names by suffixing duplicates
    """
    if df is None:
        return pd.DataFrame()
    cols = []
    seen = {}
    for c in df.columns:
        s = str(c).strip()
        # replace any non-alphanumeric or underscore with underscore
        s = re.sub(r"[^\w]", "_", s)
        if s == "":
            s = "Unnamed"
        # ensure uniqueness
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
# Load table (safe)
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
def upload_and_preview(table_name: str, existing_df: pd.DataFrame, year_based: bool=False):
    """
    Show uploader; parse file into DataFrame; ensure AdmissionYear/Program if year_based.
    Returns DataFrame (either existing_df if no upload, or uploaded DataFrame).
    """
    uploaded = st.file_uploader(f"Upload {table_name} (Excel/CSV)", type=["xlsx", "csv"], key=f"upl_{table_name}")
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
    # for year-based table ensure AdmissionYear & Program exist
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
# Download helper (excel)
# -------------------------
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
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# -------------------------
# Save table: robust & safe
# -------------------------
def save_table(table: str, df: pd.DataFrame, replace_where: dict = None):
    """
    Save DataFrame to SQLite.
    - If replace_where is provided (e.g. {"AdmissionYear": "2025", "Program": "LLB5"}):
        -> delete rows in table matching replace_where, then insert rows from df (so other rows remain).
        -> if table doesn't exist it will be created.
        -> if df is empty -> delete matching rows only.
    - If replace_where is None:
        -> overwrite entire table (drop & recreate to match df schema) if df non-empty.
        -> if df empty -> delete all rows from table (if exists).
    """
    conn = get_conn()
    cur = conn.cursor()
    df = clean_columns(df) if df is not None else pd.DataFrame()

    # If replace_where: delete matching rows first, then insert df rows (if any).
    if replace_where:
        # Ensure table exists or create with df schema if df present
        if not df.empty:
            # create if not exists using df schema
            col_defs = []
            for col, dtype in zip(df.columns, df.dtypes):
                if "int" in str(dtype):
                    t = "INTEGER"
                elif "float" in str(dtype):
                    t = "REAL"
                else:
                    t = "TEXT"
                col_defs.append(f'"{col}" {t}')
            create_stmt = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)})'
            cur.execute(create_stmt)

        # build where clause
        where_clause = " AND ".join([f'"{k}"=?' for k in replace_where.keys()])
        params = tuple(replace_where.values())

        # delete matching rows
        try:
            cur.execute(f'DELETE FROM "{table}" WHERE {where_clause}', params)
        except Exception:
            # table may not exist -> ignore
            pass

        # if df has rows, insert them
        if not df.empty:
            quoted_columns = [f'"{c}"' for c in df.columns]
            placeholders = ",".join(["?"] * len(df.columns))
            insert_stmt = f'INSERT INTO "{table}" ({",".join(quoted_columns)}) VALUES ({placeholders})'
            try:
                cur.executemany(insert_stmt, df.values.tolist())
            except Exception as e:
                st.error(f"Error inserting rows into {table}: {e}")
                conn.rollback()
                return
        conn.commit()
        st.success(f"Saved {len(df)} rows to {table} (replaced rows matching {replace_where})")
        return

    # else: overwrite entire table
    if df.empty:
        # delete all rows if table exists
        try:
            cur.execute(f'DELETE FROM "{table}"')
            conn.commit()
            st.success(f"Cleared all rows from {table}")
        except Exception:
            # table likely doesn't exist - nothing to do
            st.info(f"No table {table} existed; nothing saved.")
        return
    # drop and recreate table to match edited schema
    try:
        cur.execute(f'DROP TABLE IF EXISTS "{table}"')
    except Exception:
        pass

    col_defs = []
    for col, dtype in zip(df.columns, df.dtypes):
        if "int" in str(dtype):
            t = "INTEGER"
        elif "float" in str(dtype):
            t = "REAL"
        else:
            t = "TEXT"
        col_defs.append(f'"{col}" {t}')
    create_stmt = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)})'
    cur.execute(create_stmt)

    # insert rows
    quoted_columns = [f'"{c}"' for c in df.columns]
    placeholders = ",".join(["?"] * len(df.columns))
    insert_stmt = f'INSERT INTO "{table}" ({",".join(quoted_columns)}) VALUES ({placeholders})'
    try:
        cur.executemany(insert_stmt, df.values.tolist())
        conn.commit()
        st.success(f"Saved {len(df)} rows to {table}")
    except Exception as e:
        st.error(f"Error inserting into {table}: {e}")
        conn.rollback()
def filter_and_sort_dataframe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    if df.empty:
        st.write(f"⚠️ No data available for {table_name}")
        return df

    # --- Global + column filters inside expander ---
    with st.expander(f"🔎 Filter & Sort ({table_name})", expanded=False):
        search_text = st.text_input(
            f"🔍 Global Search ({table_name})",
            key=f"{table_name}_search"
        ).lower().strip()

        # --- Global text search mask ---
        global_mask = pd.Series([True] * len(df), index=df.index)
        if search_text:
            global_mask = df.apply(
                lambda row: row.astype(str).str.lower().str.contains(search_text).any(),
                axis=1
            )

        # --- Column-wise filters with "Select All" ---
        column_masks = []
        for col in df.columns:
            unique_vals = sorted(df[col].dropna().unique())
            options = ["(Select All)"] + list(unique_vals)

            selected_vals = st.multiselect(
                f"Filter {col}",
                options,
                default=["(Select All)"],
                key=f"{table_name}_{col}_filter"
            )

            # If not "Select All", create mask
            if "(Select All)" not in selected_vals:
                column_masks.append(df[col].isin(selected_vals))

        if column_masks:
            combined_mask = column_masks[0]
            for m in column_masks[1:]:
                combined_mask |= m   # OR across filters
        else:
            combined_mask = pd.Series([True] * len(df), index=df.index)

        # --- Final mask ---
        final_mask = global_mask & combined_mask
        filtered_df = df[final_mask]

        # --- Sorting ---
        sort_col = st.selectbox(
            "Sort by column",
            ["(No Sorting)"] + list(df.columns),
            key=f"{table_name}_sort_col"
        )
        if sort_col != "(No Sorting)":
            ascending = st.radio(
                "Sort order",
                ["Ascending", "Descending"],
                horizontal=True,
                key=f"{table_name}_sort_order"
            )
            filtered_df = filtered_df.sort_values(
                by=sort_col,
                ascending=(ascending == "Ascending")
            )

    # --- Show count outside expander ---
    st.markdown(
        f"📊 **{table_name}: Showing {len(filtered_df):,} of {len(df):,} rows "
        f"({len(df) - len(filtered_df):,} filtered out)**"
    )

    return filtered_df




        

# -------------------------
# Sidebar: Year + Program
# -------------------------
with st.sidebar:
    st.header("Filters")
    if "year" not in st.session_state:
        st.session_state.year = YEAR_OPTIONS[0]
    if "program" not in st.session_state:
        st.session_state.program = PROGRAM_OPTIONS[0]

    st.session_state.year = st.selectbox("Admission Year", YEAR_OPTIONS, index=YEAR_OPTIONS.index(st.session_state.year))
    st.session_state.program = st.selectbox("Program", PROGRAM_OPTIONS, index=PROGRAM_OPTIONS.index(st.session_state.program))

# -------------------------
# Page Title
# -------------------------
st.title("Admission Management System")
st.caption(f"Year: **{st.session_state.year}**, Program: **{st.session_state.program}**")

# -------------------------
# Tabs
# -------------------------
tabs = st.tabs(["CourseMaster", "CollegeMaster", "CollegeCourseMaster", "SeatMatrix", "StudentDetails", "Allotment", "Vacancy"])

# ---------- CourseMaster ----------
with tabs[0]:
    st.subheader("📚 CourseMaster")
    df_course = load_table("CourseMaster")
    df_course = upload_and_preview("CourseMaster", df_course, year_based=False)
    download_button_for_df(df_course, "CourseMaster")
    #edited = st.data_editor(df_course, num_rows="dynamic", use_container_width=True)
    df_filtered = filter_and_sort_dataframe(df_course, "CourseMaster")
    edited = st.data_editor(df_filtered, num_rows="dynamic", use_container_width=True)

    if st.button("💾 Save CourseMaster"):
        save_table("CourseMaster", edited)

# ---------- CollegeMaster ----------
with tabs[1]:
    st.subheader("🏫 College Master")
    uploaded = st.file_uploader("Upload College Master (Excel/CSV)", type=["xlsx", "xls", "csv"], key="college_upload")
    if uploaded:
        if uploaded.name.endswith(".csv"):
            df_col = pd.read_csv(uploaded)
        else:
            df_col = pd.read_excel(uploaded)
        save_table("CollegeMaster", df_col)

    df_col = load_table("CollegeMaster")
    df_col_filtered = filter_and_sort_dataframe(df_col, "CollegeMaster")
    edited_col = st.data_editor(df_col_filtered, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save College Master"):
        save_table("CollegeMaster", edited_col)
# ---------- CollegeCourseMaster ----------
with tabs[2]:
    st.subheader("🏫📚 College Course Master")
    uploaded = st.file_uploader("Upload College-Course Master (Excel/CSV)", type=["xlsx", "xls", "csv"], key="collegecourse_upload")
    if uploaded:
        if uploaded.name.endswith(".csv"):
            df_cc = pd.read_csv(uploaded)
        else:
            df_cc = pd.read_excel(uploaded)
        save_table("CollegeCourseMaster", df_cc)

    df_cc = load_table("CollegeCourseMaster")
    df_cc_filtered = filter_and_sort_dataframe(df_cc, "CollegeCourseMaster")
    edited_cc = st.data_editor(df_cc_filtered, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save College Course Master"):
        save_table("CollegeCourseMaster", edited_cc)

# ---------- SeatMatrix (year+program scoped) ----------
with tabs[3]:
    st.subheader("SeatMatrix (Year+Program scoped)")
    df_seat_all = load_table("SeatMatrix")
    df_seat_all = upload_and_preview("SeatMatrix", df_seat_all, year_based=True)
    # filtered view for editing
    ay = st.session_state.year
    pr = st.session_state.program
    if "AdmissionYear" in df_seat_all.columns and "Program" in df_seat_all.columns:
        filtered = df_seat_all[(df_seat_all["AdmissionYear"] == ay) & (df_seat_all["Program"] == pr)]
    else:
        filtered = pd.DataFrame(columns=df_seat_all.columns)
    download_button_for_df(filtered, f"SeatMatrix_{ay}_{pr}")
    st.write(f"Showing rows for AdmissionYear={ay} and Program={pr}. Editing and saving will replace rows for this Year+Program only.")
    edited = st.data_editor(filtered, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Save SeatMatrix (Year+Program)"):
        # ensure AdmissionYear & Program columns exist in edited (they should)
        if "AdmissionYear" not in edited.columns:
            edited["AdmissionYear"] = ay
        if "Program" not in edited.columns:
            edited["Program"] = pr
        save_table("SeatMatrix", edited, replace_where={"AdmissionYear": ay, "Program": pr})

# ---------- StudentDetails ----------
with tabs[4]:
    st.subheader("👨‍🎓 Student Details")

    # Load existing data
    df_stu_all = load_table("StudentDetails")

    # File upload
    uploaded = st.file_uploader("Upload StudentDetails (Excel/CSV)", type=["xlsx", "xls", "csv"], key="studentdetails_upload")
    if uploaded:
        if uploaded.name.endswith(".csv"):
            df_stu_all = pd.read_csv(uploaded)
        else:
            df_stu_all = pd.read_excel(uploaded)
        save_table("StudentDetails", df_stu_all)

    # If Program column exists, allow program selection
    if not df_stu_all.empty and "Program" in df_stu_all.columns:
        selected_program = st.selectbox("Select Program", sorted(df_stu_all["Program"].dropna().unique()), key="studentdetails_program")
        df_program = df_stu_all[df_stu_all["Program"] == selected_program]

        st.write(f"📋 Showing students for **Program = {selected_program}**")
        st.download_button(
            "📥 Download Filtered Students",
            data=df_program.to_csv(index=False),
            file_name=f"StudentDetails_{selected_program}.csv",
            mime="text/csv"
        )

        df_program_filtered = filter_and_sort_dataframe(df_program, "StudentDetails")
        edited = st.data_editor(df_program_filtered, num_rows="dynamic", use_container_width=True)

        if st.button("💾 Save StudentDetails (Program Scoped)"):
            save_table("StudentDetails", edited, replace_where={"Program": selected_program})

    else:
        st.download_button(
            "📥 Download All Students",
            data=df_stu_all.to_csv(index=False),
            file_name="StudentDetails.csv",
            mime="text/csv"
        )

        df_stu_filtered = filter_and_sort_dataframe(df_stu_all, "StudentDetails")
        edited = st.data_editor(df_stu_filtered, num_rows="dynamic", use_container_width=True)

        if st.button("💾 Save StudentDetails"):
            save_table("StudentDetails", edited)

    # --- FLUSH DATA BUTTON ---
    if st.button("🗑️ Flush All StudentDetails Data"):
        if st.confirm("Are you sure you want to delete all StudentDetails? This cannot be undone!"):
            df_stu_all = pd.DataFrame(columns=df_stu_all.columns)  # clear local df
            save_table("StudentDetails", df_stu_all)              # clear DB table
            st.success("✅ All StudentDetails data cleared!")

# ---------- Allotment (view-only for now) ----------
with tabs[5]:
    st.subheader("Allotment (view)")
    df_allot = load_table("Allotment")
    if df_allot.empty:
        st.info("No allotment data found yet.")
    else:
        download_button_for_df(df_allot, "Allotment")
        st.dataframe(df_allot, use_container_width=True)

# ---------- Vacancy (skeleton) ----------
with tabs[6]:
    st.subheader("Vacancy (skeleton)")
    st.info("Vacancy calculation will be added next (Step 2). For now you can upload / edit SeatMatrix and Allotment tables; vacancy will be computed from them in the next step.")
