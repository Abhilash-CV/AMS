# common_functions.py
import pandas as pd
import streamlit as st
import io, re, base64, requests, uuid, random, string

# -------------------------
# GitHub Config
# -------------------------
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO = st.secrets["GITHUB_REPO"]   # e.g. "yourname/admission-data"
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")
API_URL = "https://api.github.com"

def github_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

def _get_file_sha(path):
    """Get SHA of existing file (needed for update)."""
    url = f"{API_URL}/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    r = requests.get(url, headers=github_headers())
    if r.status_code == 200:
        return r.json()["sha"]
    return None

# -------------------------
# Core Save/Load
# -------------------------
def save_table(table: str, df: pd.DataFrame, replace_where: dict = None, append: bool = False):
    """
    Save DataFrame to GitHub as CSV.
    If replace_where is given → filter old rows, replace only those.
    If append=True → append to existing data.
    Otherwise full overwrite.
    """
    if df is None or df.empty:
        st.warning(f"⚠️ No data to save for {table}")
        return

    path = f"data/{table}.csv"
    sha = _get_file_sha(path)

    # Load existing if append or replace
    existing = pd.DataFrame()
    if sha and (append or replace_where):
        existing = load_table(table)

    if replace_where:
        # Remove rows matching replace_where
        mask = pd.Series(True, index=existing.index)
        for k, v in replace_where.items():
            if k in existing.columns:
                mask &= existing[k] != v
        existing = existing[mask]
        df = pd.concat([existing, df], ignore_index=True)

    elif append:
        df = pd.concat([existing, df], ignore_index=True)

    # Save final CSV
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    content = base64.b64encode(csv_buffer.getvalue().encode()).decode()

    data = {
        "message": f"Update {table}.csv",
        "content": content,
        "branch": GITHUB_BRANCH
    }
    if sha and not append and not replace_where:
        data["sha"] = sha  # overwrite existing

    url = f"{API_URL}/repos/{GITHUB_REPO}/contents/{path}"
    r = requests.put(url, headers=github_headers(), json=data)

    if r.status_code in (200, 201):
        st.success(f"✅ Saved {len(df)} rows to {table} (GitHub)")
    else:
        st.error(f"❌ Failed to save {table}: {r.json()}")

def load_table(table: str, year: str = None, program: str = None) -> pd.DataFrame:
    """Load table CSV from GitHub and filter by AdmissionYear/Program if given."""
    path = f"data/{table}.csv"
    url = f"{API_URL}/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    r = requests.get(url, headers=github_headers())
    if r.status_code != 200:
        return pd.DataFrame()

    content = base64.b64decode(r.json()["content"]).decode()
    df = pd.read_csv(io.StringIO(content))
    df = clean_columns(df)

    if year and "AdmissionYear" in df.columns:
        df = df[df["AdmissionYear"].astype(str) == str(year)]
    if program and "Program" in df.columns:
        df = df[df["Program"].astype(str) == str(program)]

    return df.reset_index(drop=True)

# -------------------------
# Helpers
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

def download_button_for_df(df: pd.DataFrame, name: str):
    """Download buttons for CSV/Excel."""
    if df is None or df.empty:
        st.warning("⚠️ No data to download.")
        return

    rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    col1, col2 = st.columns(2)

    # CSV
    csv_data = df.to_csv(index=False).encode("utf-8")
    col1.download_button(
        label=f"⬇ Download {name} (CSV)",
        data=csv_data,
        file_name=f"{name}.csv",
        mime="text/csv",
        key=f"download_csv_{name}_{rand_suffix}"
    )

    # Excel
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
            key=f"download_xlsx_{name}_{rand_suffix}"
        )
    except Exception:
        col2.warning("⚠️ Excel download unavailable (install xlsxwriter)")
