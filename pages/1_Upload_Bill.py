"""Upload bill image, OCR extract, review, and save."""

import tempfile

import streamlit as st

from lib.ui import page_header
from lib.auth import get_current_user
from lib.bill_extractor import extract_bill_data
from lib import models
from lib.validators import parse_date, sanitize_vehicle_no, sanitize_text

page_header("Upload Bill", "Scan a bill image and auto-extract details with OCR")

uploaded_file = st.file_uploader(
    "Upload a bill image",
    type=["jpg", "jpeg", "png", "webp"],
    help="Take a photo of the daily bill and upload it here",
)

if uploaded_file:
    col1, col2 = st.columns([1, 1], gap="medium")

    with col1:
        st.image(uploaded_file, caption="Uploaded Bill", use_container_width=True)

    with col2:
        st.markdown("")
        if st.button("Extract Bill Data", use_container_width=True, type="primary"):
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(uploaded_file.getbuffer())
                tmp_path = tmp.name

            with st.spinner("Extracting data with OCR..."):
                try:
                    extracted = extract_bill_data(tmp_path)
                    st.session_state.extracted_data = extracted
                    st.success("Data extracted!")
                    if extracted.get("raw_text"):
                        with st.expander("Raw OCR Text"):
                            for line in extracted["raw_text"]:
                                st.text(line)
                except Exception as e:
                    st.error(f"OCR error: {e}")

# ── Review & Save ────────────────────────────────────────────────────────────
if "extracted_data" in st.session_state and st.session_state.extracted_data:
    st.divider()
    st.markdown('<div class="section-header">Review & Confirm Extracted Data</div>',
                unsafe_allow_html=True)
    st.caption("Edit any field before saving. OCR may not be 100% accurate.")

    data = st.session_state.extracted_data
    prices = models.get_current_prices()

    # Track validation errors
    ub_errors = {}
    if "upload_errors" in st.session_state:
        ub_errors = st.session_state.upload_errors
        del st.session_state.upload_errors

    col1, col2 = st.columns(2, gap="medium")

    with col1:
        parties = models.get_all_parties()
        party_options = parties + ["-- New Party --"]

        if data.get("party_name") and data["party_name"].strip().upper() in [
            p.upper() for p in parties
        ]:
            default_idx = next(
                i for i, p in enumerate(parties)
                if p.upper() == data["party_name"].strip().upper()
            )
        else:
            default_idx = len(party_options) - 1

        selected_party = st.selectbox("Party Name", party_options, index=default_idx)

        if selected_party == "-- New Party --":
            party_name = st.text_input("Enter Party Name", value=data.get("party_name") or "")
        else:
            party_name = selected_party
        if "party" in ub_errors:
            st.error(ub_errors["party"])

        date_str = st.text_input("Date (DD/MM/YYYY)", value=data.get("date") or "")
        if "date" in ub_errors:
            st.error(ub_errors["date"])

        vehicle_no = st.text_input("Vehicle No", value=data.get("vehicle_no") or "")

        detected_ft = data.get("fuel_type", "HSD") or "HSD"
        fuel_types = ["HSD", "MS", "XP"]
        fuel_type = st.selectbox(
            "Fuel Type", fuel_types,
            index=fuel_types.index(detected_ft) if detected_ft in fuel_types else 0,
        )

    with col2:
        default_rate = prices.get(fuel_type, 0.0)
        ocr_rate = data.get("rate_per_litre") or default_rate

        litres = st.number_input("Litres", value=float(data.get("litres") or 0), format="%.2f",
                                  key="ub_litres")
        rate = st.number_input("Rate/Ltr (\u20b9)", value=float(ocr_rate), format="%.2f",
                                key="ub_rate")

        # Auto-calculate fuel amount reactively
        auto_amount = round(litres * rate, 2) if litres > 0 and rate > 0 else 0.0

        fuel_amount = st.number_input(
            "Fuel Amount (\u20b9)", value=auto_amount, format="%.2f",
            key=f"ub_fuel_amt_{litres}_{rate}",
            help="Auto-calculated from Litres x Rate. You can override.",
        )
        cash_to_driver = st.number_input("Cash to Driver (\u20b9)",
                                          value=float(data.get("cash_to_driver") or 0), format="%.2f",
                                          key="ub_cash")
        payment_received = st.number_input("Payment Received (\u20b9)", value=0.0, format="%.2f",
                                            key="ub_payment")

        # Payment mode dropdown — shown when payment > 0
        PAYMENT_MODES = ["CASH", "BANK EDFS", "BANK ACCOUNT SBI", "PAYTM", "HDFC"]
        ub_payment_mode = ""
        if payment_received > 0:
            ub_payment_mode = st.selectbox("Payment Mode", PAYMENT_MODES, key="ub_payment_mode")
            if "payment_mode" in ub_errors:
                st.error(ub_errors["payment_mode"])

        notes = st.text_input("Notes", value=data.get("notes") or "", key="ub_notes")

    # Balance preview
    total_bill = fuel_amount + cash_to_driver
    st.divider()

    st.markdown(f"""
    <div style="text-align: center; padding: 12px; background: #F0F7FF; border-radius: 10px; border: 1px solid #D0E2F4;">
        <div style="font-size: 0.8rem; color: #5A6D80; text-transform: uppercase; letter-spacing: 0.5px;">Total Bill</div>
        <div class="total-bill-amount" style="font-size: 1.8rem; font-weight: 700; color: #0F4C75;">\u20b9{total_bill:,.2f}</div>
        <div style="font-size: 0.8rem; color: #7A8B9A;">
            Fuel \u20b9{fuel_amount:,.2f} + Cash to Driver \u20b9{cash_to_driver:,.2f}
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("")

    if party_name:
        prev_bal = models.get_previous_balance(party_name)
        new_bal = prev_bal + total_bill - payment_received
        bcol1, bcol2, bcol3 = st.columns(3)
        bcol1.metric("Previous Balance", f"\u20b9{prev_bal:,.2f}")
        bcol2.metric("This Entry", f"+\u20b9{total_bill:,.2f} -\u20b9{payment_received:,.2f}")
        bcol3.metric("New Balance", f"\u20b9{new_bal:,.2f}")

    st.markdown("")
    if st.button("Save to Ledger", use_container_width=True, type="primary"):
        # Validate and collect errors
        validation_errors = {}
        if not party_name:
            validation_errors["party"] = "Please enter a party name."
        if not date_str:
            validation_errors["date"] = "Please enter the date (DD/MM/YYYY)."
        else:
            try:
                parse_date(date_str)
            except ValueError:
                validation_errors["date"] = "Invalid date format. Use DD/MM/YYYY."
        if fuel_amount <= 0 and cash_to_driver <= 0 and payment_received <= 0:
            validation_errors["amount"] = "Fuel amount, cash to driver, or payment received must be > 0."
        if payment_received > 0 and not ub_payment_mode:
            validation_errors["payment_mode"] = "Please select a payment mode."

        if validation_errors:
            st.session_state.upload_errors = validation_errors
            st.rerun()
        else:
            try:
                entry_date = parse_date(date_str)
                result = models.add_bill_entry(
                    party_name=party_name,
                    entry_date=entry_date,
                    vehicle_no=sanitize_vehicle_no(vehicle_no),
                    fuel_type=fuel_type,
                    litres=litres,
                    rate_per_litre=rate if rate > 0 else None,
                    fuel_amount=fuel_amount,
                    cash_to_driver=cash_to_driver,
                    payment_received=payment_received,
                    notes=sanitize_text(notes),
                    created_by=get_current_user(),
                    payment_mode=ub_payment_mode,
                )
                st.success(
                    f"Entry #{result['serial_no']} saved for {result['party_name']}! "
                    f"New Balance: \u20b9{result['new_balance']:,.2f}"
                )
                st.session_state.extracted_data = None
                st.rerun()
            except Exception as e:
                st.error(f"Error saving: {e}")
