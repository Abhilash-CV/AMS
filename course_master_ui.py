import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
import mysql.connector
# ---------------- Database Config ---------------- #
host="192.192.192.100",        # Change if remote DB
user="intern",             #  MySQL username
password="Intern@100",

def get_basic_engine(program: str, year: int):
    """
    Connect to the '_basic' database for the program/year
    e.g., PGN2024_basic
    """
    db_name = f"{program.upper()}{year}_basic"
    url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{db_name}"
    return create_engine(url)

# ---------------- Database Functions ---------------- #
def load_course_master(program: str, year: int):
    engine = get_basic_engine(program, year)
    try:
        query = text("SELECT * FROM coursemaster")
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        return df
    except Exception:
        # Return empty if table doesn't exist
        return pd.DataFrame()

def save_course_master(df: pd.DataFrame, program: str, year: int):
    engine = get_basic_engine(program, year)
    with engine.begin() as conn:
        df.to_sql("coursemaster", conn, if_exists="replace", index=False)

def flush_course_master(program: str, year: int):
    engine = get_basic_engine(program, year)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE coursemaster"))

# ---------------- Streamlit UI ---------------- #
def course_master_ui(year, program):
    st.subheader(f"📚 Course Master - {program} {year}")

    # Load table
    df_course = load_course_master(program, year)

    # File uploader
    uploaded = st.file_uploader(
        f"Upload Course Master for {program} {year} (Excel/CSV)",
        type=["xlsx", "xls", "csv"],
        key=f"upl_course_master_{year}_{program}"
    )
    if uploaded:
        try:
            if uploaded.name.lower().endswith(".csv"):
                df_new = pd.read_csv(uploaded)
            else:
                df_new = pd.read_excel(uploaded)

            df_new["AdmissionYear"] = year
            df_new["Program"] = program

            save_course_master(df_new, program, year)
            st.success("✅ Course Master uploaded successfully!")
            df_course = load_course_master(program, year)
        except Exception as e:
            st.error(f"Error reading file: {e}")

    # Display & edit table
    st.caption(f"Showing rows for **AdmissionYear={year} & Program={program}**")
    edited_course = st.data_editor(
        df_course,
        num_rows="dynamic",
        use_container_width=True,
        key=f"data_editor_course_master_{year}_{program}"
    )

    if st.button("💾 Save Course Master", key=f"save_course_master_{year}_{program}"):
        if "AdmissionYear" not in edited_course.columns:
            edited_course["AdmissionYear"] = year
        if "Program" not in edited_course.columns:
            edited_course["Program"] = program
        save_course_master(edited_course, program, year)
        st.success("✅ Course Master saved!")
        df_course = load_course_master(program, year)

    # ---------- Danger Zone ----------
    with st.expander("🗑️ Danger Zone: Course Master"):
        st.error("⚠️ This action will permanently delete ALL Course Master data!")
        confirm_key = f"flush_confirm_course_{year}_{program}"
        if confirm_key not in st.session_state:
            st.session_state[confirm_key] = False

        st.session_state[confirm_key] = st.checkbox(
            "Yes, I understand this will delete all Course Master permanently.",
            value=st.session_state[confirm_key],
            key=f"flush_course_confirm_{year}_{program}"
        )

        if st.session_state[confirm_key]:
            if st.button("🚨 Flush All Course Master Data", key=f"flush_course_btn_{year}_{program}"):
                flush_course_master(program, year)
                st.success("✅ All Course Master data cleared!")
                st.session_state[confirm_key] = False
                st.experimental_rerun()
