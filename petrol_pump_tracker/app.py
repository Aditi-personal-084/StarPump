"""
Petrol Pump Bill Tracker - Streamlit App
Upload daily bill images, extract data via EasyOCR (free, no API key),
maintain Excel ledger with running balances per party.
"""

import streamlit as st
from pathlib import Path

from bill_extractor import extract_bill_data
from excel_manager import (
    add_bill_entry,
    get_party_ledger,
    get_all_parties,
    get_all_balances,
    get_previous_balance,
    delete_last_entry,
    EXCEL_FILE,
)

UPLOAD_DIR = Path(__file__).parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def main():
    st.set_page_config(
        page_title="Petrol Pump Bill Tracker",
        page_icon="⛽",
        layout="wide",
    )

    st.title("⛽ Petrol Pump Bill Tracker")
    st.caption("Upload daily bills → Auto-extract data (EasyOCR - no API key needed) → Maintain party-wise Excel ledger")

    # Sidebar - Party Management
    with st.sidebar:
        # Party management
        st.header("Manage Parties")
        existing_parties = get_all_parties()

        new_party = st.text_input("Add New Party", placeholder="e.g., UCS, ABC Transport")
        if st.button("Add Party", use_container_width=True) and new_party:
            from excel_manager import _ensure_workbook, _ensure_party_sheet
            wb = _ensure_workbook()
            _ensure_party_sheet(wb, new_party)
            from excel_manager import EXCEL_FILE as ef
            wb.save(ef)
            wb.close()
            st.success(f"Party '{new_party.upper()}' added!")
            st.rerun()

        if existing_parties:
            st.divider()
            st.subheader("Current Balances")
            balances = get_all_balances()
            for party, balance in balances.items():
                if balance > 0:
                    st.metric(party, f"₹{balance:,.2f}", delta="Owes", delta_color="inverse")
                elif balance < 0:
                    st.metric(party, f"₹{abs(balance):,.2f}", delta="Overpaid", delta_color="normal")
                else:
                    st.metric(party, "₹0.00", delta="Settled")

        st.divider()
        if EXCEL_FILE.exists():
            with open(EXCEL_FILE, "rb") as f:
                st.download_button(
                    "📥 Download Excel Ledger",
                    data=f.read(),
                    file_name="petrol_pump_ledger.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

    # Main content - Tabs
    tab1, tab2, tab3 = st.tabs(["📸 Upload Bill", "📊 View Ledger", "✏️ Manual Entry"])

    # ==================== TAB 1: Upload Bill ====================
    with tab1:
        st.subheader("Upload Bill Image")

        uploaded_file = st.file_uploader(
            "Upload a bill image",
            type=["jpg", "jpeg", "png", "webp"],
            help="Take a photo of the daily bill and upload it here",
        )

        if uploaded_file:
            col1, col2 = st.columns([1, 1])

            with col1:
                st.image(uploaded_file, caption="Uploaded Bill", use_container_width=True)

            with col2:
                if st.button("🔍 Extract Bill Data", use_container_width=True, type="primary"):
                    save_path = UPLOAD_DIR / uploaded_file.name
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    with st.spinner("Extracting data from bill using EasyOCR (first run downloads model ~100MB)..."):
                        try:
                            extracted = extract_bill_data(str(save_path))
                            st.session_state.extracted_data = extracted
                            st.success("Data extracted successfully!")
                            if extracted.get("raw_text"):
                                with st.expander("Raw OCR Text (for verification)"):
                                    for line in extracted["raw_text"]:
                                        st.text(line)
                        except Exception as e:
                            st.error(f"Error extracting data: {e}")

        # Show extracted data for review/edit
        if "extracted_data" in st.session_state and st.session_state.extracted_data:
            st.divider()
            st.subheader("Review & Confirm Extracted Data")
            st.caption("Edit any field below before saving. OCR may not be 100% accurate on handwritten bills.")

            data = st.session_state.extracted_data

            col1, col2 = st.columns(2)

            with col1:
                # Party selection/input
                parties = get_all_parties()
                party_options = parties + ["-- New Party --"]

                if data.get("party_name") and data["party_name"].strip().upper() in [p.upper() for p in parties]:
                    default_idx = next(
                        i for i, p in enumerate(parties)
                        if p.upper() == data["party_name"].strip().upper()
                    )
                else:
                    default_idx = len(party_options) - 1

                selected_party = st.selectbox("Party Name", party_options, index=default_idx)

                if selected_party == "-- New Party --":
                    party_name = st.text_input(
                        "Enter Party Name",
                        value=data.get("party_name") or "",
                    )
                else:
                    party_name = selected_party

                date = st.text_input("Date (DD/MM/YYYY)", value=data.get("date") or "")
                vehicle_no = st.text_input("Vehicle No", value=data.get("vehicle_no") or "")
                fuel_type = st.selectbox(
                    "Fuel Type",
                    ["HSD", "MS", "XP"],
                    index=["HSD", "MS", "XP"].index(data.get("fuel_type", "HSD") or "HSD"),
                )

            with col2:
                litres = st.number_input("Litres", value=float(data.get("litres") or 0), format="%.2f")
                rate = st.number_input(
                    "Rate per Litre (₹)",
                    value=float(data.get("rate_per_litre") or 0),
                    format="%.2f",
                )
                fuel_amount = st.number_input(
                    "Fuel Amount (₹)",
                    value=float(data.get("fuel_amount") or data.get("bill_amount") or 0),
                    format="%.2f",
                    help="Cost of fuel only (e.g. 15,000)",
                )
                cash_to_driver = st.number_input(
                    "Cash Given to Driver (₹)",
                    value=float(data.get("cash_to_driver") or 0),
                    format="%.2f",
                    help="Extra cash given to the driver (e.g. 2,000)",
                )
                payment_received = st.number_input(
                    "Payment Received from Party (₹)",
                    value=0.0,
                    format="%.2f",
                    help="If the party paid anything back today",
                )
                notes = st.text_input("Notes", value=data.get("notes") or "")

            # Show bill breakdown & balance preview
            total_bill = fuel_amount + cash_to_driver
            st.divider()

            st.subheader(f"Total Bill: ₹{total_bill:,.2f}")
            st.caption(f"Fuel ₹{fuel_amount:,.2f} + Cash to Driver ₹{cash_to_driver:,.2f}")

            if party_name:
                prev_bal = get_previous_balance(party_name)
                new_bal = prev_bal + total_bill - payment_received

                bcol1, bcol2, bcol3 = st.columns(3)
                bcol1.metric("Previous Balance", f"₹{prev_bal:,.2f}")
                bcol2.metric("+ Total Bill - Payment", f"₹{total_bill:,.2f} - ₹{payment_received:,.2f}")
                bcol3.metric("New Balance", f"₹{new_bal:,.2f}")

            if st.button("✅ Save to Excel", use_container_width=True, type="primary"):
                if not party_name:
                    st.error("Please enter a party name.")
                elif not date:
                    st.error("Please enter the date.")
                elif fuel_amount <= 0 and cash_to_driver <= 0:
                    st.error("Fuel amount or cash to driver must be greater than 0.")
                else:
                    try:
                        result = add_bill_entry(
                            party_name=party_name,
                            date=date,
                            vehicle_no=vehicle_no or "",
                            fuel_type=fuel_type or "HSD",
                            litres=litres or 0,
                            rate_per_litre=rate if rate > 0 else None,
                            fuel_amount=fuel_amount,
                            cash_to_driver=cash_to_driver,
                            payment_received=payment_received,
                            notes=notes or "",
                        )
                        st.success(
                            f"Entry #{result['serial_no']} saved for {party_name}! "
                            f"Total Bill: ₹{result['total_bill']:,.2f} | "
                            f"New Balance: ₹{result['new_balance']:,.2f}"
                        )
                        st.session_state.extracted_data = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving entry: {e}")

    # ==================== TAB 2: View Ledger ====================
    with tab2:
        st.subheader("Party Ledger")

        parties = get_all_parties()
        if not parties:
            st.info("No parties added yet. Add a party from the sidebar or upload a bill.")
        else:
            selected = st.selectbox("Select Party", parties, key="ledger_party")

            if selected:
                df = get_party_ledger(selected)

                if df.empty:
                    st.info(f"No entries yet for {selected}.")
                else:
                    # Summary metrics
                    mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)
                    total_litres = df["Litres"].sum() if "Litres" in df.columns else 0
                    total_fuel = df["Fuel Amount"].sum() if "Fuel Amount" in df.columns else 0
                    total_cash_driver = df["Cash to Driver"].sum() if "Cash to Driver" in df.columns else 0
                    total_billed = df["Total Bill"].sum() if "Total Bill" in df.columns else 0
                    current_bal = get_previous_balance(selected)

                    mcol1.metric("Total Litres", f"{total_litres:,.2f}")
                    mcol2.metric("Total Fuel Amount", f"₹{total_fuel:,.2f}")
                    mcol3.metric("Total Cash to Drivers", f"₹{total_cash_driver:,.2f}")
                    mcol4.metric("Total Billed", f"₹{total_billed:,.2f}")
                    mcol5.metric("Current Balance", f"₹{current_bal:,.2f}")

                    st.dataframe(df, use_container_width=True, hide_index=True)

                # Undo last entry
                st.divider()
                if st.button("🗑️ Delete Last Entry (Undo)", key="undo"):
                    if delete_last_entry(selected):
                        st.success("Last entry deleted.")
                        st.rerun()
                    else:
                        st.warning("No entries to delete.")

    # ==================== TAB 3: Manual Entry ====================
    with tab3:
        st.subheader("Manual Bill Entry")
        st.caption("Enter bill details manually without uploading an image.")

        # Show last save result if any
        if "last_save_result" in st.session_state:
            r = st.session_state.last_save_result
            st.success(
                f"Entry #{r['serial_no']} saved for {r['party_name']}! "
                f"Total Bill: ₹{r['total_bill']:,.2f} | "
                f"New Balance: ₹{r['new_balance']:,.2f}"
            )
            del st.session_state.last_save_result

        parties = get_all_parties()

        with st.form("manual_entry_form", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                if parties:
                    party_options = parties + ["-- New Party --"]
                    selected_party = st.selectbox("Party Name", party_options)
                else:
                    selected_party = None

                m_new_party = st.text_input(
                    "New Party Name" if parties else "Party Name",
                    placeholder="e.g., UCS, ABC Transport",
                )
                m_date = st.text_input("Date (DD/MM/YYYY)")
                m_vehicle = st.text_input("Vehicle No")
                m_fuel = st.selectbox("Fuel Type", ["HSD", "MS", "XP"])

            with col2:
                m_litres = st.number_input("Litres", value=0.0, format="%.2f")
                m_rate = st.number_input("Rate/Ltr (₹)", value=0.0, format="%.2f")
                m_fuel_amount = st.number_input(
                    "Fuel Amount (₹)", value=0.0, format="%.2f",
                    help="Cost of fuel only (e.g. 15,000)",
                )
                m_cash_driver = st.number_input(
                    "Cash Given to Driver (₹)", value=0.0, format="%.2f",
                    help="Extra cash given to the driver (e.g. 2,000)",
                )
                m_payment = st.number_input(
                    "Payment Received from Party (₹)", value=0.0, format="%.2f",
                    help="If the party paid anything back today",
                )

            m_notes = st.text_input("Notes")

            submitted = st.form_submit_button(
                "💾 Save Manual Entry", use_container_width=True, type="primary"
            )

            if submitted:
                # Determine party name
                if m_new_party.strip():
                    m_party = m_new_party.strip()
                elif selected_party and selected_party != "-- New Party --":
                    m_party = selected_party
                else:
                    m_party = ""

                if not m_party:
                    st.error("Please enter a party name.")
                elif not m_date:
                    st.error("Please enter the date.")
                elif m_fuel_amount <= 0 and m_cash_driver <= 0:
                    st.error("Fuel amount or cash to driver must be greater than 0.")
                else:
                    try:
                        result = add_bill_entry(
                            party_name=m_party,
                            date=m_date,
                            vehicle_no=m_vehicle or "",
                            fuel_type=m_fuel or "HSD",
                            litres=m_litres or 0,
                            rate_per_litre=m_rate if m_rate > 0 else None,
                            fuel_amount=m_fuel_amount,
                            cash_to_driver=m_cash_driver,
                            payment_received=m_payment,
                            notes=m_notes or "",
                        )
                        st.session_state.last_save_result = result
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving: {e}")


if __name__ == "__main__":
    main()
