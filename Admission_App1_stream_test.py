# common_functions.py

import pandas as pd
import streamlit as st
import io
import re
import random
import string
import uuid
import sqlite3
import os
import os
#st.write("common_functions.py path:", os.path.abspath(__file__))
import common_functions
import inspect

print("🛠 Loaded common_functions from:", common_functions.__file__)
print("🛠 Available functions:", [f for f in dir(common_functions) if not f.startswith("_")])

# -------------------------
# DB File Path
# -------------------------
DB_FILE = os.path.join(os.path.dirname(__file__), "admission.db")

# -------------------------
# Load Table
# -------------------------
def load_table(table: str, year: str = None, program: str = None) -> pd.DataFrame:
    conn = get_conn()
    if not table_exists(table):
        ensure_table_and_columns(table, pd.DataFrame())
        return pd.DataFrame()

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

# -------------------------
# Save Table
# -------------------------
def save_table(table: str, df: pd.DataFrame, replace_where: dict = None):
    conn = get_conn()
    cur = conn.cursor()
    df = clean_columns(df) if df is not None else pd.DataFrame()

    if replace_where:
        for k, v in replace_where.items():
            if k not in df.columns:
                df[k] = v

        ensure_table_and_columns(table, df)

        where_clause = " AND ".join([f'"{k}"=?' for k in replace_where.keys()])
        params = tuple(replace_where.values())
        try:
            cur.execute(f'DELETE FROM "{table}" WHERE {where_clause}', params)
        except Exception:
            pass

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

    try:
        cur.execute(f'DROP TABLE IF EXISTS "{table}"')
    except Exception:
        pass

    if df is None or df.empty:
        conn.commit()
        st.success(f"✅ Cleared all rows from {table}")
        return

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
# Clean Columns
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

# -------------------------
# Download Button
# -------------------------
def download_button_for_df(df: pd.DataFrame, name: str):
    if df is None or df.empty:
        st.warning("⚠️ No data to download.")
        return

    rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

    col1, col2 = st.columns(2)
    csv_data = df.to_csv(index=False).encode("utf-8")
    col1.download_button(
        label=f"⬇ Download {name} (CSV)",
        data=csv_data,
        file_name=f"{name}.csv",
        mime="text/csv",
        key=f"download_csv_{name}_{rand_suffix}",
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
            key=f"download_xlsx_{name}_{rand_suffix}",
            use_container_width=True
        )
    except Exception:
        col2.warning("⚠️ Excel download unavailable (install xlsxwriter)")

# -------------------------
# Filter & Sort DataFrame
# -------------------------
def filter_and_sort_dataframe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    if df is None or df.empty:
        st.write(f"⚠️ No data available for {table_name}")
        return df

    year = st.session_state.get("year", "")
    program = st.session_state.get("program", "")
    base_key = f"{table_name}_{year}_{program}"

    with st.expander(f"🔎 Filter & Sort ({table_name})", expanded=False):
        search_text = st.text_input(
            f"🔍 Global Search ({table_name})",
            value="",
            key=f"{base_key}_search"
        ).lower().strip()

        mask = pd.Series(True, index=df.index)
        if search_text:
            mask &= df.apply(lambda row: row.astype(str).str.lower().str.contains(search_text).any(), axis=1)

        for col in df.columns:
            unique_vals = sorted([str(x) for x in df[col].dropna().unique()])
            options = ["(All)"] + unique_vals
            selected_vals = st.multiselect(
                f"Filter {col}",
                options,
                default=["(All)"],
                key=f"{base_key}_{col}_filter"
            )
            if "(All)" not in selected_vals:
                mask &= df[col].astype(str).isin(selected_vals)

        filtered = df[mask].reset_index(drop=True)
        filtered.index = filtered.index + 1

    st.markdown(f"**📊 Showing {len(filtered)} of {len(df)} records**")
    return filtered

# -------------------------
# DB Helpers
# -------------------------
@st.cache_resource
def get_conn():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

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
    conn = get_conn()
    cur = conn.cursor()
    existing = get_table_columns(table)

    if not existing:
        if df is None or df.empty:
            cur.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ("AdmissionYear" TEXT, "Program" TEXT)')
            conn.commit()
            existing = get_table_columns(table)
        else:
            col_defs = []
            for col, dtype in zip(df.columns, df.dtypes):
                col_defs.append(f'"{col}" {pandas_dtype_to_sql(dtype)}')
            if "AdmissionYear" not in df.columns:
                col_defs.append('"AdmissionYear" TEXT')
            if "Program" not in df.columns:
                col_defs.append('"Program" TEXT')
            create_stmt = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(col_defs)})'
            cur.execute(create_stmt)
            conn.commit()
            existing = get_table_columns(table)

    if df is not None:
        for col in df.columns:
            if col not in existing:
                try:
                    cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{col}" TEXT')
                    conn.commit()
                    existing.append(col)
                except Exception:
                    pass

    for special in ("AdmissionYear", "Program"):
        if special not in existing:
            try:
                cur.execute(f'ALTER TABLE "{table}" ADD COLUMN "{special}" TEXT')
                conn.commit()
                existing.append(special)
            except Exception:
                pass


