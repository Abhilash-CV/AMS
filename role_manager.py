import sqlite3
import pandas as pd

DB_FILE = "admission.db"

# ---------------------------
# Database Initialization
# ---------------------------
def init_roles_table():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_roles (
        username TEXT,
        page_name TEXT,
        can_edit INTEGER,
        PRIMARY KEY (username, page_name)
    )
    """)
    conn.commit()
    conn.close()

# ---------------------------
# CRUD Operations
# ---------------------------
def set_permission(username: str, page_name: str, can_edit: bool):
    """Insert or update permission for a user and page."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
    INSERT INTO user_roles (username, page_name, can_edit)
    VALUES (?, ?, ?)
    ON CONFLICT(username, page_name)
    DO UPDATE SET can_edit=excluded.can_edit
    """, (username, page_name, 1 if can_edit else 0))
    conn.commit()
    conn.close()

def get_all_permissions() -> pd.DataFrame:
    """Return all user-page permissions as a DataFrame."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM user_roles", conn)
    conn.close()
    return df

def user_can_edit(username: str, page_name: str) -> bool:
    """Check if a user has edit permission for a given page."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT can_edit FROM user_roles WHERE username=? AND page_name=?",
              (username, page_name))
    row = c.fetchone()
    conn.close()
    return row and row[0] == 1
