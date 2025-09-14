import streamlit as st
import pandas as pd
import json
import os

USER_ROLE_FILE = "user_roles.json"

# --- Helper Functions ---
def load_user_roles():
    if os.path.exists(USER_ROLE_FILE):
        with open(USER_ROLE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}  # Empty dict if file doesn't exist

def save_user_roles(user_roles):
    with open(USER_ROLE_FILE, "w", encoding="utf-8") as f:
        json.dump(user_roles, f, indent=4)

def user_role_management_page(PAGES):
    st.title("🔑 User Role Management")

    # Load user roles
    user_roles = load_user_roles()

    # Show current users
    if user_roles:
        st.subheader("👥 Current Users & Roles")
        df_users = pd.DataFrame([
            {"Username": u, "Role": data["role"], "Allowed Pages": ", ".join(data.get("allowed_pages", []))}
            for u, data in user_roles.items()
        ])
        st.dataframe(df_users, use_container_width=True)
    else:
        st.info("No users defined yet.")

    st.markdown("---")
    st.subheader("➕ Add / Update User Role")

    username = st.text_input("Username (case-sensitive)")
    role = st.selectbox("Select Role", ["admin", "viewer"])
    allowed_pages = st.multiselect(
        "Allowed Pages",
        options=list(PAGES.keys()),
        default=list(PAGES.keys()) if role == "admin" else []
    )

    if st.button("💾 Save User"):
        if username:
            user_roles[username] = {"role": role, "allowed_pages": allowed_pages}
            save_user_roles(user_roles)
            st.success(f"✅ User '{username}' updated successfully!")
            st.experimental_rerun()
        else:
            st.warning("⚠️ Please enter a username.")

    st.markdown("---")
    st.subheader("🗑️ Remove User")
    remove_user = st.selectbox("Select user to remove", [""] + list(user_roles.keys()))
    if st.button("🗑️ Delete User"):
        if remove_user and remove_user in user_roles:
            del user_roles[remove_user]
            save_user_roles(user_roles)
            st.success(f"✅ User '{remove_user}' removed!")
            st.experimental_rerun()
