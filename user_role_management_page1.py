# user_role_management_page.py
import streamlit as st
import json
import os
import hashlib
import pandas as pd
from role_manager import init_roles_table, set_permission, get_all_permissions

USER_ROLE_FILE = "user_roles.json"

# --- Helpers ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def load_user_roles():
    if os.path.exists(USER_ROLE_FILE):
        with open(USER_ROLE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_user_roles(user_roles):
    with open(USER_ROLE_FILE, "w", encoding="utf-8") as f:
        json.dump(user_roles, f, indent=4)

def user_role_management_page(PAGES):
    st.title("🔑 User Role Management")

    # --- Load User Roles ---
    user_roles = load_user_roles()

    # --- Show Current Users ---
    if user_roles:
        df_users = pd.DataFrame([
            {"Username": u, "Role": d["role"], "Allowed Pages": ", ".join(d.get("allowed_pages", []))}
            for u, d in user_roles.items()
        ])
        st.subheader("👥 Current Users")
        st.dataframe(df_users, use_container_width=True)
    else:
        st.info("No users defined yet.")

    st.markdown("---")
    st.subheader("➕ Add / Update User")
    username = st.text_input("Username (case-sensitive)")
    role = st.selectbox("Role", ["admin", "viewer"])
    allowed_pages = st.multiselect(
        "Allowed Pages",
        options=list(PAGES.keys()),
        default=list(PAGES.keys()) if role == "admin" else ["Dashboard"]
    )
    password = st.text_input("Password (leave empty for default 'welcome123')", type="password")

    if st.button("💾 Save User"):
        if username:
            if not password:
                password = "welcome123"
            user_roles[username] = {
                "role": role,
                "allowed_pages": allowed_pages,
                "password": hash_password(password)
            }
            save_user_roles(user_roles)
            st.success(f"✅ User '{username}' saved. Password: {password}")
            st.rerun()
        else:
            st.warning("Please enter a username.")

    st.markdown("---")
    st.subheader("🗑️ Remove User")
    remove_user = st.selectbox("Select user to remove", [""] + list(user_roles.keys()))
    if st.button("🗑️ Delete User"):
        if remove_user:
            user_roles.pop(remove_user)
            save_user_roles(user_roles)
            st.success(f"✅ User '{remove_user}' removed.")
            st.rerun()

    # --- Permissions Management ---
    st.markdown("---")
    st.subheader("📝 Assign / Modify Permissions")

    init_roles_table()
    df_roles = get_all_permissions()
    st.dataframe(df_roles, use_container_width=True)

    with st.form("role_form"):
        selected_user = st.selectbox("👤 Select User", list(user_roles.keys()) or ["No Users"])
        selected_pages = st.multiselect("📂 Select Pages", list(PAGES.keys()))
        allow_edit = st.checkbox("✅ Allow Edit", value=True)

        submitted = st.form_submit_button("💾 Save Permissions")
        if submitted and selected_user != "No Users":
            for page in selected_pages:
                set_permission(selected_user, page, allow_edit)
            st.success(f"✅ Permissions updated for **{selected_user}** on {len(selected_pages)} pages.")
            st.rerun()
