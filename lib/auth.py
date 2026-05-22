"""Simple two-account auth using st.secrets and session state."""

import streamlit as st
from lib.ui import PUMP_NAME, DEALER_TAG, _logo_img_tag


def require_login():
    """Show login form and st.stop() if not authenticated."""
    if "user" not in st.session_state:
        _show_login_form()
        st.stop()


def _show_login_form():
    st.markdown("""
    <style>
        section[data-testid="stSidebar"] { display: none; }
        .block-container { max-width: 420px !important; padding-top: 8vh !important; }
    </style>
    """, unsafe_allow_html=True)

    logo = _logo_img_tag(64)
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 2rem;">
        {logo}
        <h2 style="margin: 12px 0 4px 0; color: #0F4C75;">{PUMP_NAME}</h2>
        <p style="color: #D42027; font-size: 0.85rem; font-weight: 600; margin: 0;">
            {DEALER_TAG}
        </p>
        <p style="color: #7A8B9A; font-size: 0.8rem; margin-top: 4px;">Bill Tracker</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True, type="primary")

    if submitted:
        auth = st.secrets["auth"]
        if username == auth["owner_username"] and password == auth["owner_password"]:
            st.session_state.user = {"username": username, "role": "owner"}
            st.rerun()
        elif username == auth["manager_username"] and password == auth["manager_password"]:
            st.session_state.user = {"username": username, "role": "manager"}
            st.rerun()
        else:
            st.error("Invalid username or password.")


def get_current_user() -> str:
    return st.session_state.get("user", {}).get("username", "unknown")


def get_current_role() -> str:
    return st.session_state.get("user", {}).get("role", "unknown")


def logout():
    st.session_state.clear()
    st.rerun()
