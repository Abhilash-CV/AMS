import streamlit as st
import pandas as pd
import json
import os
import hashlib
import secrets

USER_ROLE_FILE = "user_roles.json"

# --- Helper Functions ---
def hash_password(password: str) -> str:
    """Return SHA256 hash of a password."""
    return hashlib.sha256(password.encode()).hexdigest()

def load_user_roles():
    """Load user roles from JSON file."""
    if os.path.exists(USER_ROLE_FILE):
        with open(USER_ROLE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_user_roles(user_roles):
    """Save user roles to JSON file."""
    with open(USER_ROLE_FILE, "w", encoding="utf-8") as f:
        json.dump(user_roles, f, indent=4)

def user_role_management_page(PAGES):
    st.title("🔑 User Role Management")

    # Load current user data
    user_roles = load_user_roles()

    # Show table of users
    if user_roles:
        st.subheader("👥 Current Users & Roles")
        df_users = pd.DataFrame([
            {
                "Username": u,
                "Role": data["role"],
                "Allowed Pages": ", ".join(data.get("allowed_pages", []))
            }
            for u, data in user_roles.items()
        ])
        st.dataframe(df_users, use_container_width=True)
    else:
        st.info("No users defined yet.")

    st.markdown("---")
    st.subheader("➕ Add / Update User")

    username = st.text_input("Username (case-sensitive)")
    role = st.selectbox("Select Role", ["admin", "viewer"])
    allowed_pages = st.multiselect(
        "Allowed Pages",
        options=list(PAGES.keys()),
        default=list(PAGES.keys()) if role == "admin" else []
    )
    set_password = st.checkbox("Set Custom Password?", value=False)
    password = ""
    if set_password:
        password = st.text_input("Enter Password", type="password")

    if st.button("💾 Save User"):
        if username:
            if username not in user_roles:
                # Create new user
                if not password:
                    password = "welcome123"  # default password
                user_roles[username] = {
                    "role": role,
                    "allowed_pages": allowed_pages,
                    "password": hash_password(password)
                }
                st.success(f"✅ User '{username}' created! Default password: {password}")
            else:
                # Update existing user (keep old password unless changed)
                user_roles[username]["role"] = role
                user_roles[username]["allowed_pages"] = allowed_pages
                if password:
                    user_roles[username]["password"] = hash_password(password)
                    st.info(f"🔑 Password for '{username}' updated.")
                st.success(f"✅ User '{username}' updated successfully!")
            save_user_roles(user_roles)
            st.rerun()
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
            st.rerun()

    st.markdown("---")
    st.subheader("🔑 Reset Password")
    reset_user = st.selectbox("Select user to reset password", [""] + list(user_roles.keys()))
    if st.button("🔄 Reset Password"):
        if reset_user and reset_user in user_roles:
            new_pass = secrets.token_urlsafe(8)  # Generate random password
            user_roles[reset_user]["password"] = hash_password(new_pass)
            save_user_roles(user_roles)
            st.success(f"✅ Password for '{reset_user}' reset! New password: **{new_pass}**")
            st.rerun()
