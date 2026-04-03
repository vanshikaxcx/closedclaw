"""
ArthSetu — Main FastAPI Application
Registers all module routers, configures CORS, and initializes the database.
"""

import os
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import init_db
from backend.modules.paybot.paybot import router as paybot_router

# Initialize database on startup
init_db()

app = FastAPI(
    title="ArthSetu — Agentic Commerce Platform",
    description=(
        "ArthSetu is an integrated financial platform for Indian SMBs. "
        "PayBot is the agentic payment assistant that enables natural language "
        "purchase execution with 9-layer security, scoped delegation tokens, "
        "and human-in-the-loop approval."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(paybot_router)


@app.get("/")
async def root():
    """Root endpoint — service info."""
    return {
        "service": "ArthSetu",
        "module": "PayBot — Agentic Commerce",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
        "endpoints": {
            "parse_intent": "POST /api/parse-intent",
            "agent_execute": "POST /api/agent/execute",
            "transfer": "POST /api/transfer",
            "transfer_confirm": "POST /api/transfer-confirm",
            "transfer_cancel": "POST /api/transfer-cancel",
            "search_merchants": "POST /api/agent/search-merchants",
            "prepare_order": "POST /api/agent/prepare-order",
            "check_balance": "GET /api/agent/check-balance",
            "token_status": "GET /api/token-status",
            "merchants": "GET /api/merchants",
            "audit_log": "GET /api/audit-log",
        },
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    print(f"\n🚀 ArthSetu PayBot starting on http://{host}:{port}")
    print(f"📚 API Docs: http://{host}:{port}/docs")
    print(f"🏥 Health: http://{host}:{port}/api/health\n")
    uvicorn.run("backend.app:app", host=host, port=port, reload=True)
