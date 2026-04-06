from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict


class HealthResponse(BaseModel):
    status: str
    version: str
    db: str
    wallet_store: str
    merchant_count: int
    demo_mode: bool
    timestamp: str


class ResetDemoResponse(BaseModel):
    status: str
    merchant_id: str
    reset_at: str


class WalletBalanceResponse(BaseModel):
    merchant_id: str
    balance: float
    currency: str = "INR"
    last_updated: str


class TransferRequest(BaseModel):
    from_id: str
    to_upi_id: str
    amount: float
    note: str | None = ""
    token_id: str | None = None


class TransferConfirmRequest(BaseModel):
    transfer_id: str
    merchant_id: str


class TrustScoreEventRequest(BaseModel):
    merchant_id: str
    event_type: Literal[
        "PAYMENT_RECEIVED",
        "GST_FILED",
        "RETURN_RAISED",
        "INVOICE_OVERDUE",
        "TRANSFER_COMPLETED",
    ]
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreditOfferRequest(BaseModel):
    merchant_id: str
    invoice_id: str


class CreditAcceptRequest(BaseModel):
    offer_id: str
    merchant_id: str


class NotificationReadAllRequest(BaseModel):
    merchant_id: str


class WhatsappAlertRequest(BaseModel):
    merchant_id: str
    phone: str
    message: str


class LoginRequest(BaseModel):
    merchant_id: str
    pin_hash: str


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    phone: str
    role: Literal["merchant", "consumer", "admin"] = "merchant"
    pin_hash: str
    merchant_id: str | None = None
    business_name: str | None = None
    gstin: str | None = None
    category: str | None = None
    city: str | None = None


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20


class DateRangeParams(BaseModel):
    from_date: datetime | None = None
    to_date: datetime | None = None
