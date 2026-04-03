from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import count_collection, demo_mode_enabled, demo_seed_on_startup_enabled, get_db, init_firestore
from app.routers.audit import router as audit_router
from app.routers.ai_assistant import router as ai_assistant_router
from app.routers.cashflow import router as cashflow_router
from app.routers.health import router as health_router
from app.routers.invoices import router as invoices_router
from app.routers.merchants import router as merchants_router
from app.routers.notifications import router as notifications_router
from app.routers.gst_module import router as gst_module_router
from app.routers.trustscore import router as trustscore_router
from app.routers.wallet import router as wallet_router
from app.seed import SEED_MERCHANT_ID, ensure_seed_data
from app.wallet import initialize_wallet_store


app = FastAPI(title="ArthSetu Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    response = await call_next(request)
    print(f"[{datetime.now().isoformat()}] {request.method} {request.url.path} -> {response.status_code}")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": str(exc)},
    )


@app.on_event("startup")
def on_startup() -> None:
    init_firestore()
    db = get_db()
    startup_mode = "normal"
    demo_mode = demo_mode_enabled()
    demo_seed_on_startup = demo_seed_on_startup_enabled()

    try:
        if demo_seed_on_startup:
            merchant_count = ensure_seed_data(db, force=False)
        else:
            merchant_count = count_collection(db, "merchants")
    except Exception as exc:
        startup_mode = "degraded"
        print(f"Startup data check skipped due to database issue: {exc}")
        try:
            merchant_count = count_collection(db, "merchants")
        except Exception:
            merchant_count = 0

    try:
        initialize_wallet_store(db)
    except Exception as exc:
        startup_mode = "degraded"
        print(f"Wallet store initialization skipped due to database issue: {exc}")

    print(
        "ArthSetu backend ready. "
        f"{merchant_count} merchants loaded. "
        f"Demo merchant: {SEED_MERCHANT_ID if demo_mode else 'disabled'}. "
        f"Demo startup seed: {'enabled' if demo_seed_on_startup else 'disabled'}. "
        f"Startup mode: {startup_mode}."
    )


app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(wallet_router, prefix="/api", tags=["wallet"])
app.include_router(trustscore_router, prefix="/api", tags=["trustscore"])
app.include_router(invoices_router, prefix="/api", tags=["invoices"])
app.include_router(audit_router, prefix="/api", tags=["audit"])
app.include_router(merchants_router, prefix="/api", tags=["merchants"])
app.include_router(notifications_router, prefix="/api", tags=["notifications"])
app.include_router(gst_module_router, prefix="/api", tags=["gst-module"])
app.include_router(ai_assistant_router, prefix="/api", tags=["ai-assistant"])
app.include_router(cashflow_router, tags=["cashflow"])
