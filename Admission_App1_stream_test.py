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

# -----------------------------
# DB Helpers
# -----------------------------
def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS CourseMaster (Program TEXT, Course TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS CollegeMaster (grp TEXT, typ TEXT, College TEXT, college_desc TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS CollegeCourseMaster (College TEXT, Course TEXT, Seats INT)")
    cur.execute("CREATE TABLE IF NOT EXISTS SeatMatrix (College TEXT, Program TEXT, Seats INT)")
    cur.execute("CREATE TABLE IF NOT EXISTS StudentDetails (ApplNo TEXT, Name TEXT, Program TEXT, Year TEXT)")
    conn.commit()
    conn.close()

init_db()

def load_table(table):
    conn = get_connection()
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    conn.close()
    return df

def save_table(table, df):
    conn = get_connection()
    df.to_sql(table, conn, if_exists="replace", index=False)
    conn.close()

# -----------------------------
# App Layout
# -----------------------------
tabs = st.tabs(["CourseMaster", "CollegeMaster", "CollegeCourseMaster", "SeatMatrix", "StudentDetails", "Allotment", "Vacancy"])

# -----------------------------
# Course Master
# -----------------------------
with tabs[0]:
    st.header("Course Master")
    df_course = load_table("CourseMaster")
    edited = st.data_editor(df_course, num_rows="dynamic", use_container_width=True, key="course_master_editor")
    if st.button("💾 Save Course Master", key="save_course_master_btn"):
        save_table("CourseMaster", edited)
        st.success("Course Master saved successfully!")

# -----------------------------
# College Master
# -----------------------------
with tabs[1]:
    st.header("College Master")
    df_col = load_table("CollegeMaster")
    edited_col = st.data_editor(df_col, num_rows="dynamic", use_container_width=True, key="college_master_editor")
    if st.button("💾 Save College Master", key="save_college_master_btn"):
        save_table("CollegeMaster", edited_col)
        st.success("College Master saved successfully!")

# -----------------------------
# College Course Master
# -----------------------------
with tabs[2]:
    st.header("College Course Master")
    df_cc = load_table("CollegeCourseMaster")
    edited_cc = st.data_editor(df_cc, num_rows="dynamic", use_container_width=True, key="college_course_master_editor")
    if st.button("💾 Save College Course Master", key="save_college_course_master_btn"):
        save_table("CollegeCourseMaster", edited_cc)
        st.success("College Course Master saved successfully!")

# -----------------------------
# Seat Matrix
# -----------------------------
with tabs[3]:
    st.header("Seat Matrix")
    df_seat = load_table("SeatMatrix")
    edited_seat = st.data_editor(df_seat, num_rows="dynamic", use_container_width=True, key="seat_matrix_editor")
    if st.button("💾 Save Seat Matrix", key="save_seat_matrix_btn"):
        save_table("SeatMatrix", edited_seat)
        st.success("Seat Matrix saved successfully!")

# -----------------------------
# Student Details
# -----------------------------
with tabs[4]:
    st.header("Student Details")
    df_student = load_table("StudentDetails")
    edited_student = st.data_editor(df_student, num_rows="dynamic", use_container_width=True, key="student_details_editor")
    if st.button("💾 Save Student Details", key="save_student_details_btn"):
        save_table("StudentDetails", edited_student)
        st.success("Student Details saved successfully!")

# -----------------------------
# Allotment
# -----------------------------
with tabs[5]:
    st.header("Allotment")
    st.info("Allotment logic to be implemented.")

# -----------------------------
# Vacancy
# -----------------------------
with tabs[6]:
    st.header("Vacancy")
    st.info("Vacancy calculation to be implemented.")
