from datetime import UTC, datetime
from uuid import uuid4

from backend.db import get_db


def ensure_wallet(entity_id: str, connection=None) -> None:
    conn = connection or get_db()
    existing = conn.execute(
        "SELECT entity_id FROM wallets WHERE entity_id = ?",
        (entity_id,),
    ).fetchone()
    if existing is None:
        conn.execute(
            "INSERT INTO wallets (entity_id, balance) VALUES (?, ?)",
            (entity_id, 0.0),
        )


def get_balance(entity_id: str, connection=None) -> float:
    conn = connection or get_db()
    ensure_wallet(entity_id, conn)
    row = conn.execute(
        "SELECT balance FROM wallets WHERE entity_id = ?",
        (entity_id,),
    ).fetchone()
    return float(row["balance"])


def transfer_funds(
    sender_id: str,
    receiver_id: str,
    amount: float,
    note: str = "",
    connection=None,
) -> str:
    conn = connection or get_db()
    if amount <= 0:
        raise ValueError("amount must be greater than zero")

    ensure_wallet(sender_id, conn)
    ensure_wallet(receiver_id, conn)

    sender_balance = get_balance(sender_id, conn)
    if sender_balance < amount:
        raise ValueError("insufficient funds")

    receiver_balance = get_balance(receiver_id, conn)

    conn.execute(
        "UPDATE wallets SET balance = ? WHERE entity_id = ?",
        (round(sender_balance - amount, 2), sender_id),
    )
    conn.execute(
        "UPDATE wallets SET balance = ? WHERE entity_id = ?",
        (round(receiver_balance + amount, 2), receiver_id),
    )

    tx_id = f"TX-{uuid4().hex[:12]}"
    conn.execute(
        """
        INSERT INTO transactions (tx_id, sender_id, receiver_id, amount, timestamp, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (tx_id, sender_id, receiver_id, round(amount, 2), datetime.now(UTC).isoformat(), note),
    )
    return tx_id
