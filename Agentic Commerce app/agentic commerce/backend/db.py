"""
ArthSetu — Database Layer
SQLite initialization, schema creation, seed data, and connection helpers.
Implements the full ArthSetu schema including PayBot extensions.
"""

import sqlite3
import json
import os
import pathlib

DATABASE_PATH = os.getenv("DATABASE_PATH", "arthsetu.db")
_BASE_DIR = pathlib.Path(__file__).resolve().parent


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Get a SQLite connection with row_factory set to sqlite3.Row."""
    path = db_path or DATABASE_PATH
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def dict_from_row(row: sqlite3.Row | None) -> dict | None:
    """Convert a sqlite3.Row to a plain dict."""
    if row is None:
        return None
    return dict(row)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
-- Merchants table
CREATE TABLE IF NOT EXISTS merchants (
    merchant_id     TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    category        TEXT NOT NULL,
    location        TEXT,
    is_agent_addressable INTEGER NOT NULL DEFAULT 1,
    paytm_pos_id    TEXT
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    product_id      TEXT PRIMARY KEY,
    merchant_id     TEXT NOT NULL,
    name            TEXT NOT NULL,
    price           REAL NOT NULL,
    unit            TEXT,
    hsn_code        TEXT,
    gst_rate        REAL NOT NULL DEFAULT 0.0,
    stock_qty       INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id)
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id         TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    phone           TEXT,
    wallet_balance  REAL NOT NULL DEFAULT 0
);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    tx_id           TEXT PRIMARY KEY,
    merchant_id     TEXT,
    user_id         TEXT,
    amount          REAL NOT NULL,
    timestamp       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    gst_category    TEXT,
    hsn_code        TEXT,
    status          TEXT NOT NULL DEFAULT 'completed',
    order_id        TEXT,
    token_id        TEXT,
    FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Invoices table
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id      TEXT PRIMARY KEY,
    seller_id       TEXT,
    buyer_id        TEXT,
    amount          REAL NOT NULL,
    due_date        DATE,
    status          TEXT NOT NULL DEFAULT 'pending',
    advance_amount  REAL DEFAULT 0,
    repaid          INTEGER DEFAULT 0
);

-- Scoped Delegation Tokens (AP2 Intent Mandate)
CREATE TABLE IF NOT EXISTS tokens (
    token_id            TEXT PRIMARY KEY,
    user_id             TEXT NOT NULL,
    agent_id            TEXT NOT NULL,
    prompt_playback     TEXT NOT NULL,
    budget_cap          REAL NOT NULL,
    budget_spent        REAL NOT NULL DEFAULT 0,
    categories          TEXT NOT NULL,
    merchant_whitelist  TEXT NOT NULL,
    items               TEXT NOT NULL,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_until         DATETIME NOT NULL,
    tx_ids_used         TEXT NOT NULL DEFAULT '[]',
    status              TEXT NOT NULL DEFAULT 'active',
    human_present       INTEGER NOT NULL DEFAULT 1,
    hitl_threshold      REAL NOT NULL DEFAULT 200,
    pending_hitl_token  TEXT,
    signature           TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Immutable Audit Log
CREATE TABLE IF NOT EXISTS audit_log (
    log_id          TEXT PRIMARY KEY,
    timestamp       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    token_id        TEXT,
    agent_id        TEXT,
    action_type     TEXT NOT NULL,
    actor           TEXT NOT NULL,
    entity_id       TEXT,
    amount          REAL,
    category        TEXT,
    merchant_id     TEXT,
    outcome         TEXT NOT NULL,
    payload_hash    TEXT NOT NULL,
    ip_address      TEXT,
    session_id      TEXT
);

-- Immutability triggers on audit_log
CREATE TRIGGER IF NOT EXISTS audit_log_immutable
BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(FAIL, 'audit_log is immutable — updates are not allowed');
END;

CREATE TRIGGER IF NOT EXISTS audit_log_no_delete
BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(FAIL, 'audit_log is immutable — deletes are not allowed');
END;

-- Pending HITL Orders
CREATE TABLE IF NOT EXISTS hitl_orders (
    hitl_token      TEXT PRIMARY KEY,
    token_id        TEXT NOT NULL,
    order_id        TEXT NOT NULL,
    merchant_id     TEXT NOT NULL,
    amount          REAL NOT NULL,
    line_items      TEXT NOT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at      DATETIME NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    FOREIGN KEY (token_id) REFERENCES tokens(token_id)
);

-- TrustScore History (stub for Team C integration)
CREATE TABLE IF NOT EXISTS trustscore_history (
    record_id       TEXT PRIMARY KEY,
    merchant_id     TEXT,
    score           REAL,
    components      TEXT,
    computed_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- V2: Agent Sessions
CREATE TABLE IF NOT EXISTS agent_sessions (
    session_id      TEXT PRIMARY KEY,
    token_id        TEXT NOT NULL,
    user_id         TEXT NOT NULL,
    task_type       TEXT NOT NULL,
    hitl_mode       TEXT NOT NULL,
    phase           TEXT NOT NULL DEFAULT 'running',
    steps           TEXT NOT NULL DEFAULT '[]',
    user_input      TEXT NOT NULL,
    intent          TEXT NOT NULL,
    order_data      TEXT,
    selection_data  TEXT,
    result          TEXT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (token_id) REFERENCES tokens(token_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- V2: Pending Selections (for selection_hitl mode)
CREATE TABLE IF NOT EXISTS pending_selections (
    selection_id     TEXT PRIMARY KEY,
    session_id       TEXT NOT NULL,
    token_id         TEXT NOT NULL,
    selection_type   TEXT NOT NULL,
    prompt           TEXT NOT NULL,
    options          TEXT NOT NULL,
    selected_option  TEXT,
    status           TEXT NOT NULL DEFAULT 'pending',
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES agent_sessions(session_id)
);
"""


def init_db(db_path: str | None = None) -> None:
    """Create all tables and seed demo data."""
    conn = get_connection(db_path)
    conn.executescript(SCHEMA_SQL)
    _seed_data(conn)
    conn.close()


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

def _seed_data(conn: sqlite3.Connection) -> None:
    """Seed merchants, products, and demo users if tables are empty."""
    cursor = conn.cursor()

    # Check if already seeded
    row = cursor.execute("SELECT COUNT(*) as cnt FROM merchants").fetchone()
    if row["cnt"] > 0:
        return

    # Load merchant catalog
    merchants_path = _BASE_DIR / "data" / "merchants.json"
    with open(merchants_path) as f:
        merchants = json.load(f)

    for m in merchants:
        cursor.execute(
            "INSERT INTO merchants (merchant_id, name, category, location, is_agent_addressable, paytm_pos_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (m["merchant_id"], m["name"], m["category"], m["location"],
             1 if m["is_agent_addressable"] else 0, m.get("paytm_pos_id")),
        )
        for p in m["products"]:
            cursor.execute(
                "INSERT INTO products (product_id, merchant_id, name, price, unit, hsn_code, gst_rate, stock_qty) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (p["product_id"], m["merchant_id"], p["name"], p["price"],
                 p.get("unit"), p.get("hsn_code"), p.get("gst_rate", 0), p.get("stock_qty", 0)),
            )

    # Seed virtual merchants for V2 agent domains
    virtual_merchants = [
        ("jio_recharge", "Jio Recharge", "telecom"),
        ("airtel_recharge", "Airtel Recharge", "telecom"),
        ("movie_booking", "Movie Booking", "entertainment"),
        ("train_booking", "Train Booking", "travel"),
        ("cheapest_split", "Cheapest Split Order", "grocery"),
    ]
    for m_id, m_name, m_cat in virtual_merchants:
        cursor.execute(
            "INSERT INTO merchants (merchant_id, name, category, location, is_agent_addressable) "
            "VALUES (?, ?, ?, ?, ?)",
            (m_id, m_name, m_cat, "Online", 1),
        )

    # Seed demo users
    demo_users = [
        ("priya_001", "Priya Sharma", "+919876543210", 2000.0),
        ("rahul_002", "Rahul Verma", "+919876543211", 5000.0),
        ("anita_003", "Anita Gupta", "+919876543212", 3000.0),
    ]
    for user_id, name, phone, balance in demo_users:
        cursor.execute(
            "INSERT INTO users (user_id, name, phone, wallet_balance) VALUES (?, ?, ?, ?)",
            (user_id, name, phone, balance),
        )

    conn.commit()


# ---------------------------------------------------------------------------
# Helper queries
# ---------------------------------------------------------------------------

def get_user(conn: sqlite3.Connection, user_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return dict_from_row(row)


def get_merchant(conn: sqlite3.Connection, merchant_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM merchants WHERE merchant_id = ?", (merchant_id,)).fetchone()
    return dict_from_row(row)


def get_all_merchants(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM merchants WHERE is_agent_addressable = 1"
    ).fetchall()
    return [dict(r) for r in rows]


def get_merchant_products(conn: sqlite3.Connection, merchant_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM products WHERE merchant_id = ?", (merchant_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_merchant_ids(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT merchant_id FROM merchants WHERE is_agent_addressable = 1"
    ).fetchall()
    return [r["merchant_id"] for r in rows]


def save_token(conn: sqlite3.Connection, token: dict) -> None:
    conn.execute(
        """INSERT INTO tokens
        (token_id, user_id, agent_id, prompt_playback, budget_cap, budget_spent,
         categories, merchant_whitelist, items, valid_until, tx_ids_used,
         status, human_present, hitl_threshold, pending_hitl_token, signature)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            token["token_id"], token["user_id"], token["agent_id"],
            token["prompt_playback"], token["budget_cap"], token["budget_spent"],
            json.dumps(token["categories"]), json.dumps(token["merchant_whitelist"]),
            json.dumps(token["items"]), token["valid_until"],
            json.dumps(token.get("tx_ids_used", [])), token["status"],
            1 if token.get("human_present", True) else 0,
            token.get("hitl_threshold", 200), token.get("pending_hitl_token"),
            token["signature"],
        ),
    )
    conn.commit()


def get_token_fresh(conn: sqlite3.Connection, token_id: str) -> dict | None:
    """Atomic fresh read of token — BEGIN EXCLUSIVE to prevent TOCTOU."""
    conn.execute("BEGIN EXCLUSIVE")
    row = conn.execute("SELECT * FROM tokens WHERE token_id = ?", (token_id,)).fetchone()
    conn.commit()
    if row is None:
        return None
    t = dict(row)
    # Parse JSON fields
    t["categories"] = json.loads(t["categories"])
    t["merchant_whitelist"] = json.loads(t["merchant_whitelist"])
    t["items"] = json.loads(t["items"])
    t["tx_ids_used"] = json.loads(t["tx_ids_used"])
    return t


def update_token_budget(conn: sqlite3.Connection, token_id: str, amount: float, order_id: str) -> None:
    """Atomically update budget_spent and append order_id to tx_ids_used."""
    token = get_token_fresh(conn, token_id)
    if not token:
        return
    new_spent = token["budget_spent"] + amount
    used = token["tx_ids_used"]
    used.append(order_id)
    conn.execute(
        "UPDATE tokens SET budget_spent = ?, tx_ids_used = ? WHERE token_id = ?",
        (new_spent, json.dumps(used), token_id),
    )
    # Auto-exhaust if budget depleted
    if new_spent >= token["budget_cap"]:
        conn.execute("UPDATE tokens SET status = 'exhausted' WHERE token_id = ?", (token_id,))
    conn.commit()


def update_token_status(conn: sqlite3.Connection, token_id: str, status: str) -> None:
    conn.execute("UPDATE tokens SET status = ? WHERE token_id = ?", (status, token_id))
    conn.commit()


def set_token_hitl(conn: sqlite3.Connection, token_id: str, hitl_token: str | None) -> None:
    if hitl_token:
        conn.execute(
            "UPDATE tokens SET pending_hitl_token = ?, status = 'pending_hitl' WHERE token_id = ?",
            (hitl_token, token_id),
        )
    else:
        conn.execute(
            "UPDATE tokens SET pending_hitl_token = NULL, status = 'active' WHERE token_id = ?",
            (token_id,),
        )
    conn.commit()


if __name__ == "__main__":
    print("Initialising ArthSetu database...")
    init_db()
    print(f"Database created at {DATABASE_PATH}")
    conn = get_connection()
    merchants = get_all_merchants(conn)
    print(f"Seeded {len(merchants)} merchants")
    for m in merchants:
        products = get_merchant_products(conn, m["merchant_id"])
        print(f"  {m['name']}: {len(products)} products")
    users = conn.execute("SELECT * FROM users").fetchall()
    print(f"Seeded {len(users)} demo users")
    for u in users:
        print(f"  {u['name']}: Rs.{u['wallet_balance']}")
    conn.close()


# ---------------------------------------------------------------------------
# V2: Agent session helpers
# ---------------------------------------------------------------------------

def create_session(conn: sqlite3.Connection, session: dict) -> None:
    conn.execute(
        """INSERT INTO agent_sessions
        (session_id, token_id, user_id, task_type, hitl_mode, phase,
         steps, user_input, intent)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            session["session_id"], session["token_id"], session["user_id"],
            session["task_type"], session["hitl_mode"], session.get("phase", "running"),
            json.dumps(session.get("steps", [])), session["user_input"],
            json.dumps(session["intent"]),
        ),
    )
    conn.commit()


def get_session(conn: sqlite3.Connection, session_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM agent_sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    if row is None:
        return None
    s = dict(row)
    s["steps"] = json.loads(s["steps"])
    s["intent"] = json.loads(s["intent"])
    if s.get("order_data"):
        s["order_data"] = json.loads(s["order_data"])
    if s.get("selection_data"):
        s["selection_data"] = json.loads(s["selection_data"])
    if s.get("result"):
        s["result"] = json.loads(s["result"])
    return s


def update_session(conn: sqlite3.Connection, session_id: str, **kwargs) -> None:
    updates = []
    values = []
    for key, value in kwargs.items():
        if key in ("steps", "intent", "order_data", "selection_data", "result"):
            value = json.dumps(value)
        updates.append(f"{key} = ?")
        values.append(value)
    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(session_id)
    conn.execute(
        f"UPDATE agent_sessions SET {', '.join(updates)} WHERE session_id = ?",
        values,
    )
    conn.commit()


def create_pending_selection(conn: sqlite3.Connection, selection: dict) -> None:
    conn.execute(
        """INSERT INTO pending_selections
        (selection_id, session_id, token_id, selection_type, prompt, options)
        VALUES (?,?,?,?,?,?)""",
        (
            selection["selection_id"], selection["session_id"],
            selection["token_id"], selection["selection_type"],
            selection["prompt"], json.dumps(selection["options"]),
        ),
    )
    conn.commit()


def get_pending_selection(conn: sqlite3.Connection, session_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM pending_selections WHERE session_id = ? AND status = 'pending'",
        (session_id,),
    ).fetchone()
    if row is None:
        return None
    s = dict(row)
    s["options"] = json.loads(s["options"])
    return s


def resolve_selection(conn: sqlite3.Connection, selection_id: str, option_id: str) -> None:
    conn.execute(
        "UPDATE pending_selections SET selected_option = ?, status = 'resolved' WHERE selection_id = ?",
        (option_id, selection_id),
    )
    conn.commit()

