"""Home dashboard — party balances and fuel prices overview."""

from datetime import datetime

import streamlit as st

from lib.ui import page_header
from lib import models

page_header("Dashboard", "Overview of all party balances and fuel prices")

# ── First week reminder ──────────────────────────────────────────────────────
today = datetime.now()
if today.day <= 7:
    prev_month = today.month - 1 if today.month > 1 else 12
    prev_year = today.year if today.month > 1 else today.year - 1
    month_name = datetime(prev_year, prev_month, 1).strftime("%B %Y")

    st.warning(
        f"**Monthly Reminder:** Please download the ledger for all parties "
        f"for **{month_name}** before the 7th. "
        f"Go to **View Ledger** → select a party → choose the date range → download.",
        icon="\U0001f4e5",
    )
    st.markdown("")

# ── Content ──────────────────────────────────────────────────────────────────
balances = models.get_all_balances()
prices = models.get_current_prices()

if not balances and not prices:
    st.info(
        "Welcome! Get started by setting fuel prices in **Settings** "
        "and adding your first bill entry."
    )
else:
    # Fuel prices row
    if prices:
        st.markdown("**Current Fuel Prices**")
        pcols = st.columns(3)
        fuel_labels = {"HSD": "HSD (Diesel)", "MS": "MS (Petrol)", "XP": "XP (Premium)"}
        for i, ft in enumerate(["HSD", "MS", "XP"]):
            with pcols[i]:
                rate = prices.get(ft)
                if rate:
                    st.metric(fuel_labels[ft], f"\u20b9{rate:,.2f}/ltr")
                else:
                    st.metric(fuel_labels[ft], "Not set")
        st.markdown("")

    # Party balances — rows of 3
    if balances:
        st.markdown("**Party Balances**")
        items = list(balances.items())
        for row_start in range(0, len(items), 3):
            row = items[row_start:row_start + 3]
            cols = st.columns(3)
            for i, (party, balance) in enumerate(row):
                with cols[i]:
                    if balance > 0:
                        st.metric(party, f"\u20b9{balance:,.2f}", delta="Owes", delta_color="inverse")
                    elif balance < 0:
                        st.metric(party, f"\u20b9{abs(balance):,.2f}", delta="Overpaid", delta_color="normal")
                    else:
                        st.metric(party, "\u20b90.00", delta="Settled")
    else:
        st.info("No parties yet. Add one from **Manual Entry** or **Upload Bill**.")
