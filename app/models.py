from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MerchantModel:
    merchant_id: str
    name: str
    business_name: str
    category: str
    city: str
    phone: str
    gstin: str
    kyc_status: str = "pending"
    wallet_balance: float = 0.0
    trust_score: int = 0
    trust_bucket: str = "Low"
    role: str = "merchant"
    upi_id: str | None = None
    pin_hash: str | None = None
    created_at: str | None = None


@dataclass(slots=True)
class InvoiceModel:
    invoice_id: str
    merchant_id: str
    buyer_name: str
    buyer_gstin: str
    amount: float
    due_date: str
    status: str
    overdue_days: int = 0
    advance_amount: float = 0.0
    fee_rate: float = 0.0
    offer_id: str | None = None
    repaid: bool = False
    created_at: str | None = None
    paid_at: str | None = None


@dataclass(slots=True)
class TrustScoreModel:
    merchant_id: str
    score: int
    bucket: str
    components: dict[str, float] = field(default_factory=dict)
    computed_at: str | None = None


@dataclass(slots=True)
class AuditModel:
    log_id: str
    timestamp: str
    actor_type: str
    actor_id: str
    action: str
    outcome: str
    entity_id: str | None = None
    amount: float | None = None
    token_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
