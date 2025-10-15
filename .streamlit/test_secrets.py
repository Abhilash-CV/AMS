import streamlit as st

st.title("🔑 Test Supabase Secrets")

try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]

    st.success("✅ Secrets loaded successfully!")
    st.write("Supabase URL:", url)
    st.write("Key starts with:", key[:10])  # show first 10 characters
except KeyError as e:
    st.error(f"❌ Secret not found: {e}")
