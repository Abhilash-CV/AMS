# common_functions.py
import pandas as pd
import streamlit as st
import io
import re
import random
import string
from supabase import create_client

# -------------------------
# 🔐 Supabase Connection
# -------------------------
def get_supabase():
    """
    Returns a Supabase client.
    Handles missing secrets gracefully and displays a friendly error.
    """
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except KeyError:
        st.error(
            "❌ Supabase credentials not found! "
            "Please add SUPABASE_URL and SUPABASE_KEY in secrets.toml "
            "or Streamlit app settings."
        )
        return None

    try:
        client = create_client(url, key)
        return client
    except Exception as e:
        st.error(f"❌ Failed to connect to Supabase: {e}")
        return None


def get_conn():
    """
    Backward compatibility function for DB connection.
    """
    return get_supabase()


# -------------------------
# 🧹 Clean Columns
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
# 📥 Load Table
# -------------------------
def load_table(table: str, year: str = None, program: str = None) -> pd.DataFrame:
    sb = get_supabase()
    if sb is None:
        return pd.DataFrame()

    try:
        query = sb.table(table).select("*")
        if year:
            query = query.eq("AdmissionYear", year)
        if program:
            query = query.eq("Program", program)
        data = query.execute()
        records = data.data
        if not records:
            return pd.DataFrame()
        df = pd.DataFrame(records)
        return clean_columns(df)
    except Exception as e:
        st.error(f"Error loading {table}: {e}")
        return pd.DataFrame()


# -------------------------
# 💾 Save Table
# -------------------------
def save_table(table: str, df: pd.DataFrame, replace_where: dict = None, append: bool = False):
    sb = get_supabase()
    if sb is None:
        st.warning("⚠️ Cannot save data: Supabase connection not available.")
        return

    if df is None or df.empty:
        st.warning("⚠️ No data to save.")
        return

    df = clean_columns(df)
    data = df.to_dict(orient="records")

    try:
        if replace_where and not append:
            # Delete existing rows that match replace_where
            query = sb.table(table)
            for k, v in replace_where.items():
                query = query.eq(k, v)
            existing = query.execute().data
            if existing:
                for row in existing:
                    if "id" in row:
                        sb.table(table).delete().eq("id", row["id"]).execute()

        # Upsert all records
        for record in data:
            sb.table(table).upsert(record).execute()

        st.success(f"✅ Saved {len(df)} rows to {table}")
    except Exception as e:
        st.error(f"❌ Error saving {table}: {e}")


# -------------------------
# 📤 Download Helpers
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
# 🔍 Filter & Sort
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
# 🧱 Dummy Helpers for Compatibility
# -------------------------
def table_exists(table: str) -> bool:
    """Check if a Supabase table exists."""
    sb = get_supabase()
    if sb is None:
        return False
    try:
        sb.table(table).select("id").limit(1).execute()
        return True
    except Exception:
        return False

def ensure_table_and_columns(table: str, df: pd.DataFrame):
    """
    Supabase automatically manages schema — this is a no-op.
    Included for backward compatibility.
    """
    return

def pandas_dtype_to_sql(dtype) -> str:
    s = str(dtype).lower()
    if "int" in s:
        return "INTEGER"
    if "float" in s or "double" in s:
        return "REAL"
    return "TEXT"
