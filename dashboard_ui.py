# dashboard_ui.py
import streamlit as st
import pandas as pd
import plotly.express as px
from common_functions import load_table

def dashboard_ui(year: str, program: str):
    # --- Load Data ---
    df_course = load_table("Course Master", year, program)
    df_col = load_table("College Master", year, program)
    df_Candidate = load_table("Candidate Details", year, program)
    df_seat = load_table("Seat Matrix", year, program)

    st.title("🎯 Admission Dashboard")
    st.markdown(f"<h6 style='color:#888;'>Year: <b>{year}</b> | Program: <b>{program}</b></h6>", unsafe_allow_html=True)

    # --- FILTERS ---
    with st.expander("🔍 Filters", expanded=True):
        filter_col1, filter_col2 = st.columns(2)


    # --- College Filter ---
        selected_college = "All"
        if not df_course.empty and "College" in df_course.columns:
            college_options = ["All"] + sorted(df_course["College"].dropna().unique().tolist())
            selected_college = filter_col1.selectbox("Filter by College", college_options, index=0)
    
        # Apply College Filter AFTER selection
        if selected_college != "All":
            # Filter Courses
            df_course = df_course[df_course["College"] == selected_college]
            # Filter Candidates
            if not df_Candidate.empty and "College" in df_Candidate.columns:
                df_Candidate = df_Candidate[df_Candidate["College"] == selected_college]
            # Filter Seat Matrix
            if not df_seat.empty and "College" in df_seat.columns:
                df_seat = df_seat[df_seat["College"] == selected_college]

    # --- Quota Filter ---
    selected_quota = "All"
    if not df_Candidate.empty and "Quota" in df_Candidate.columns:
        quota_options = ["All"] + sorted(df_Candidate["Quota"].dropna().unique().tolist())
        selected_quota = filter_col2.selectbox("Filter by Quota", quota_options, index=0)

    # Apply Quota Filter
    if selected_quota != "All":
        df_Candidate = df_Candidate[df_Candidate["Quota"] == selected_quota]

        # Quota Filter
        selected_quota = None
        if not df_Candidate.empty and "Quota" in df_Candidate.columns:
            quota_options = ["All"] + sorted(df_Candidate["Quota"].dropna().unique().tolist())
            selected_quota = filter_col2.selectbox("Filter by Quota", quota_options, index=0)
            if selected_quota != "All":
                df_Candidate = df_Candidate[df_Candidate["Quota"] == selected_quota]

    # --- KPI Cards ---
    st.subheader("📊 Key Metrics")
    kpi_cols = st.columns(4)

    total_courses = len(df_course)
    total_colleges = len(df_col)
    total_candidates = len(df_Candidate)
    total_seats = int(df_seat["Seats"].sum()) if not df_seat.empty and "Seats" in df_seat.columns else 0

    kpi_data = [
        {"icon": "🏫", "title": "Courses", "value": total_courses, "color": "#FF6B6B"},
        {"icon": "🏛️", "title": "Colleges", "value": total_colleges, "color": "#4ECDC4"},
        {"icon": "👨‍🎓", "title": "Candidates", "value": total_candidates, "color": "#556270"},
        {"icon": "💺", "title": "Seats", "value": total_seats, "color": "#FFD93D"},
    ]

    def kpi_card(col, icon, title, value, color="#000000"):
        col.markdown(
            f"""
            <div style="
                background-color:{color}20;
                padding:16px;
                border-radius:20px;
                text-align:center;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                transition: transform 0.2s ease-in-out;
            ">
                <div style="font-size:28px; font-weight:bold">{icon}</div>
                <div style="font-size:14px; color:#555; margin-top:2px;">{title}</div>
                <div style="font-size:22px; font-weight:bold; margin-top:5px;">{value}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    for col, kpi in zip(kpi_cols, kpi_data):
        kpi_card(col, kpi["icon"], kpi["title"], kpi["value"], kpi["color"])

    # --- Charts Section ---
    st.subheader("📈 Visual Insights")
    chart_col1, chart_col2 = st.columns(2)

    # Seats by Category
    if not df_seat.empty and "Category" in df_seat.columns and "Seats" in df_seat.columns:
        seat_cat = df_seat.groupby("Category")["Seats"].sum().reset_index()
        fig_seats = px.bar(
            seat_cat,
            x="Category",
            y="Seats",
            text="Seats",
            color="Seats",
            color_continuous_scale="viridis",
            template="plotly_white",
            height=300
        )
        fig_seats.update_traces(textposition="outside", marker_line_width=1)
        fig_seats.update_layout(
            title="Seats by Category",
            title_x=0.5,
            margin=dict(l=10, r=10, t=50, b=10),
            plot_bgcolor="rgba(0,0,0,0)"
        )
        chart_col1.plotly_chart(fig_seats, use_container_width=True)

    # Candidates by Quota (Pie)
    if not df_Candidate.empty and "Quota" in df_Candidate.columns:
        quota_count = df_Candidate["Quota"].value_counts().reset_index()
        quota_count.columns = ["Quota", "Count"]
        fig_quota = px.pie(
            quota_count,
            names="Quota",
            values="Count",
            hole=0.4,
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Set3,
            height=300
        )
        fig_quota.update_layout(
            title="Candidate Distribution by Quota",
            title_x=0.5,
            margin=dict(l=10, r=10, t=50, b=10)
        )
        chart_col2.plotly_chart(fig_quota, use_container_width=True)

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
            color_continuous_scale="plasma",
            height=350
        )
        fig_col_course.update_traces(textposition="outside", marker_line_width=1)
        fig_col_course.update_layout(
            margin=dict(l=10, r=10, t=40, b=40),
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_col_course, use_container_width=True)
