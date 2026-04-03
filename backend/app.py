from pathlib import Path

from fastapi import FastAPI, HTTPException

from backend.audit import append_audit
from backend.db import (
    configure_database,
    connect_db,
    get_db,
    init_db,
    reset_request_db,
    set_request_db,
)
from backend.modules.cashflow import cashflow_router
from backend.modules.invoice import invoice_router, process_repayment
from backend.modules.trustscore import trustscore_router
from backend.wallet import get_balance, transfer_funds
from backend.whatsapp import send_whatsapp


def create_app(test_config: dict | None = None) -> FastAPI:
    app = FastAPI(title="ArthSetu Backend")
    default_db = Path(__file__).resolve().parent / "arthsetu.db"

    config = {
        "DATABASE_PATH": str(default_db),
        "TESTING": False,
    }
    if test_config:
        config.update(test_config)

    app.state.database_path = config["DATABASE_PATH"]
    app.state.testing = config["TESTING"]

    configure_database(app.state.database_path)
    app.include_router(cashflow_router)
    app.include_router(trustscore_router)
    app.include_router(invoice_router)

    @app.middleware("http")
    async def db_middleware(request, call_next):
        connection = connect_db(app.state.database_path)
        token = set_request_db(connection)
        try:
            response = await call_next(request)
            connection.commit()
            return response
        except Exception:
            connection.rollback()
            raise
        finally:
            reset_request_db(token)
            connection.close()

    @app.on_event("startup")
    def startup_event() -> None:
        init_db(reset=False, db_path=app.state.database_path)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/reset-demo")
    def reset_demo():
        init_db(reset=True, db_path=app.state.database_path)
        return {"status": "reset"}

    @app.get("/api/check-balance")
    def check_balance(entity_id: str = ""):
        entity_id = entity_id.strip()
        if not entity_id:
            raise HTTPException(status_code=400, detail="entity_id is required")
        balance = get_balance(entity_id)
        return {"entity_id": entity_id, "wallet_balance": balance}

    @app.post("/api/transfer")
    def transfer(payload: dict):
        sender_id = (payload.get("sender_id") or "").strip()
        receiver_id = (payload.get("receiver_id") or "").strip()
        amount = payload.get("amount")
        token_id = payload.get("token_id")
        note = payload.get("note") or "manual_transfer"

        if not sender_id or not receiver_id or amount is None:
            raise HTTPException(status_code=400, detail="sender_id, receiver_id, and amount are required")

        conn = get_db()
        try:
            tx_id = transfer_funds(
                sender_id=sender_id,
                receiver_id=receiver_id,
                amount=float(amount),
                note=note,
                connection=conn,
            )

            process_repayment(
                conn=conn,
                sender_id=sender_id,
                receiver_id=receiver_id,
                incoming_amount=float(amount),
                parent_tx_id=tx_id,
            )

            append_audit(
                action="TRANSFER_COMPLETED",
                entity_id=tx_id,
                amount=float(amount),
                token_id=token_id,
                outcome="SUCCESS",
                details={"sender_id": sender_id, "receiver_id": receiver_id},
                connection=conn,
            )

            return {
                "tx_id": tx_id,
                "status": "success",
                "balance_after": get_balance(receiver_id, connection=conn),
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/whatsapp-alert")
    def whatsapp_alert(payload: dict):
        phone = (payload.get("phone") or "").strip()
        message = (payload.get("message") or "").strip()

        if not phone or not message:
            raise HTTPException(status_code=400, detail="phone and message are required")

        conn = get_db()
        response = send_whatsapp(phone=phone, message=message, connection=conn)
        return response

    @app.get("/api/audit-log")
    def get_audit_log(limit: int = 100):
        conn = get_db()
        rows = conn.execute(
            """
            SELECT log_id, timestamp, action, entity_id, amount, token_id, outcome, details
            FROM audit_log
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        logs = []
        for row in rows:
            logs.append(
                {
                    "log_id": row["log_id"],
                    "timestamp": row["timestamp"],
                    "action": row["action"],
                    "entity_id": row["entity_id"],
                    "amount": row["amount"],
                    "token_id": row["token_id"],
                    "outcome": row["outcome"],
                    "details": row["details"],
                }
            )
        return {"logs": logs}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    init_db(reset=False, db_path=app.state.database_path)
    uvicorn.run(app, host="0.0.0.0", port=5000)
