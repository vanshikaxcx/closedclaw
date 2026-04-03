from __future__ import annotations

import random
from datetime import datetime, timedelta, UTC
from typing import Iterable


def _seed_for(merchant_id: str) -> int:
    return sum(ord(ch) for ch in merchant_id) * 97


def generate_transactions(
    merchant_id: str,
    days: int = 180,
    avg_daily_revenue: float = 18000.0,
) -> list[dict]:
    """Generate reproducible synthetic POS transactions for a merchant."""
    rng = random.Random(_seed_for(merchant_id))
    start = datetime.now(UTC) - timedelta(days=days - 1)

    txns: list[dict] = []
    for offset in range(days):
        day = start + timedelta(days=offset)

        # Weekly + growth seasonality.
        weekday = day.weekday()
        weekday_mult = 1.0
        if weekday in (4, 5):
            weekday_mult = 1.25
        elif weekday == 6:
            weekday_mult = 0.9

        growth_mult = 1 + (offset / max(1, days)) * 0.18
        day_revenue = avg_daily_revenue * weekday_mult * growth_mult
        day_revenue *= 1 + (rng.random() - 0.5) * 0.18
        day_revenue = max(6000.0, day_revenue)

        txn_count = max(8, int(day_revenue / 1200))
        remaining = day_revenue

        for idx in range(txn_count):
            if idx == txn_count - 1:
                amount = round(max(60.0, remaining), 2)
            else:
                chunk = max(60.0, (day_revenue / txn_count) * (0.5 + rng.random()))
                amount = round(min(chunk, remaining), 2)
                remaining -= amount

            txns.append(
                {
                    "tx_id": f"TXN-{merchant_id}-{day.date().isoformat()}-{idx}",
                    "merchant_id": merchant_id,
                    "amount": amount,
                    "timestamp": (day + timedelta(minutes=idx * 9)).isoformat(),
                    "raw_description": "PayBot POS sale",
                    "type": "sale",
                }
            )

    return txns


def generate_transactions_for_merchants(merchant_ids: Iterable[str], days: int = 180) -> list[dict]:
    all_rows: list[dict] = []
    for merchant_id in merchant_ids:
        all_rows.extend(generate_transactions(merchant_id=merchant_id, days=days))
    return all_rows
