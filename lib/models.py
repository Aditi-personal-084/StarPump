"""All database read/write operations. Replaces excel_manager.py."""

from datetime import date
from decimal import Decimal
from typing import Optional

import pandas as pd

from lib import db
from lib.validators import sanitize_party_name


# ── Parties ──────────────────────────────────────────────────────────────────

def add_party(name: str) -> int:
    """Insert a new party. Returns party ID. Raises on duplicate."""
    safe = sanitize_party_name(name)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO parties (name) VALUES (%s) RETURNING id", (safe,)
            )
            party_id = cur.fetchone()[0]
        conn.commit()
        return party_id
    except Exception:
        conn.rollback()
        raise
    finally:
        db.put_conn(conn)


def get_all_parties() -> list[str]:
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM parties ORDER BY name")
            return [r[0] for r in cur.fetchall()]
    finally:
        db.put_conn(conn)


def _get_or_create_party(cur, name: str) -> int:
    """Get party ID, creating if needed. Must be called inside a transaction."""
    safe = sanitize_party_name(name)
    cur.execute("SELECT id FROM parties WHERE name = %s", (safe,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("INSERT INTO parties (name) VALUES (%s) RETURNING id", (safe,))
    return cur.fetchone()[0]


# ── Fuel Prices ──────────────────────────────────────────────────────────────

def set_fuel_price(fuel_type: str, rate: float, set_by: str):
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO fuel_prices (fuel_type, rate, set_by) VALUES (%s, %s, %s)",
                (fuel_type, rate, set_by),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        db.put_conn(conn)


def get_current_prices() -> dict[str, float]:
    """Returns {'HSD': 89.50, 'MS': 95.00, 'XP': 100.50}."""
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (fuel_type) fuel_type, rate
                FROM fuel_prices
                ORDER BY fuel_type, effective_from DESC
            """)
            return {r[0]: float(r[1]) for r in cur.fetchall()}
    finally:
        db.put_conn(conn)


def get_price_history() -> list[dict]:
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT fuel_type, rate, effective_from, set_by
                FROM fuel_prices ORDER BY effective_from DESC LIMIT 50
            """)
            return [
                {
                    "fuel_type": r[0],
                    "rate": float(r[1]),
                    "effective_from": r[2],
                    "set_by": r[3],
                }
                for r in cur.fetchall()
            ]
    finally:
        db.put_conn(conn)


# ── Bill Entries ─────────────────────────────────────────────────────────────

def get_previous_balance(party_name: str) -> float:
    safe = sanitize_party_name(party_name)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM parties WHERE name = %s", (safe,))
            row = cur.fetchone()
            if not row:
                return 0.0
            cur.execute("""
                SELECT balance FROM bill_entries
                WHERE party_id = %s AND is_deleted = FALSE
                ORDER BY created_at DESC LIMIT 1
            """, (row[0],))
            bal = cur.fetchone()
            return float(bal[0]) if bal else 0.0
    finally:
        db.put_conn(conn)


def add_opening_balance(party_name: str, amount: float, created_by: str):
    """Add a carry-forward / opening balance entry for a party."""
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            party_id = _get_or_create_party(cur, party_name)

            # Only allow if party has no entries
            cur.execute("""
                SELECT COUNT(*) FROM bill_entries
                WHERE party_id = %s AND is_deleted = FALSE
            """, (party_id,))
            count = cur.fetchone()[0]
            if count > 0:
                raise ValueError("Party already has entries. Cannot set opening balance.")

            cur.execute("""
                INSERT INTO bill_entries
                    (party_id, entry_date, vehicle_no, fuel_type, litres,
                     rate_per_litre, fuel_amount, cash_to_driver, total_bill,
                     payment_received, balance, notes, created_by)
                VALUES (%s, %s, '', 'HSD', 0, NULL, 0, 0, 0, 0, %s,
                        'Opening / Carry Forward Balance', %s)
            """, (party_id, date.today(), amount, created_by))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        db.put_conn(conn)


def add_bill_entry(
    party_name: str,
    entry_date: date,
    vehicle_no: str,
    fuel_type: str,
    litres: float,
    rate_per_litre: float | None,
    fuel_amount: float,
    cash_to_driver: float,
    payment_received: float,
    notes: str,
    created_by: str,
) -> dict:
    """Add a bill entry inside a single transaction. Returns result dict."""
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            party_id = _get_or_create_party(cur, party_name)

            # Get previous balance
            cur.execute("""
                SELECT balance FROM bill_entries
                WHERE party_id = %s AND is_deleted = FALSE
                ORDER BY created_at DESC LIMIT 1
            """, (party_id,))
            row = cur.fetchone()
            prev_balance = float(row[0]) if row else 0.0

            total_bill = fuel_amount + cash_to_driver
            new_balance = prev_balance + total_bill - payment_received

            # Get serial number
            cur.execute("""
                SELECT COUNT(*) FROM bill_entries
                WHERE party_id = %s AND is_deleted = FALSE
            """, (party_id,))
            serial_no = cur.fetchone()[0] + 1

            cur.execute("""
                INSERT INTO bill_entries
                    (party_id, entry_date, vehicle_no, fuel_type, litres,
                     rate_per_litre, fuel_amount, cash_to_driver, total_bill,
                     payment_received, balance, notes, created_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                party_id, entry_date, vehicle_no, fuel_type, litres,
                rate_per_litre, fuel_amount, cash_to_driver, total_bill,
                payment_received, new_balance, notes, created_by,
            ))
            entry_id = cur.fetchone()[0]

        conn.commit()
        return {
            "id": entry_id,
            "serial_no": serial_no,
            "party_name": sanitize_party_name(party_name),
            "total_bill": total_bill,
            "previous_balance": prev_balance,
            "new_balance": new_balance,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        db.put_conn(conn)


def get_party_ledger(
    party_name: str,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> pd.DataFrame:
    safe = sanitize_party_name(party_name)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM parties WHERE name = %s", (safe,))
            row = cur.fetchone()
            if not row:
                return pd.DataFrame()

            query = """
                SELECT
                    ROW_NUMBER() OVER (ORDER BY created_at) AS "S.No",
                    entry_date AS "Date",
                    vehicle_no AS "Vehicle No",
                    fuel_type AS "Fuel Type",
                    litres AS "Litres",
                    rate_per_litre AS "Rate/Ltr",
                    fuel_amount AS "Fuel Amount",
                    cash_to_driver AS "Cash to Driver",
                    total_bill AS "Total Bill",
                    payment_received AS "Payment Received",
                    balance AS "Balance",
                    notes AS "Notes"
                FROM bill_entries
                WHERE party_id = %s AND is_deleted = FALSE
            """
            params: list = [row[0]]

            if date_from:
                query += " AND entry_date >= %s"
                params.append(date_from)
            if date_to:
                query += " AND entry_date <= %s"
                params.append(date_to)

            query += " ORDER BY created_at"

            cur.execute(query, params)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            df = pd.DataFrame(rows, columns=cols)
            # Convert Decimal columns to float for display
            for col in df.select_dtypes(include=["object"]).columns:
                try:
                    df[col] = df[col].apply(
                        lambda x: float(x) if isinstance(x, Decimal) else x
                    )
                except (ValueError, TypeError):
                    pass
            return df
    finally:
        db.put_conn(conn)


def get_all_balances() -> dict[str, float]:
    """Single query — no N+1."""
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.name, COALESCE(b.balance, 0)
                FROM parties p
                LEFT JOIN LATERAL (
                    SELECT balance FROM bill_entries
                    WHERE party_id = p.id AND is_deleted = FALSE
                    ORDER BY created_at DESC LIMIT 1
                ) b ON TRUE
                ORDER BY p.name
            """)
            return {r[0]: float(r[1]) for r in cur.fetchall()}
    finally:
        db.put_conn(conn)


def soft_delete_last_entry(party_name: str, deleted_by: str) -> bool:
    safe = sanitize_party_name(party_name)
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM parties WHERE name = %s", (safe,))
            row = cur.fetchone()
            if not row:
                return False
            cur.execute("""
                UPDATE bill_entries
                SET is_deleted = TRUE, deleted_at = now(), deleted_by = %s
                WHERE id = (
                    SELECT id FROM bill_entries
                    WHERE party_id = %s AND is_deleted = FALSE
                    ORDER BY created_at DESC LIMIT 1
                )
            """, (deleted_by, row[0]))
            affected = cur.rowcount
        conn.commit()
        return affected > 0
    except Exception:
        conn.rollback()
        raise
    finally:
        db.put_conn(conn)
