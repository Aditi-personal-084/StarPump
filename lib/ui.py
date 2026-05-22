"""Shared UI styling and branding for Star Resorts & Service Station."""

import base64
from pathlib import Path

import streamlit as st

PUMP_NAME = "Star Resorts & Service Station"
SHORT_NAME = "StarPump"
DEALER_TAG = "Bharat Petroleum Dealer"

STATIC_DIR = Path(__file__).parent.parent / "static"
BPCL_LOGO_PATH = STATIC_DIR / "bpcl_logo.png"


def _get_logo_b64() -> str | None:
    """Return base64-encoded logo if the file exists."""
    if BPCL_LOGO_PATH.exists():
        return base64.b64encode(BPCL_LOGO_PATH.read_bytes()).decode()
    return None


def _logo_img_tag(height: int = 48) -> str:
    """Return an <img> tag for the BPCL logo, or a styled text fallback."""
    b64 = _get_logo_b64()
    if b64:
        return f'<img src="data:image/png;base64,{b64}" height="{height}" style="object-fit: contain;" />'
    # Text fallback styled in BPCL colors (red shield + yellow/blue)
    return f"""
    <div style="display:inline-flex; align-items:center; gap:6px;">
        <div style="
            background: linear-gradient(180deg, #D42027 0%, #B71C1C 100%);
            color: #FFD600; font-weight: 900; font-size: {height * 0.35}px;
            width: {height}px; height: {height}px;
            border-radius: 6px; display: flex; align-items: center;
            justify-content: center; letter-spacing: -0.5px;
            border: 2px solid #FFD600;
        ">BP</div>
    </div>"""


def apply_theme():
    """Inject custom CSS for consistent branding across all pages."""
    st.markdown("""
    <style>
        /* ── Brand colors ─────────────────────────────────────── */
        :root {
            --brand-primary: #0F4C75;
            --brand-accent: #3282B8;
            --brand-light: #BBE1FA;
            --brand-dark: #1B262C;
            --brand-gold: #F0A500;
        }

        /* ── Sidebar styling ──────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0F4C75 0%, #1B262C 100%);
        }
        section[data-testid="stSidebar"] * {
            color: #E8E8E8 !important;
        }
        section[data-testid="stSidebar"] .stMetric label {
            color: #BBE1FA !important;
        }
        section[data-testid="stSidebar"] .stMetric [data-testid="stMetricValue"] {
            color: #FFFFFF !important;
        }
        section[data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,0.15) !important;
        }

        /* ── Metric cards ─────────────────────────────────────── */
        [data-testid="stMetric"] {
            background: #F8FAFE;
            border: 1px solid #E2EAF4;
            border-radius: 10px;
            padding: 16px 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        [data-testid="stMetric"] label {
            color: #5A6D80 !important;
            font-size: 0.8rem !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        [data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #0F4C75 !important;
            font-weight: 700 !important;
        }

        /* ── All primary/form buttons ─────────────────────────── */
        .stButton > button[kind="primary"],
        .stButton > button[kind="primaryFormSubmit"],
        .stFormSubmitButton > button,
        [data-testid="stFormSubmitButton"] > button,
        button[kind="primary"],
        button[kind="primaryFormSubmit"] {
            background: linear-gradient(135deg, #0F4C75, #3282B8) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            letter-spacing: 0.3px;
            transition: all 0.2s ease;
        }
        .stButton > button[kind="primary"]:hover,
        .stFormSubmitButton > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover {
            background: linear-gradient(135deg, #0D3F63, #2870A0) !important;
            box-shadow: 0 4px 12px rgba(15, 76, 117, 0.3) !important;
        }

        /* ── Secondary/default buttons ────────────────────────── */
        .stButton > button[kind="secondary"],
        .stButton > button:not([kind="primary"]):not([kind="primaryFormSubmit"]) {
            background: transparent !important;
            color: #0F4C75 !important;
            border: 1.5px solid #0F4C75 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease;
        }
        .stButton > button[kind="secondary"]:hover,
        .stButton > button:not([kind="primary"]):not([kind="primaryFormSubmit"]):hover {
            background: #0F4C75 !important;
            color: #FFFFFF !important;
        }

        /* ── Sidebar buttons ──────────────────────────────────── */
        section[data-testid="stSidebar"] .stButton > button {
            background: rgba(255,255,255,0.1) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(255,255,255,0.25) !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            backdrop-filter: blur(4px);
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(255,255,255,0.2) !important;
            border-color: rgba(255,255,255,0.4) !important;
        }

        /* ── Sidebar download button ──────────────────────────── */
        section[data-testid="stSidebar"] .stDownloadButton > button {
            background: linear-gradient(135deg, #F0A500, #E8890C) !important;
            color: #1B262C !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 700 !important;
        }
        section[data-testid="stSidebar"] .stDownloadButton > button:hover {
            background: linear-gradient(135deg, #E8990A, #D67A08) !important;
        }

        /* ── Data table ───────────────────────────────────────── */
        [data-testid="stDataFrame"] {
            border-radius: 10px;
            overflow: hidden;
        }

        /* ── Section headers ──────────────────────────────────── */
        .section-header {
            background: linear-gradient(135deg, #0F4C75, #3282B8);
            color: white !important;
            padding: 12px 20px;
            border-radius: 8px;
            margin-bottom: 16px;
            font-size: 1.1rem;
            font-weight: 600;
        }

        /* ── Info cards (containers) ──────────────────────────── */
        .block-container {
            padding-top: 2rem !important;
        }

        /* ── Branded badge ────────────────────────────────────── */
        .brand-badge {
            display: inline-block;
            background: linear-gradient(135deg, #F0A500, #E8890C);
            color: #1B262C !important;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }

        /* ── Fuel price tags ──────────────────────────────────── */
        .fuel-tag {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.85rem;
            margin: 4px 0;
        }
        .fuel-hsd { background: #FFF3CD; color: #856404; border: 1px solid #FFE69C; }
        .fuel-ms  { background: #D1ECF1; color: #0C5460; border: 1px solid #BEE5EB; }
        .fuel-xp  { background: #D4EDDA; color: #155724; border: 1px solid #C3E6CB; }

        /* ── Mobile responsive ────────────────────────────────── */
        @media (max-width: 768px) {
            .block-container {
                padding-top: 1rem !important;
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
            }
            [data-testid="stMetric"] {
                padding: 10px 14px;
            }
            .section-header {
                padding: 10px 14px;
                font-size: 0.95rem;
            }
            /* Page header responsive */
            .page-header-title {
                font-size: 1.2rem !important;
            }
            .page-header-pump {
                font-size: 0.72rem !important;
            }
            .page-header-dealer {
                display: none !important;
            }
            .page-header-logo {
                height: 30px !important;
            }
            .page-header-subtitle {
                font-size: 0.8rem !important;
            }
            /* Total bill card responsive */
            .total-bill-amount {
                font-size: 1.4rem !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    """Render a branded page header with BPCL logo."""
    b64 = _get_logo_b64()
    if b64:
        logo_html = f'<img src="data:image/png;base64,{b64}" class="page-header-logo" height="40" style="object-fit: contain;" />'
    else:
        logo_html = _logo_img_tag(40)

    st.markdown(f"""
    <div style="margin-bottom: 1.5rem;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 4px;">
            {logo_html}
            <div>
                <h1 class="page-header-title" style="margin: 0; padding: 0; font-size: 1.6rem; color: #0F4C75;
                           font-family: 'Source Sans Pro', 'Segoe UI', Roboto, sans-serif;
                           font-weight: 700; letter-spacing: -0.3px;">
                    {title}
                </h1>
                <span class="page-header-pump" style="color: #7A8B9A; font-size: 0.82rem;">{PUMP_NAME}</span>
                <span class="page-header-dealer" style="color: #B0B8C1; font-size: 0.7rem; margin-left: 6px;">| {DEALER_TAG}</span>
            </div>
        </div>
        {"<p class='page-header-subtitle' style='color: #5A6D80; margin-top: 4px; font-size: 0.9rem;'>" + subtitle + "</p>" if subtitle else ""}
    </div>
    """, unsafe_allow_html=True)


def setup_page():
    """Call at the top of every page: set_page_config + DB init + auth + theme + sidebar.
    Must be called before any other st.* call."""
    from lib.auth import require_login
    from lib.db import init_db

    st.set_page_config(
        page_title=f"StarPump | {PUMP_NAME}",
        page_icon="\u26fd",
        layout="wide",
    )
    init_db()
    require_login()
    apply_theme()
    sidebar_branding()


def section_header(text: str):
    """Render a styled section header."""
    st.markdown(f'<div class="section-header">{text}</div>', unsafe_allow_html=True)


def sidebar_branding():
    """Render the sidebar branding block with BPCL logo."""
    logo = _logo_img_tag(52)
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align: center; padding: 10px 0 5px 0;">
            {logo}
            <div style="font-size: 1rem; font-weight: 700; color: #FFFFFF; margin-top: 8px;">
                {PUMP_NAME}
            </div>
            <div style="font-size: 0.7rem; color: #FFD600; margin-top: 2px;
                         letter-spacing: 0.5px; font-weight: 600;">
                {DEALER_TAG}
            </div>
            <div style="margin-top: 8px;">
                <span class="brand-badge">Bill Tracker</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("")
