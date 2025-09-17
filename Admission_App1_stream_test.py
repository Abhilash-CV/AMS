# admission_app_stream_fixed.py
import io
import re
import sqlite3
from datetime import datetime
import hashlib
import sys
import os
from common_functions import (
    load_table,
    save_table,
    clean_columns,
    download_button_for_df,
    filter_and_sort_dataframe,
    get_conn,
    table_exists,
    ensure_table_and_columns,
    pandas_dtype_to_sql
)

# Ensure the repo folder is in Python path
repo_dir = os.path.dirname(os.path.abspath(__file__))
if repo_dir not in sys.path:
    sys.path.append(repo_dir)
import pandas as pd
import plotly.express as px
import streamlit as st

# ✅ Import your Seat Conversion UI
from seat_conversion1 import seat_conversion_ui
from course_master_ui import course_master_ui 
from college_master_ui import college_master_ui
from college_course_master_ui import college_course_master_ui
from seat_matrix_ui import seat_matrix_ui
from candidate_details_ui import candidate_details_ui
from allotment_ui import allotment_ui
from vacancy_ui import vacancy_ui
from dashboard_ui import dashboard_ui



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
# -------------------------
# After st.set_page_config(...)
# -------------------------

# Initialize some globals so UI doesn't break if DB is empty
df_seat = pd.DataFrame()
df_course = pd.DataFrame()
df_Candidate = pd.DataFrame()
df_col = pd.DataFrame()

# Sidebar: Filters & Navigation
st.sidebar.title("Filters & Navigation")

# Provide YEAR_OPTIONS and PROGRAM_OPTIONS earlier (you already have these)
if "year" not in st.session_state:
    st.session_state.year = YEAR_OPTIONS[-1]
if "program" not in st.session_state:
    st.session_state.program = PROGRAM_OPTIONS[0]

# Make them selectable in the sidebar (keeps values in session_state)
st.session_state.year = st.sidebar.selectbox(
    "Admission Year",
    YEAR_OPTIONS,
    index=max(0, YEAR_OPTIONS.index(st.session_state.year))
)
st.session_state.program = st.sidebar.selectbox(
    "Program",
    PROGRAM_OPTIONS,
    index=max(0, PROGRAM_OPTIONS.index(st.session_state.program))
)

# Expose local variables for convenience
year = st.session_state.year
program = st.session_state.program

# Ensure login/session keys exist
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "login_error" not in st.session_state:
    st.session_state.login_error = ""

# Show login or main UI
if not st.session_state.logged_in:
    login_page()
else:
    #st.sidebar.markdown(f"**User:** {st.session_state.username.capitalize()}")
    st.success(f"👋 Welcome, {st.session_state.username.capitalize()}!")
    # 👆 Place logout button on the right side of the header
    top_col1, top_col2 = st.columns([8, 1])  # adjust ratios for spacing
    with top_col1:
        st.title("Admission Management System")
        st.caption(f"Year: **{year}**, Program: **{program}**")
    with top_col2:
        st.button("🚪 Logout", on_click=do_logout, use_container_width=True)

    # Sidebar Navigation using streamlit-option-menu
    from streamlit_option_menu import option_menu

    with st.sidebar:
        st.markdown("## 📂 Navigation")
        page = option_menu(
            None,
            [
                "Dashboard", "Course Master", "College Master", "College Course Master",
                "Seat Matrix", "Candidate Details", "Allotment", "Vacancy", "Seat Conversion"
            ],
            icons=[
                "house", "journal-bookmark", "building", "collection",
                "grid-3x3-gap", "people", "clipboard-check", "exclamation-circle", "arrow-repeat"
            ],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "5px", "background-color": "#f8f9fa"},
                "icon": {"color": "#2C3E50", "font-size": "18px"},
                "nav-link": {
                    "font-size": "13px",
                    "text-align": "left",
                    "margin": "0px",
                    "--hover-color": "#e1eafc",
                },
                "nav-link-selected": {"background-color": "#4CAF50", "color": "white"},
            }
        )

    # -------------------------
    # Page dispatch
    # -------------------------
    if page == "Dashboard":
        dashboard_ui(year, program)

    elif page == "Course Master":
        course_master_ui(year, program)

    elif page == "College Master":
        college_master_ui(year, program)

    elif page == "College Course Master":
        college_course_master_ui(year, program)

    elif page == "Seat Matrix":
        seat_matrix_ui(year, program)

    elif page == "Candidate Details":
        candidate_details_ui(year, program)

    elif page == "Allotment":
        allotment_ui(year, program)

    elif page == "Vacancy":
        vacancy_ui(year, program)

    elif page == "Seat Conversion":
        # If seat_conversion_ui requires different args, adjust accordingly
        seat_conversion_ui()

    else:
        st.info("Select a page from the sidebar navigation.")

    # -------------------------
    # Optional quick previews / downloads area (collapsible)
    # -------------------------
    with st.expander("📚 Data Table Previews (Quick)"):
        # Reload top-level dfs (so previews are up-to-date)
        df_course = load_table("Course Master", year, program)
        df_col = load_table("College Master", year, program)
        df_Candidate = load_table("Candidate Details", year, program)
        df_seat = load_table("Seat Matrix", year, program)

        for name, df in [
            ("Course Master", df_course),
            ("Candidate Details", df_Candidate),
            ("College Master", df_col),
            ("Seat Matrix", df_seat)
        ]:
            with st.expander(f"{name} Preview"):
                if df is None or df.empty:
                    st.info("No data found.")
                else:
                    st.dataframe(df, use_container_width=True)
                    download_button_for_df(df, f"{name}_{year}_{program}")
















































