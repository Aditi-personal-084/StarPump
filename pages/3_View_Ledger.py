"""View party ledger with date filters, download, and soft-delete undo."""

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

import streamlit as st

from lib.ui import page_header
from lib.auth import get_current_user
from lib import models
from lib.export import generate_party_excel

page_header("View Ledger", "Party-wise transaction history and balances")

parties = models.get_all_parties()

if not parties:
    st.info("No parties yet. Add one from **Manual Entry** or **Upload Bill**.")
else:
    selected = st.selectbox("Select Party", parties)

    if selected:
        # ── Date range filter ────────────────────────────────────────────────
        st.markdown("")
        st.markdown("**Date Range**")

        today = date.today()
        last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_month_end = today.replace(day=1) - timedelta(days=1)

        presets = {
            "All Time": (None, None),
            "Last 15 Days": (today - timedelta(days=15), today),
            "This Month": (today.replace(day=1), today),
            "Last Month": (last_month_start, last_month_end),
            "Last 3 Months": (today - relativedelta(months=3), today),
            "Last 6 Months": (today - relativedelta(months=6), today),
            "Custom": ("custom", "custom"),
        }

        preset_names = list(presets.keys())
        selected_preset = st.selectbox(
            "Quick Select", preset_names, index=0,
            label_visibility="collapsed", key="ledger_preset",
        )

        date_from, date_to = presets[selected_preset]

        if selected_preset == "Custom":
            dcol1, dcol2 = st.columns(2)
            with dcol1:
                date_from = st.date_input("From", value=today.replace(day=1), key="ledger_from")
            with dcol2:
                date_to = st.date_input("To", value=today, key="ledger_to")

        # ── Fetch data ───────────────────────────────────────────────────────
        df = models.get_party_ledger(selected, date_from=date_from, date_to=date_to)

        if df.empty:
            st.info(f"No entries for **{selected}** in the selected period.")
        else:
            # Summary metrics
            total_litres = df["Litres"].sum() if "Litres" in df.columns else 0
            total_fuel = df["Fuel Amount"].sum() if "Fuel Amount" in df.columns else 0
            total_cash = df["Cash to Driver"].sum() if "Cash to Driver" in df.columns else 0
            total_billed = df["Total Bill"].sum() if "Total Bill" in df.columns else 0
            current_bal = models.get_previous_balance(selected)

            mcol1, mcol2, mcol3 = st.columns(3)
            mcol1.metric("Total Litres", f"{total_litres:,.2f}")
            mcol2.metric("Total Fuel", f"\u20b9{total_fuel:,.2f}")
            mcol3.metric("Cash to Drivers", f"\u20b9{total_cash:,.2f}")

            total_payments = df["Payment Received"].sum() if "Payment Received" in df.columns else 0

            mcol4, mcol5, mcol6 = st.columns(3)
            mcol4.metric("Total Billed", f"\u20b9{total_billed:,.2f}")
            mcol5.metric("Total Payments", f"\u20b9{total_payments:,.2f}")
            mcol6.metric("Current Balance", f"\u20b9{current_bal:,.2f}")

            # Payment Mode Breakdown
            mode_summary = models.get_payment_mode_summary(selected, date_from=date_from, date_to=date_to)
            if mode_summary:
                st.markdown("**Payment Mode Breakdown**")
                mode_cols = st.columns(len(mode_summary))
                for i, (mode, total) in enumerate(mode_summary.items()):
                    mode_cols[i].metric(mode, f"\u20b9{total:,.2f}")

            # Payment Reminder Message
            if current_bal > 0:
                with st.expander("Payment Reminder Message"):
                    reminder = (
                        f"Dear {selected},\n\n"
                        f"This is a gentle reminder from Star Pump regarding your outstanding balance.\n\n"
                        f"Outstanding Amount: Rs. {current_bal:,.2f}\n"
                        f"As on: {today.strftime('%d/%m/%Y')}\n\n"
                        f"Kindly arrange the payment at your earliest convenience.\n\n"
                        f"Thank you,\nStar Pump"
                    )
                    st.code(reminder, language="text")

            st.markdown("")
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "S.No": st.column_config.NumberColumn(width="small"),
                    "Date": st.column_config.TextColumn(width="small"),
                    "Fuel Amount": st.column_config.NumberColumn(format="\u20b9%.2f"),
                    "Cash to Driver": st.column_config.NumberColumn(format="\u20b9%.2f"),
                    "Total Bill": st.column_config.NumberColumn(format="\u20b9%.2f"),
                    "Payment Received": st.column_config.NumberColumn(format="\u20b9%.2f"),
                    "Balance": st.column_config.NumberColumn(format="\u20b9%.2f"),
                    "Rate/Ltr": st.column_config.NumberColumn(format="\u20b9%.2f"),
                    "Payment Mode": st.column_config.TextColumn(width="medium"),
                },
            )

        # ── Download ─────────────────────────────────────────────────────────
        st.markdown("")

        # Build filename
        if selected_preset == "All Time" or date_from is None:
            period_label = "All_Time"
        elif selected_preset == "Custom":
            period_label = f"{date_from.strftime('%d%b%Y')}_to_{date_to.strftime('%d%b%Y')}"
        else:
            period_label = selected_preset.replace(" ", "_")

        file_name = f"{selected}_{period_label}_{today.strftime('%b_%Y')}.xlsx"

        party_excel = generate_party_excel(selected, date_from=date_from, date_to=date_to)
        st.download_button(
            f"Download {selected} — {selected_preset}",
            data=party_excel,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        # ── Delete last entry ────────────────────────────────────────────────
        st.divider()
        with st.expander("Danger Zone"):
            st.caption("This will soft-delete the last entry. The record is kept for audit.")
            if st.button("Delete Last Entry", type="secondary"):
                if models.soft_delete_last_entry(selected, deleted_by=get_current_user()):
                    st.success("Last entry deleted.")
                    st.rerun()
                else:
                    st.warning("No entries to delete.")
