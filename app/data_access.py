from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# --- Connection Management ---


@st.cache_resource
def get_engine() -> Engine:
    """Create and cache the database engine."""
    db_url = st.secrets["db"]["url"]
    # pool_pre_ping ensures the connection is alive before executing queries
    return create_engine(db_url, pool_pre_ping=True)


# --- Project Queries ---


def fetch_projects(engine: Engine) -> pd.DataFrame:
    """Fetch all projects (project_id, project_name)."""
    sql = text("SELECT project_id, project_name FROM projects ORDER BY project_name")

    with engine.connect() as conn:
        return pd.read_sql(sql, conn)


# --- Transaction Queries ---


def fetch_transactions(
    engine: Engine,
    project_id: int,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """Fetch transactions for a specific project with optional date filtering."""

    sql = text("""
        SELECT transaction_id, project_id, transaction_date, unit, build_stage, category, description,
            credit, debit, is_funding
        FROM transactions
        WHERE project_id = :pid
        AND transaction_date >= :start
        AND transaction_date <= :end
        ORDER BY transaction_date DESC, transaction_id DESC
    """)

    params = {
        "pid": project_id,
        "start": start_date or "1900-01-01",
        "end": end_date or "2999-12-31",
}

    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params=params)


# --- Transaction Writes ---


def insert_transaction(
    engine: Engine,
    *,
    project_id: int,
    unit: str,
    transaction_date,
    build_stage: str,
    category: str,
    description: str,
    credit: float,
    debit: float,
    is_funding: bool,
) -> bool:
    """Insert a single transaction. Returns True if successful, False otherwise."""
    sql = text("""
        INSERT INTO transactions
            (project_id, unit, transaction_date, build_stage, category, description,
             credit, debit, is_funding)
        VALUES
            (:pid, :unit, :date, :stage, :cat, :desc, :cred, :deb, :is_funding)
    """)

    try:
        # engine.begin() acts as a context manager: auto-commits on success, rolls back on error
        with engine.begin() as conn:
            conn.execute(
                sql,
                {
                    "pid": project_id,
                    "unit": unit,
                    "date": transaction_date,
                    "stage": build_stage,
                    "cat": category,
                    "desc": description,
                    "cred": credit,
                    "deb": debit,
                    "is_funding": is_funding,
                },
            )
        return True
    except Exception as exc:
        raise


def delete_transaction(engine, transaction_id: int) -> bool:
    """Deletes a specific transaction by its ID."""
    try:
        with engine.begin() as conn:
            # Assuming your primary key is named 'id' or 'transaction_id'
            # Adjust 'transaction_id' to match your actual database column name
            query = text("DELETE FROM transactions WHERE transaction_id = :tid")
            conn.execute(query, {"tid": transaction_id})
        return True
    except Exception as e:
        print(f"Error deleting transaction: {e}")
        return False