"""Fuel price management and settings."""

import streamlit as st
import pandas as pd

from lib.ui import page_header
from lib.auth import get_current_user
from lib import models

page_header("Settings", "Manage fuel prices, parties, and preferences")

# ── Fuel Prices ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Fuel Prices</div>', unsafe_allow_html=True)
st.caption("Update prices when they change. New prices apply to future entries only.")

prices = models.get_current_prices()

with st.form("fuel_prices_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        hsd_rate = st.number_input("HSD (Diesel) \u20b9/ltr",
                                    value=prices.get("HSD", 0.0), format="%.2f", min_value=0.0)
    with col2:
        ms_rate = st.number_input("MS (Petrol) \u20b9/ltr",
                                   value=prices.get("MS", 0.0), format="%.2f", min_value=0.0)
    with col3:
        xp_rate = st.number_input("XP (Premium) \u20b9/ltr",
                                   value=prices.get("XP", 0.0), format="%.2f", min_value=0.0)

    if st.form_submit_button("Update Prices", use_container_width=True, type="primary"):
        user = get_current_user()
        updated = []
        if hsd_rate > 0 and hsd_rate != prices.get("HSD", 0.0):
            models.set_fuel_price("HSD", hsd_rate, user)
            updated.append("HSD")
        if ms_rate > 0 and ms_rate != prices.get("MS", 0.0):
            models.set_fuel_price("MS", ms_rate, user)
            updated.append("MS")
        if xp_rate > 0 and xp_rate != prices.get("XP", 0.0):
            models.set_fuel_price("XP", xp_rate, user)
            updated.append("XP")

        if updated:
            st.success(f"Updated: {', '.join(updated)}")
            st.rerun()
        else:
            st.info("No price changes detected.")

# ── Price History ────────────────────────────────────────────────────────────
st.markdown("")
with st.expander("Price Change History"):
    history = models.get_price_history()
    if history:
        df = pd.DataFrame(history)
        df.columns = ["Fuel Type", "Rate (\u20b9)", "Effective From", "Set By"]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No price history yet.")

# ── Manage Parties ───────────────────────────────────────────────────────────
st.markdown("")
st.markdown('<div class="section-header">Manage Parties</div>', unsafe_allow_html=True)
st.caption("Add a new party with an optional carry-forward balance from previous records.")

col1, col2, col3 = st.columns([3, 2, 1], gap="medium", vertical_alignment="bottom")
with col1:
    new_party = st.text_input("Party Name", placeholder="e.g., UCS, ABC Transport",
                               label_visibility="collapsed", key="new_party_name")
with col2:
    opening_bal = st.number_input("Opening Balance (\u20b9)", value=0.0, format="%.2f",
                                   label_visibility="collapsed", key="opening_bal",
                                   help="Carry-forward balance from previous records. Leave 0 if none.")
with col3:
    add_clicked = st.button("Add Party", use_container_width=True, type="primary")

if add_clicked:
    if new_party.strip():
        try:
            models.add_party(new_party)
            if opening_bal != 0:
                models.add_opening_balance(new_party, opening_bal, get_current_user())
            st.success(
                f"Party **{new_party.strip().upper()}** added!"
                + (f" Opening balance: \u20b9{opening_bal:,.2f}" if opening_bal != 0 else "")
            )
            st.rerun()
        except Exception as e:
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                st.warning("Party already exists.")
            else:
                st.error(f"Error: {e}")
    else:
        st.error("Enter a party name.")

# ── Current Parties ──────────────────────────────────────────────────────────
parties = models.get_all_parties()
if parties:
    st.markdown("")
    st.markdown("**Current Parties**")
    for row_start in range(0, len(parties), 3):
        row_parties = parties[row_start:row_start + 3]
        party_cols = st.columns(3)
        for i, p in enumerate(row_parties):
            with party_cols[i]:
                bal = models.get_previous_balance(p)
                st.metric(p, f"\u20b9{bal:,.2f}")

    # Set opening balance for existing parties with no entries
    st.markdown("")
    with st.expander("Set Opening Balance for Existing Party"):
        st.caption(
            "Use this if you added a party but forgot to set the carry-forward balance. "
            "Only works for parties with no bill entries yet."
        )
        cf_party = st.selectbox("Select Party", parties, key="cf_party")
        cf_amount = st.number_input("Carry Forward Balance (\u20b9)", value=0.0,
                                     format="%.2f", key="cf_amount")
        if st.button("Set Opening Balance", type="primary", key="cf_save"):
            if cf_amount == 0:
                st.error("Enter a balance amount.")
            else:
                try:
                    models.add_opening_balance(cf_party, cf_amount, get_current_user())
                    st.success(f"Opening balance of \u20b9{cf_amount:,.2f} set for **{cf_party}**.")
                    st.rerun()
                except ValueError as e:
                    st.warning(str(e))
                except Exception as e:
                    st.error(f"Error: {e}")
