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
             "Seat Matrix", "CandidateDetails", "Allotment", "Vacancy","Seat Conversion"],
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
        df_col = load_table("College Master", year, program)
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
       # if not df_Candidate.empty and "Quota" in df_Candidate.columns:
           # quota_count = df_Candidate["Quota"].value_counts().reset_index()
           # quota_count.columns = ["Quota", "Count"]
            #fig_quota = px.pie(
              #  quota_count,
               # names="Quota",
                #values="Count",
               # hole=0.5,
               # template="plotly_white",
               # color_discrete_sequence=px.colors.qualitative.Set3,
              #  height=300
           # )
          #  chart_col2.plotly_chart(fig_quota, use_container_width=True)
    
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
        #st.subheader("📚 Course Master")
        course_master_ui(year, program)
        
    
    elif page == "Seat Matrix":
        seat_matrix_ui(year, program)

    
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
        college_master_ui(year, program)

    
    elif page == "College Course Master":
        college_course_master_ui(year, program)
        
    
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
    elif page == "Seat Conversion":
        #st.title("🔄 Seat Conversion")
        from seat_conversion1 import seat_conversion_ui
        seat_conversion_ui()
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


    
    #with tabs[0]:
    #     st.subheader("📚 Course Master")
        
    #     # Load table data for selected year & program
    #     df_course = load_table("Course Master", year, program)
        
    #     # File uploader
    #     upload_key = f"upl_course_master_{year}_{program}"
    #     uploaded = st.file_uploader(
    #         "Upload Course Master (Excel/CSV)",
    #         type=["xlsx", "xls", "csv"],
    #         key=upload_key
    #     )
    #     if uploaded:
    #         try:
    #             if uploaded.name.lower().endswith('.csv'):
    #                 df_new = pd.read_csv(uploaded)
    #             else:
    #                 df_new = pd.read_excel(uploaded)
        
    #             df_new = clean_columns(df_new)
    #             df_new["AdmissionYear"] = year
    #             df_new["Program"] = program
        
    #             # Save with replacement for same year+program
    #             save_table("Course Master", df_new, replace_where={"AdmissionYear": year, "Program": program})
    #             df_course = load_table("Course Master", year, program)
    #             st.success("✅ Course Master uploaded successfully!")
    #         except Exception as e:
    #             st.error(f"Error reading file: {e}")
        
    #     # Download + Filter + Edit
    #     download_button_for_df(df_course, f"Course Master_{year}_{program}")
    #     st.caption(f"Showing rows for **AdmissionYear={year} & Program={program}**")
        
    #     df_course_filtered = filter_and_sort_dataframe(df_course, "Course Master")
    #     edited_course = st.data_editor(
    #         df_course_filtered,
    #         num_rows="dynamic",
    #         use_container_width=True,
    #         key=f"data_editor_course_master_{year}_{program}",
    #     )
        
    #     if st.button("💾 Save Course Master", key=f"save_course_master_{year}_{program}"):
    #         if "AdmissionYear" not in edited_course.columns:
    #             edited_course["AdmissionYear"] = year
    #         if "Program" not in edited_course.columns:
    #             edited_course["Program"] = program
    #         save_table("Course Master", edited_course, replace_where={"AdmissionYear": year, "Program": program})
    #         st.success("✅ Course Master saved!")
    #         df_course = load_table("Course Master", year, program)
    
    #     # ---------- Course Master Danger Zone ----------
    #     with st.expander("🗑️ Danger Zone: Course Master"):
    #         st.error("⚠️ This action will permanently delete ALL Course Master data!")
    #         confirm_key = f"flush_confirm_course_{year}_{program}"
    #         if confirm_key not in st.session_state:
    #             st.session_state[confirm_key] = False
        
    #         st.session_state[confirm_key] = st.checkbox(
    #             "Yes, I understand this will delete all Course Master permanently.",
    #             value=st.session_state[confirm_key],
    #             key=f"flush_course_confirm_{year}_{program}"
    #         )
        
    #         if st.session_state[confirm_key]:
    #             if st.button("🚨 Flush All Course Master Data", key=f"flush_course_btn_{year}_{program}"):
    #                 save_table("Course Master", pd.DataFrame(), replace_where=None)
    #                 st.success("✅ All Course Master data cleared!")
    #                 st.session_state[confirm_key] = False
    #                 st.rerun()
    
                    

    

    
        
        
    # ---------- CollegeMaster (global) ----------
    # ---------- College Master ----------
   # ---------- College Master (scoped by Year + Program) ----------
   # with tabs[1]:
    
            

   # ---------- College Course Master (scoped by Year + Program) ----------
    #with tabs[2]:
        #college_course_master_ui(year, program)

    
    # ---------- SeatMatrix (year+program scoped) ----------
    #with tabs[3]:
        #seat_matrix_ui(year, program)
    # ---------- CandidateDetails (year+program scoped) ----------
    with tabs[4]:
        st.subheader("👨‍🎓 Candidate Details (Year+Program)")
    
        # Load scoped data
        df_stu = load_table("Candidate Details", year, program)
    
        # Upload
        uploaded = st.file_uploader(
            "Upload CandidateDetails (Excel/CSV)",
            type=["xlsx", "xls", "csv"],
            key=f"upl_CandidateDetails_{year}_{program}"
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
    
                # Deduplicate (prefer CandidateID / RollNo if present)
                dedup_cols = []
                for col in ["CandidateID", "RollNo", "RegistrationNo"]:
                    if col in df_new.columns:
                        dedup_cols.append(col)
                if dedup_cols:
                    df_new = df_new.drop_duplicates(subset=dedup_cols)
    
                save_table(
                    "Candidate Details",
                    df_new,
                    replace_where={"AdmissionYear": year, "Program": program}
                )
                df_stu = load_table("Candidate Details", year, program)
                st.success("✅ Candidate Details uploaded successfully!")
            except Exception as e:
                st.error(f"Error reading file: {e}")
    
        # Download + Show
        download_button_for_df(df_stu, f"CandidateDetails_{year}_{program}")
        st.caption(f"Showing rows for **AdmissionYear={year} & Program={program}**")
    
        df_stu_filtered = filter_and_sort_dataframe(df_stu, "CandidateDetails")
        edited_stu = st.data_editor(
            df_stu_filtered,
            num_rows="dynamic",
            use_container_width=True,
            key=f"data_editor_CandidateDetails_{year}_{program}"
        )
    
        # Save
        if st.button("💾 Save CandidateDetails (Year+Program Scoped)", key=f"save_CandidateDetails_{year}_{program}"):
            if "AdmissionYear" not in edited_stu.columns:
                edited_stu["AdmissionYear"] = year
            if "Program" not in edited_stu.columns:
                edited_stu["Program"] = program
    
            dedup_cols = []
            for col in ["CandidateID", "RollNo", "RegistrationNo"]:
                if col in edited_stu.columns:
                    dedup_cols.append(col)
            if dedup_cols:
                edited_stu = edited_stu.drop_duplicates(subset=dedup_cols)
    
            save_table(
                "Candidate Details",
                edited_stu,
                replace_where={"AdmissionYear": year, "Program": program}
            )
            st.success("✅ Candidate Details saved!")
            df_stu = load_table("Candidate Details", year, program)
    
        # Danger Zone
        with st.expander("🗑️ Danger Zone: Candidate Details"):
            st.error(f"⚠️ This will permanently delete Candidate Details for {year} - {program}!")
    
            confirm_key = f"flush_confirm_candidate_{year}_{program}"
            if confirm_key not in st.session_state:
                st.session_state[confirm_key] = False
    
            st.session_state[confirm_key] = st.checkbox(
                f"Yes, I understand this will delete Candidate Details permanently for {year} - {program}.",
                value=st.session_state[confirm_key],
                key=f"flush_candidate_confirm_{year}_{program}"
            )
    
            if st.session_state[confirm_key]:
                if st.button("🚨 Flush Candidate Details Data", key=f"flush_candidate_btn_{year}_{program}"):
                    save_table(
                        "Candidate Details",
                        pd.DataFrame(),
                        replace_where={"AdmissionYear": year, "Program": program}
                    )
                    st.success(f"✅ Candidate Details cleared for {year} - {program}!")
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






































