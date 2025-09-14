import streamlit as st
from role_manager import init_roles_table, set_permission, get_all_permissions

def user_role_management_page():
    st.header("👥 User Role Management")

    init_roles_table()

    # Replace with your real user list (or fetch from DB)
    users = ["admin", "viewer1", "viewer2"]
    pages = ["Dashboard", "Course Master", "College Master",
             "College Course Master", "Seat Matrix",
             "Candidate Details", "Allotment", "Vacancy"]

    # Show current permissions
    df_roles = get_all_permissions()
    st.subheader("📊 Current Permissions")
    st.dataframe(df_roles, use_container_width=True)

    st.subheader("📝 Assign / Modify Permissions")

    with st.form("role_form"):
        selected_user = st.selectbox("👤 Select User", users)
        selected_pages = st.multiselect("📂 Select Pages", pages)
        allow_edit = st.checkbox("✅ Allow Edit", value=True)

        submitted = st.form_submit_button("💾 Save Permissions")
        if submitted:
            for page in selected_pages:
                set_permission(selected_user, page, allow_edit)
            st.success(f"✅ Permissions updated for **{selected_user}** on {len(selected_pages)} pages.")
            st.rerun()
