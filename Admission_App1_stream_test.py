# Admission_App1_stream_test.py

import os
import sys
import hashlib
import streamlit as st
import pandas as pd
import base64

# Ensure repo folder is in Python path
repo_dir = os.path.dirname(os.path.abspath(__file__))
if repo_dir not in sys.path:
    sys.path.append(repo_dir)

# -------------------------
# ✅ Import custom modules
# -------------------------
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
from seat_conversion_ui import seat_conversion_ui
from course_master_ui import course_master_ui 
from college_master_ui import college_master_ui
from college_course_master_ui import college_course_master_ui
from seat_matrix_ui import seat_matrix_ui
from candidate_details_ui import candidate_details_ui
from allotment_ui import allotment_ui
from vacancy_ui import vacancy_ui
from dashboard_ui import dashboard_ui
from user_role_management_page1 import user_role_management_page
from payment_refund_ui import payment_refund_ui
from seat_comparison_ui import seat_comparison_ui
from student_option_page import student_option_ui
from combine_excel_ui import combine_excel_ui
from combine_excel1_ui import combine_excel1_ui
from refund_forfeit_panel import refund_forfeit_panel
# -------------------------
# --- Password Hashing ---
# -------------------------
USER_CREDENTIALS = {
    "admin": hashlib.sha256("admin123".encode()).hexdigest(),
    "user1": hashlib.sha256("password1".encode()).hexdigest(),
}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# -------------------------
# --- Session State ---
# -------------------------
for key, default in [
    ("logged_in", False),
    ("username", ""),
    ("login_error", ""),
    ("year", "2025"),
    ("program", "PGN")
]:
    if key not in st.session_state:
        st.session_state[key] = default

# -------------------------
# --- Streamlit Config ---
# -------------------------
st.set_page_config(
    page_title="Admission Management System",
    layout="wide",
    page_icon="🏫",
)

# -------------------------
# --- Helpers ---
# -------------------------
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

def do_login(username, password):
    hashed = hash_password(password)
    if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == hashed:
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.login_error = ""
    else:
        st.session_state.login_error = "❌ Invalid username or password"

def do_logout():
    st.session_state.logged_in = False
    st.session_state.username = ""

def login_page():
    col1, col2, col3 = st.columns([2, 5, 3])
    with col3:
        st.header("🔐 Login")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.session_state.login_error:
            st.error(st.session_state.login_error)
        st.button("Login", key="login_btn", on_click=do_login, args=(username, password))
    with col2:
        img_base64 = get_base64_image("images/cee1.png")
        st.markdown(f"""
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
        """, unsafe_allow_html=True)

# -------------------------
# --- Test Supabase Secrets ---
# -------------------------
def test_secrets():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        st.success("✅ Supabase secrets loaded successfully!")
        st.write("Supabase URL:", url)
        st.write("Key starts with:", key[:10])
    except KeyError:
        st.error("❌ Supabase secrets missing! Check secrets.toml or Streamlit Cloud settings.")

# -------------------------
# --- Main UI ---
# -------------------------
if not st.session_state.logged_in:
    login_page()
else:
    # Top bar
    top_col1, top_col2 = st.columns([8, 1])
    with top_col1:
        st.title("Admission Management System")
        st.caption(f"Year: **{st.session_state.year}**, Program: **{st.session_state.program}**")
    with top_col2:
        st.button("🚪 Logout", on_click=do_logout, use_container_width=True)

    # Sidebar filters
    PROGRAM_OPTIONS = ["LLB5", "LLB3", "PGN", "PG Homeo", "Engineering"]
    YEAR_OPTIONS = ["2023", "2024", "2025", "2026"]

    st.session_state.year = st.sidebar.selectbox("Admission Year", YEAR_OPTIONS,
        index=max(0, YEAR_OPTIONS.index(st.session_state.year)))
    st.session_state.program = st.sidebar.selectbox("Program", PROGRAM_OPTIONS,
        index=max(0, PROGRAM_OPTIONS.index(st.session_state.program)))

    # Sidebar navigation
    from streamlit_option_menu import option_menu
    PAGES = {
        "Dashboard": "house",
        "Course Master": "journal-bookmark",
        "College Master": "building",
        "College Course Master": "collection",
        "Seat Matrix": "grid-3x3-gap",
        "Candidate Details": "people",
        "Allotment": "clipboard-check",
        "Vacancy": "exclamation-circle",
        "Seat Conversion": "arrow-repeat",
        "Seat Change": "arrow-left-right",
        "Seat Merging": "table",
        "Seat Combine": "table",
        "User Management": "person-gear",
        "Payment Details": "credit-card",
        "Refund Panel": "list-ol",
        "Student Options (Test)": "list-ol"
        
    }

    from user_role_management_page1 import load_user_roles
    user_roles = load_user_roles()
    role_info = {"role": "viewer"}
    if st.session_state.username in user_roles:
        role_info = user_roles[st.session_state.username]

    allowed_pages = list(PAGES.keys())
    if role_info.get("role") != "admin":
        allowed_pages = role_info.get("allowed_pages", allowed_pages)
        allowed_pages = [p for p in allowed_pages if p != "User Management"]

    with st.sidebar:
        st.markdown("## 📂 Navigation")
        page = option_menu(
            None, allowed_pages,
            icons=[PAGES[p] for p in allowed_pages],
            menu_icon="cast",
            default_index=0,
        )

    # -------------------------
    # Page routing
    # -------------------------
    if page == "User Management":
        if role_info.get("role") == "admin":
            from user_role_management_page import user_role_management_page
            user_role_management_page(PAGES)
        else:
            st.error("🚫 Not authorized")
    else:
        year = st.session_state.year
        program = st.session_state.program
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
            seat_conversion_ui()
        elif page == "Seat Change":
            seat_comparison_ui()
        elif page == "Payment Details":
            payment_refund_ui()
        elif page == "Student Options (Test)":
            student_option_ui(year, program, student_id="admin_test")
        elif page == "Seat Merging":
            combine_excel_ui()
        elif page == "Seat Combine":
            combine_excel1_ui()
        elif page == "Refund Panel":
            refund_forfeit_panel()


# Optional: run secret test
# test_secrets()






