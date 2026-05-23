"""Postgres connection pool and schema migrations for Neon free tier."""

import streamlit as st
import psycopg2
from psycopg2 import pool

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS parties (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fuel_prices (
    id              SERIAL PRIMARY KEY,
    fuel_type       TEXT NOT NULL CHECK (fuel_type IN ('HSD', 'MS', 'XP')),
    rate            NUMERIC(10,2) NOT NULL,
    effective_from  TIMESTAMPTZ NOT NULL DEFAULT now(),
    set_by          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fuel_prices_type_date
    ON fuel_prices (fuel_type, effective_from DESC);

CREATE TABLE IF NOT EXISTS bill_entries (
    id               SERIAL PRIMARY KEY,
    party_id         INTEGER NOT NULL REFERENCES parties(id),
    entry_date       DATE NOT NULL,
    vehicle_no       TEXT NOT NULL DEFAULT '',
    fuel_type        TEXT NOT NULL DEFAULT 'HSD',
    litres           NUMERIC(10,2) NOT NULL DEFAULT 0,
    rate_per_litre   NUMERIC(10,2),
    fuel_amount      NUMERIC(12,2) NOT NULL DEFAULT 0,
    cash_to_driver   NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_bill       NUMERIC(12,2) NOT NULL DEFAULT 0,
    payment_received NUMERIC(12,2) NOT NULL DEFAULT 0,
    balance          NUMERIC(12,2) NOT NULL DEFAULT 0,
    notes            TEXT NOT NULL DEFAULT '',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by       TEXT NOT NULL,
    is_deleted       BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at       TIMESTAMPTZ,
    deleted_by       TEXT
);
CREATE INDEX IF NOT EXISTS idx_bill_entries_party
    ON bill_entries (party_id, created_at);
"""


@st.cache_resource
def _get_pool():
    """Create a connection pool (cached per app worker)."""
    return pool.SimpleConnectionPool(
        minconn=1,
        maxconn=5,
        dsn=st.secrets["database"]["url"],
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )


def get_conn():
    """Get a connection from the pool, replacing it if stale (e.g. Neon suspend)."""
    p = _get_pool()
    conn = p.getconn()
    try:
        conn.isolation_level  # quick attribute check
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        # reset in case previous user left it in error state
        conn.rollback()
    except Exception:
        # Connection is dead — close and create a fresh one
        try:
            conn.close()
        except Exception:
            pass
        conn = psycopg2.connect(dsn=st.secrets["database"]["url"])
        # Put the new conn back into the pool's tracking
        p._pool.append(conn)  # noqa: SLF001
    return conn


def put_conn(conn):
    _get_pool().putconn(conn)


MIGRATIONS = [
    # Add payment_mode column (CASH, BANK EDFS, BANK ACCOUNT SBI, PAYTM, HDFC)
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'bill_entries' AND column_name = 'payment_mode'
        ) THEN
            ALTER TABLE bill_entries ADD COLUMN payment_mode TEXT NOT NULL DEFAULT '';
        END IF;
    END $$;
    """,
]


def _run_migrations():
    """Execute CREATE TABLE IF NOT EXISTS statements. Idempotent."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            for migration in MIGRATIONS:
                cur.execute(migration)
        conn.commit()
    finally:
        put_conn(conn)


def init_db():
    """Initialize DB: run migrations once per session. Shows error UI on failure."""
    if st.session_state.get("db_ready"):
        return True
    try:
        _run_migrations()
        st.session_state.db_ready = True
        return True
    except Exception as e:
        st.error(
            "**Database connection failed.** Check your `.streamlit/secrets.toml` "
            "and make sure the Neon database is set up.\n\n"
            f"Error: `{e}`"
        )
        st.stop()
        return False
