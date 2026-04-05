from __future__ import annotations

import threading
from datetime import UTC, datetime

from app.database import COLL_MERCHANTS, DatabaseClient


class InsufficientFundsError(Exception):
    pass


_wallets: dict[str, float] = {}
_last_updated: dict[str, str] = {}
_lock = threading.RLock()
_initialized = False


def initialize_wallet_store(db: DatabaseClient) -> None:
    global _initialized
    with _lock:
        _wallets.clear()
        _last_updated.clear()

        for doc in db.collection(COLL_MERCHANTS).stream():
            row = doc.to_dict() or {}
            merchant_id = row.get("merchant_id") or doc.id
            _wallets[merchant_id] = float(row.get("wallet_balance") or 0.0)
            _last_updated[merchant_id] = datetime.now(UTC).isoformat()

        _initialized = True


def is_loaded() -> bool:
    return _initialized


def get_balance(merchant_id: str) -> float:
    with _lock:
        return float(_wallets.get(merchant_id, 0.0))


def get_last_updated(merchant_id: str) -> str:
    with _lock:
        return _last_updated.get(merchant_id, datetime.now(UTC).isoformat())


def debit(merchant_id: str, amount: float) -> float:
    if amount <= 0:
        raise ValueError("amount must be greater than zero")

    with _lock:
        balance = float(_wallets.get(merchant_id, 0.0))
        if balance < amount:
            raise InsufficientFundsError("insufficient funds")
        new_balance = round(balance - amount, 2)
        _wallets[merchant_id] = new_balance
        _last_updated[merchant_id] = datetime.now(UTC).isoformat()
        return new_balance


def credit(merchant_id: str, amount: float) -> float:
    if amount <= 0:
        raise ValueError("amount must be greater than zero")

    with _lock:
        balance = float(_wallets.get(merchant_id, 0.0))
        new_balance = round(balance + amount, 2)
        _wallets[merchant_id] = new_balance
        _last_updated[merchant_id] = datetime.now(UTC).isoformat()
        return new_balance


def transfer(from_id: str, to_id: str, amount: float) -> tuple[float, float]:
    if amount <= 0:
        raise ValueError("amount must be greater than zero")

    with _lock:
        sender_balance = float(_wallets.get(from_id, 0.0))
        receiver_balance = float(_wallets.get(to_id, 0.0))

        if sender_balance < amount:
            raise InsufficientFundsError("insufficient funds")

        sender_new = round(sender_balance - amount, 2)
        receiver_new = round(receiver_balance + amount, 2)

        now_iso = datetime.now(UTC).isoformat()
        _wallets[from_id] = sender_new
        _wallets[to_id] = receiver_new
        _last_updated[from_id] = now_iso
        _last_updated[to_id] = now_iso

        return sender_new, receiver_new


def sync_to_db(db: DatabaseClient) -> None:
    with _lock:
        batch = db.batch()
        for merchant_id, balance in _wallets.items():
            ref = db.collection(COLL_MERCHANTS).document(merchant_id)
            batch.set(ref, {"wallet_balance": float(balance), "updated_at": datetime.now(UTC).isoformat()}, merge=True)
        batch.commit(retry=None, timeout=8.0)


def reset(seed_balances: dict[str, float]) -> None:
    with _lock:
        _wallets.clear()
        _wallets.update({key: float(value) for key, value in seed_balances.items()})
        now_iso = datetime.now(UTC).isoformat()
        _last_updated.clear()
        for key in _wallets:
            _last_updated[key] = now_iso


def snapshot_balances() -> dict[str, float]:
    with _lock:
        return dict(_wallets)
