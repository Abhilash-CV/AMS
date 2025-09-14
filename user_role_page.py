import streamlit as st
import json
import os
import hashlib
import pandas as pd
import secrets

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
    user_roles = load_user_roles()

    # --- Show users ---
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
        default=list(PAGES.keys()) if role=="admin" else ["Dashboard"]
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
