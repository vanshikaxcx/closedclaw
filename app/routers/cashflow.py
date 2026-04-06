from __future__ import annotations

from datetime import date, datetime, timedelta
from statistics import mean, pstdev
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import COLL_MERCHANTS, COLL_TRANSACTIONS, DatabaseClient, get_document, list_documents, utc_now_iso
from app.dependencies import get_firestore_db

router = APIRouter()


def _safe_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except Exception:
        return None


def _merchant_or_404(db: DatabaseClient, merchant_id: str) -> dict[str, Any]:
    merchant = get_document(db, COLL_MERCHANTS, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail={"error": "merchant not found", "merchant_id": merchant_id})
    return merchant


def _daily_history_rows(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[date, dict[str, Any]] = {}

    for row in transactions:
        dt = _safe_date(row.get("timestamp"))
        if dt is None:
            continue
        amount = float(row.get("amount") or 0.0)

        if dt not in grouped:
            grouped[dt] = {"date": dt, "amount": 0.0, "transaction_count": 0}

        grouped[dt]["amount"] += amount
        grouped[dt]["transaction_count"] += 1

    out = []
    for dt in sorted(grouped):
        item = grouped[dt]
        out.append(
            {
                "date": dt.isoformat(),
                "amount": round(item["amount"], 2),
                "transaction_count": int(item["transaction_count"]),
            }
        )

    return out


def _trend_stats(daily: list[dict[str, Any]]) -> tuple[str, float, float, float]:
    recent = daily[-30:]
    prior = daily[-60:-30]

    recent_avg = mean([row["amount"] for row in recent]) if recent else 0.0
    prior_avg = mean([row["amount"] for row in prior]) if prior else recent_avg

    if prior_avg <= 0:
        strength = 0.0
    else:
        strength = abs((recent_avg - prior_avg) / prior_avg) * 100

    if recent_avg > prior_avg * 1.05:
        direction = "growing"
    elif recent_avg < prior_avg * 0.95:
        direction = "declining"
    else:
        direction = "stable"

    return direction, round(strength, 1), round(recent_avg, 2), round(prior_avg, 2)


def _seasonality_multiplier(day: date) -> float:
    multiplier = 1.0

    weekday = day.weekday()
    if weekday in (4, 5):
        multiplier *= 1.3
    elif weekday == 6:
        multiplier *= 0.9

    next_month = (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    month_last_day = (next_month - timedelta(days=1)).day
    if day.day >= month_last_day - 2:
        multiplier *= 1.2

    return multiplier


def _projection_from_baseline(last_14_mean: float, start_date: date, horizon: int) -> tuple[float, list[float]]:
    points: list[float] = []
    for idx in range(1, horizon + 1):
        day = start_date + timedelta(days=idx)
        points.append(last_14_mean * _seasonality_multiplier(day))
    return round(sum(points), 2), points


def _confidence_bounds(amount: float, pct: float) -> tuple[float, float]:
    return round(amount * (1 - pct), 2), round(amount * (1 + pct), 2)


def _daily_projection_history(last_14_mean: float, start_date: date, days: int = 30) -> list[dict[str, Any]]:
    rows = []
    for idx in range(1, days + 1):
        day = start_date + timedelta(days=idx)
        amount = last_14_mean * _seasonality_multiplier(day)
        rows.append(
            {
                "date": day.isoformat(),
                "amount": round(amount, 2),
                "transaction_count": max(1, round(amount / 700)),
                "is_projected": True,
                "lower_bound": round(amount * 0.9, 2),
                "upper_bound": round(amount * 1.1, 2),
            }
        )
    return rows


def _insight(health_label: str, avg_daily: float, trend: str, strength: float, outlook: str) -> str:
    return (
        f"Revenue is {health_label.lower()} at Rs. {round(avg_daily, 0)}/day average. "
        f"A {round(strength, 1)}% {trend} trend over the past 30 days suggests a {outlook} outlook ahead."
    )


@router.post("/cashflow/analyze/{merchant_id}")
def post_cashflow_analyze(merchant_id: str, db: DatabaseClient = Depends(get_firestore_db)):
    _merchant_or_404(db, merchant_id)

    transactions = list_documents(
        db,
        COLL_TRANSACTIONS,
        filters=[("merchant_id", "==", merchant_id)],
        order_by="timestamp",
        descending=False,
        limit=20000,
    )

    daily = _daily_history_rows(transactions)
    days_available = len(daily)
    if days_available < 30:
        return {"error": "insufficient_data", "days_available": days_available, "days_required": 30}

    amounts = [row["amount"] for row in daily]
    avg_daily = mean(amounts)
    stddev = pstdev(amounts) if len(amounts) > 1 else 0.0
    cov = stddev / avg_daily if avg_daily > 0 else 0.0
    health_score = max(0.0, min(100.0, 100.0 - (cov * 100.0)))

    if health_score >= 75:
        health_label = "Healthy"
    elif health_score >= 50:
        health_label = "Moderate"
    else:
        health_label = "Volatile"

    trend, strength, recent_avg, prior_avg = _trend_stats(daily)

    baseline_window = daily[-14:]
    baseline = mean([row["amount"] for row in baseline_window])
    start_date = _safe_date(daily[-1]["date"]) or date.today()

    p30_amount, p30_points = _projection_from_baseline(baseline, start_date, 30)
    p60_amount, _ = _projection_from_baseline(baseline, start_date, 60)
    p90_amount, _ = _projection_from_baseline(baseline, start_date, 90)

    p30_low, p30_high = _confidence_bounds(p30_amount, 0.10)
    p60_low, p60_high = _confidence_bounds(p60_amount, 0.18)
    p90_low, p90_high = _confidence_bounds(p90_amount, 0.25)

    current_month_actual = sum(row["amount"] for row in daily[-30:])
    if p30_amount > current_month_actual * 1.1:
        outlook = "positive"
    elif p30_amount < current_month_actual * 0.9:
        outlook = "negative"
    else:
        outlook = "neutral"

    alerts = []
    last_30_revenue = sum(row["amount"] for row in daily[-30:])
    estimated_stock_cost = last_30_revenue * 0.30
    projected_inflow_next_7 = round(sum(p30_points[:7]), 2)

    if projected_inflow_next_7 > estimated_stock_cost * 0.8:
        alerts.append(
            {
                "type": "stock_reorder",
                "message": "Projected inflow indicates safe stock reorder window in the coming week.",
                "severity": "info",
            }
        )

    consecutive_declines = 0
    for idx in range(max(1, len(daily) - 20), len(daily)):
        if daily[idx]["amount"] < daily[idx - 1]["amount"]:
            consecutive_declines += 1
        else:
            consecutive_declines = 0

    if trend == "declining" and consecutive_declines >= 14:
        alerts.append(
            {
                "type": "cash_warning",
                "message": "Cashflow has declined for over two weeks. Review collections and payouts.",
                "severity": "warning",
            }
        )

    if trend == "growing":
        alerts.append(
            {
                "type": "positive_trend",
                "message": "Revenue trend is positive. Financing eligibility may improve.",
                "severity": "info",
            }
        )

    response_history = [
        {
            "date": row["date"],
            "amount": row["amount"],
            "transaction_count": row["transaction_count"],
            "is_projected": False,
            "lower_bound": round(row["amount"] * 0.9, 2),
            "upper_bound": round(row["amount"] * 1.1, 2),
        }
        for row in daily[-180:]
    ] + _daily_projection_history(baseline, start_date, days=30)

    return {
        "merchant_id": merchant_id,
        "analysis_date": utc_now_iso(),
        "health": {
            "score": round(health_score, 2),
            "label": health_label,
            "avg_daily_revenue": round(avg_daily, 2),
            "stddev": round(stddev, 2),
            "coefficient_of_variation": round(cov, 4),
        },
        "trend": {
            "direction": trend,
            "strength_pct": strength,
            "recent_30d_avg": recent_avg,
            "prior_30d_avg": prior_avg,
        },
        "projections": {
            "p30": {"amount": p30_amount, "lower": p30_low, "upper": p30_high, "confidence": 90},
            "p60": {"amount": p60_amount, "lower": p60_low, "upper": p60_high, "confidence": 82},
            "p90": {"amount": p90_amount, "lower": p90_low, "upper": p90_high, "confidence": 75},
        },
        "outlook": outlook,
        "alerts": alerts,
        "insight": _insight(health_label, avg_daily, trend, strength, outlook),
        "daily_history": response_history,
    }


@router.get("/merchants")
def get_cashflow_merchants(db: DatabaseClient = Depends(get_firestore_db)):
    merchants = list_documents(db, COLL_MERCHANTS, order_by="merchant_id", descending=False, limit=500)

    result = []
    for merchant in merchants:
        if str(merchant.get("role") or "merchant") != "merchant":
            continue
        merchant_id = str(merchant.get("merchant_id") or merchant.get("id"))
        txns = list_documents(db, COLL_TRANSACTIONS, filters=[("merchant_id", "==", merchant_id)], limit=5000)
        daily = _daily_history_rows(txns)
        avg = mean([row["amount"] for row in daily]) if daily else 0.0
        result.append(
            {
                "merchant_id": merchant_id,
                "name": merchant.get("name") or "",
                "business_name": merchant.get("business_name") or "",
                "category": merchant.get("category") or "",
                "city": merchant.get("city") or "",
                "avg_daily_revenue": round(avg, 2),
                "transaction_count": len(txns),
            }
        )

    return {"merchants": result}


@router.get("/cashflow/history/{merchant_id}")
def get_cashflow_history(
    merchant_id: str,
    days: int = Query(default=30, ge=1, le=180),
    db: DatabaseClient = Depends(get_firestore_db),
):
    _merchant_or_404(db, merchant_id)

    txns = list_documents(
        db,
        COLL_TRANSACTIONS,
        filters=[("merchant_id", "==", merchant_id)],
        order_by="timestamp",
        descending=False,
        limit=20000,
    )
    daily = _daily_history_rows(txns)

    trimmed = daily[-days:]
    history = [
        {
            "date": row["date"],
            "amount": row["amount"],
            "transaction_count": row["transaction_count"],
            "day_of_week": (date.fromisoformat(row["date"]).strftime("%A")),
        }
        for row in trimmed
    ]

    return {
        "merchant_id": merchant_id,
        "days_requested": days,
        "days_available": len(daily),
        "daily_history": history,
    }


@router.get("/health")
def get_cashflow_health(db: DatabaseClient = Depends(get_firestore_db)):
    merchants = list_documents(db, COLL_MERCHANTS, order_by="merchant_id", descending=False, limit=500)
    count = 0
    for merchant in merchants:
        if str(merchant.get("role") or "merchant") != "merchant":
            continue
        merchant_id = str(merchant.get("merchant_id") or merchant.get("id"))
        txns = list_documents(db, COLL_TRANSACTIONS, filters=[("merchant_id", "==", merchant_id)], limit=20000)
        unique_days = {(_safe_date(row.get("timestamp"))) for row in txns}
        unique_days = {row for row in unique_days if row is not None}
        if len(unique_days) >= 30:
            count += 1

    return {"status": "ok", "engine": "loaded", "merchants_with_data": count}
