import json
from datetime import UTC, datetime
from uuid import uuid4

from db import get_db


def append_audit(
    action: str,
    entity_id: str | None = None,
    amount: float | None = None,
    token_id: str | None = None,
    outcome: str = "SUCCESS",
    details: dict | None = None,
    connection=None,
) -> str:
    conn = connection or get_db()
    log_id = f"LOG-{uuid4().hex[:12]}"
    conn.execute(
        """
        INSERT INTO audit_log (log_id, timestamp, action, entity_id, amount, token_id, outcome, details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            log_id,
            datetime.now(UTC).isoformat(),
            action,
            entity_id,
            amount,
            token_id,
            outcome,
            json.dumps(details or {}),
        ),
    )
    return log_id
