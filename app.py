"""StarPump — Star Resorts & Service Station Bill Tracker."""

import streamlit as st

from datetime import datetime

from lib.ui import apply_theme, sidebar_branding, PUMP_NAME
from lib.auth import require_login, logout, get_current_user, get_current_role
from lib.db import init_db
from lib.export import generate_excel

st.set_page_config(
    page_title=f"StarPump | {PUMP_NAME}",
    page_icon="\u26fd",
    layout="wide",
)

# DB + Auth (before anything else)
init_db()
require_login()
apply_theme()

# ── Sidebar branding + user info ─────────────────────────────────────────────
sidebar_branding()

with st.sidebar:
    st.divider()
    user = get_current_user()
    role = get_current_role()
    st.markdown(f"""
    <div style="padding: 0 4px;">
        <div style="font-size: 0.8rem; color: #BBE1FA;">Logged in as</div>
        <div style="font-size: 1rem; font-weight: 600; color: #FFFFFF;">{user}</div>
        <div style="font-size: 0.75rem; color: #7A9EBF; text-transform: uppercase;">{role}</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("")

    if st.button("Logout", use_container_width=True):
        logout()

    st.divider()
    now = datetime.now()
    month_year = now.strftime("%b_%Y")
    excel_bytes = generate_excel()
    st.download_button(
        "Download Full Ledger",
        data=excel_bytes,
        file_name=f"StarPump_All_Parties_{month_year}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

# ── Navigation ───────────────────────────────────────────────────────────────
pg = st.navigation([
    st.Page("pages/0_Dashboard.py", title="Dashboard", icon="\U0001f3e0", default=True),
    st.Page("pages/1_Upload_Bill.py", title="Upload Bill", icon="\U0001f4f8"),
    st.Page("pages/2_Manual_Entry.py", title="Manual Entry", icon="\u270f\ufe0f"),
    st.Page("pages/3_View_Ledger.py", title="View Ledger", icon="\U0001f4ca"),
    st.Page("pages/4_Settings.py", title="Settings", icon="\u2699\ufe0f"),
])

pg.run()
