import json
import sqlite3
from contextvars import ContextVar, Token
from datetime import UTC, date, datetime, timedelta
from pathlib import Path


_database_path: str | None = None
_request_db: ContextVar[sqlite3.Connection | None] = ContextVar("request_db", default=None)


DROP_SCHEMA_SQL = """
DROP TABLE IF EXISTS financing_ledger;
DROP TABLE IF EXISTS credit_offers;
DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS wallets;
DROP TABLE IF EXISTS trustscore_history;
DROP TABLE IF EXISTS trustscores;
DROP TABLE IF EXISTS merchants;
DROP TABLE IF EXISTS whatsapp_log;
DROP TABLE IF EXISTS audit_log;
"""


CREATE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS merchants (
    merchant_id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trustscores (
    merchant_id TEXT PRIMARY KEY,
    score INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (merchant_id) REFERENCES merchants (merchant_id)
);

CREATE TABLE IF NOT EXISTS trustscore_history (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    merchant_id TEXT NOT NULL,
    score INTEGER NOT NULL,
    components TEXT NOT NULL,
    computed_at TEXT NOT NULL,
    FOREIGN KEY (merchant_id) REFERENCES merchants (merchant_id)
);

CREATE TABLE IF NOT EXISTS wallets (
    entity_id TEXT PRIMARY KEY,
    balance REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    tx_id TEXT PRIMARY KEY,
    sender_id TEXT NOT NULL,
    receiver_id TEXT NOT NULL,
    amount REAL NOT NULL,
    timestamp TEXT NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id TEXT PRIMARY KEY,
    seller_id TEXT NOT NULL,
    buyer_id TEXT NOT NULL,
    amount REAL NOT NULL,
    due_date TEXT NOT NULL,
    status TEXT NOT NULL,
    advance_amount REAL DEFAULT 0,
    offer_id TEXT,
    financed_at TEXT,
    repaid INTEGER DEFAULT 0,
    repaid_at TEXT,
    FOREIGN KEY (seller_id) REFERENCES merchants (merchant_id)
);

CREATE TABLE IF NOT EXISTS credit_offers (
    offer_id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    merchant_id TEXT NOT NULL,
    trustscore_snapshot INTEGER NOT NULL,
    advance_pct REAL NOT NULL,
    max_cap_applied REAL NOT NULL,
    advance_amount REAL NOT NULL,
    fee_rate REAL NOT NULL,
    status TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    accepted_at TEXT,
    FOREIGN KEY (invoice_id) REFERENCES invoices (invoice_id),
    FOREIGN KEY (merchant_id) REFERENCES merchants (merchant_id)
);

CREATE TABLE IF NOT EXISTS financing_ledger (
    ledger_id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    offer_id TEXT,
    event_type TEXT NOT NULL,
    amount REAL NOT NULL,
    tx_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices (invoice_id)
);

CREATE TABLE IF NOT EXISTS audit_log (
    log_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_id TEXT,
    amount REAL,
    token_id TEXT,
    outcome TEXT NOT NULL,
    details TEXT
);

CREATE TABLE IF NOT EXISTS whatsapp_log (
    sid TEXT PRIMARY KEY,
    phone TEXT NOT NULL,
    message TEXT NOT NULL,
    sent_at TEXT NOT NULL
);
"""


def connect_db(db_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def configure_database(db_path: str) -> None:
    global _database_path
    _database_path = db_path


def set_request_db(connection: sqlite3.Connection) -> Token:
    return _request_db.set(connection)


def reset_request_db(token: Token) -> None:
    _request_db.reset(token)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def get_db() -> sqlite3.Connection:
    connection = _request_db.get()
    if connection is None:
        if not _database_path:
            raise RuntimeError("Database is not configured")
        connection = connect_db(_database_path)
        _request_db.set(connection)
    return connection


def init_db(reset: bool = False, db_path: str | None = None) -> None:
    target_path = db_path or _database_path
    if not target_path:
        raise RuntimeError("Database path is required")

    Path(target_path).parent.mkdir(parents=True, exist_ok=True)
    connection = connect_db(target_path)
    try:
        if reset:
            connection.executescript(DROP_SCHEMA_SQL)
        connection.executescript(CREATE_SCHEMA_SQL)
        seed_demo_data(connection)
        connection.commit()
    finally:
        connection.close()


def seed_demo_data(connection: sqlite3.Connection) -> None:
    # Clear existing rows for deterministic local runs.
    connection.executescript(
        """
        DELETE FROM financing_ledger;
        DELETE FROM credit_offers;
        DELETE FROM invoices;
        DELETE FROM transactions;
        DELETE FROM wallets;
        DELETE FROM trustscore_history;
        DELETE FROM trustscores;
        DELETE FROM merchants;
        DELETE FROM whatsapp_log;
        DELETE FROM audit_log;
        """
    )

    merchants = [
        ("seller_a", "Ramesh General Store"),
        ("seller_b", "Sharma Electronics"),
        ("seller_c", "Gupta Clothing"),
        ("buyer_a", "Acme Retail LLP"),
        ("buyer_b", "Metro Supplies"),
    ]
    connection.executemany(
        "INSERT INTO merchants (merchant_id, name) VALUES (?, ?)",
        merchants,
    )

    now = utc_now_iso()
    scores = [
        ("seller_a", 82, now),
        ("seller_b", 58, now),
        ("seller_c", 35, now),
    ]
    connection.executemany(
        "INSERT INTO trustscores (merchant_id, score, updated_at) VALUES (?, ?, ?)",
        scores,
    )

    history_rows = []
    for merchant_id, score, computed_at in scores:
        components = {
            "payment_rate": round(score * 0.30, 2),
            "consistency": round(score * 0.20, 2),
            "volume_trend": round(score * 0.20, 2),
            "gst_compliance": round(score * 0.20, 2),
            "return_rate": round(score * 0.10, 2),
        }
        history_rows.append((merchant_id, score, json.dumps(components), computed_at))

    connection.executemany(
        """
        INSERT INTO trustscore_history (merchant_id, score, components, computed_at)
        VALUES (?, ?, ?, ?)
        """,
        history_rows,
    )

    wallets = [
        ("financing_pool", 1_000_000.0),
        ("seller_a", 10_000.0),
        ("seller_b", 7_500.0),
        ("seller_c", 4_000.0),
        ("buyer_a", 50_000.0),
        ("buyer_b", 90_000.0),
    ]
    connection.executemany(
        "INSERT INTO wallets (entity_id, balance) VALUES (?, ?)",
        wallets,
    )

    today = date.today()
    invoices = [
        (
            "INV-ELIGIBLE-1",
            "seller_a",
            "buyer_a",
            100_000.0,
            (today - timedelta(days=35)).isoformat(),
            "PENDING",
            0.0,
            None,
            None,
            0,
            None,
        ),
        (
            "INV-ELIGIBLE-2",
            "seller_b",
            "buyer_b",
            120_000.0,
            (today - timedelta(days=22)).isoformat(),
            "PENDING",
            0.0,
            None,
            None,
            0,
            None,
        ),
        (
            "INV-INELIGIBLE-LOWSCORE",
            "seller_c",
            "buyer_a",
            65_000.0,
            (today - timedelta(days=26)).isoformat(),
            "PENDING",
            0.0,
            None,
            None,
            0,
            None,
        ),
        (
            "INV-PAID-1",
            "seller_a",
            "buyer_b",
            19_500.0,
            (today - timedelta(days=10)).isoformat(),
            "PAID",
            0.0,
            None,
            None,
            1,
            (today - timedelta(days=5)).isoformat(),
        ),
        (
            "INV-PLAIN-PENDING",
            "seller_b",
            "buyer_a",
            40_000.0,
            (today - timedelta(days=8)).isoformat(),
            "PENDING",
            0.0,
            None,
            None,
            0,
            None,
        ),
    ]
    connection.executemany(
        """
        INSERT INTO invoices (
            invoice_id, seller_id, buyer_id, amount, due_date, status,
            advance_amount, offer_id, financed_at, repaid, repaid_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        invoices,
    )
