# common_functions.py
import pandas as pd
import streamlit as st

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
def clean_columns(df):
    # Your existing logic for cleaning column names
    pass

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

