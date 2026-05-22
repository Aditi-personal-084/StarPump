"""Manual bill entry without image upload."""

import streamlit as st

from lib.ui import page_header
from lib.auth import get_current_user
from lib import models
from lib.validators import parse_date, sanitize_vehicle_no, sanitize_text

page_header("Manual Entry", "Enter bill details manually without uploading an image")

# Show last save result
if "last_save_result" in st.session_state:
    r = st.session_state.last_save_result
    st.success(
        f"Entry #{r['serial_no']} saved for {r['party_name']}! "
        f"Total Bill: \u20b9{r['total_bill']:,.2f} | "
        f"New Balance: \u20b9{r['new_balance']:,.2f}"
    )
    del st.session_state.last_save_result

parties = models.get_all_parties()
prices = models.get_current_prices()

# Track validation errors
errors = {}
if "manual_errors" in st.session_state:
    errors = st.session_state.manual_errors
    del st.session_state.manual_errors

col1, col2 = st.columns(2, gap="medium")

with col1:
    st.markdown("**Party & Vehicle Details**")

    if parties:
        party_options = parties + ["-- New Party --"]
        selected_party = st.selectbox("Party Name", party_options, key="me_party_select")
    else:
        selected_party = None

    new_party = st.text_input(
        "New Party Name" if parties else "Party Name",
        placeholder="e.g., UCS, ABC Transport",
        key="me_new_party",
    )
    if "party" in errors:
        st.error(errors["party"])

    m_date = st.text_input("Date (DD/MM/YYYY)", key="me_date")
    if "date" in errors:
        st.error(errors["date"])

    m_vehicle = st.text_input("Vehicle No", key="me_vehicle")

    fuel_types = ["HSD", "MS", "XP"]
    m_fuel_type = st.selectbox("Fuel Type", fuel_types, key="me_fuel_type")

with col2:
    st.markdown("**Amounts**")

    default_rate = prices.get(m_fuel_type, 0.0)
    m_litres = st.number_input("Litres", value=0.0, format="%.2f", key="me_litres")
    m_rate = st.number_input("Rate/Ltr (\u20b9)", value=default_rate, format="%.2f",
                              key="me_rate", help="Auto-filled from current fuel price.")

    # Auto-calculate fuel amount
    auto_amount = round(m_litres * m_rate, 2) if m_litres > 0 and m_rate > 0 else 0.0

    m_fuel_amount = st.number_input(
        "Fuel Amount (\u20b9)", value=auto_amount, format="%.2f",
        key=f"me_fuel_amt_{m_litres}_{m_rate}",
        help="Auto-calculated from Litres x Rate. You can override.",
    )

    m_cash_driver = st.number_input("Cash to Driver (\u20b9)", value=0.0, format="%.2f",
                                     key="me_cash")
    m_payment = st.number_input("Payment Received (\u20b9)", value=0.0, format="%.2f",
                                 key="me_payment")
    if "amount" in errors:
        st.error(errors["amount"])

m_notes = st.text_input("Notes", key="me_notes")

# Show total preview
total_bill = m_fuel_amount + m_cash_driver
if total_bill > 0:
    st.divider()
    st.markdown(f"""
    <div style="text-align: center; padding: 12px; background: #F0F7FF; border-radius: 10px; border: 1px solid #D0E2F4;">
        <div style="font-size: 0.8rem; color: #5A6D80; text-transform: uppercase;">Total Bill</div>
        <div class="total-bill-amount" style="font-size: 1.8rem; font-weight: 700; color: #0F4C75;">\u20b9{total_bill:,.2f}</div>
        <div style="font-size: 0.8rem; color: #7A8B9A;">
            Fuel \u20b9{m_fuel_amount:,.2f} + Cash to Driver \u20b9{m_cash_driver:,.2f}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Balance preview
    m_party = ""
    if new_party.strip():
        m_party = new_party.strip()
    elif selected_party and selected_party != "-- New Party --":
        m_party = selected_party

    if m_party:
        prev_bal = models.get_previous_balance(m_party)
        new_bal = prev_bal + total_bill - m_payment
        st.markdown("")
        bcol1, bcol2, bcol3 = st.columns(3)
        bcol1.metric("Previous Balance", f"\u20b9{prev_bal:,.2f}")
        bcol2.metric("This Entry", f"+\u20b9{total_bill:,.2f} -\u20b9{m_payment:,.2f}")
        bcol3.metric("New Balance", f"\u20b9{new_bal:,.2f}")

st.markdown("")
if st.button("Save Entry", use_container_width=True, type="primary"):
    # Determine party name
    if new_party.strip():
        m_party = new_party.strip()
    elif selected_party and selected_party != "-- New Party --":
        m_party = selected_party
    else:
        m_party = ""

    fuel_amount = m_fuel_amount

    # Validate and collect errors
    validation_errors = {}
    if not m_party:
        validation_errors["party"] = "Please enter a party name."
    if not m_date:
        validation_errors["date"] = "Please enter the date (DD/MM/YYYY)."
    else:
        try:
            parse_date(m_date)
        except ValueError:
            validation_errors["date"] = "Invalid date format. Use DD/MM/YYYY."
    if fuel_amount <= 0 and m_cash_driver <= 0:
        validation_errors["amount"] = "Fuel amount or cash to driver must be > 0."

    if validation_errors:
        st.session_state.manual_errors = validation_errors
        st.rerun()
    else:
        try:
            entry_date = parse_date(m_date)
            result = models.add_bill_entry(
                party_name=m_party,
                entry_date=entry_date,
                vehicle_no=sanitize_vehicle_no(m_vehicle),
                fuel_type=m_fuel_type,
                litres=m_litres,
                rate_per_litre=m_rate if m_rate > 0 else None,
                fuel_amount=fuel_amount,
                cash_to_driver=m_cash_driver,
                payment_received=m_payment,
                notes=sanitize_text(m_notes),
                created_by=get_current_user(),
            )
            st.session_state.last_save_result = result
            st.rerun()
        except Exception as e:
            st.error(f"Error saving: {e}")
