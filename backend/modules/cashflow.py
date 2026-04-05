import json
from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from statistics import mean

from fastapi import APIRouter, HTTPException


cashflow_router = APIRouter()

DATASET_PATH = Path(__file__).resolve().parents[2] / "arthsetu_all_merchants.json"
CONFIDENCE_BANDS = {
    30: 0.10,
    60: 0.18,
    90: 0.25,
}


@lru_cache(maxsize=1)
def _load_grouped_history() -> dict[str, list[tuple[date, float]]]:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}")

    raw = json.loads(DATASET_PATH.read_text())
    if not isinstance(raw, list):
        raise ValueError("Expected top-level list in merchant dataset")

    grouped: dict[str, list[tuple[date, float]]] = defaultdict(list)
    for row in raw:
        merchant_id = str(row.get("merchant_id", "")).strip()
        if not merchant_id:
            continue

        try:
            record_date = date.fromisoformat(str(row["date"]))
            daily_revenue = float(row["daily_revenue"])
        except (KeyError, TypeError, ValueError):
            continue

        grouped[merchant_id].append((record_date, daily_revenue))

    for merchant_id in grouped:
        grouped[merchant_id].sort(key=lambda item: item[0])

    return grouped


def _seasonal_multiplier(day: date) -> float:
    multiplier = 1.0

    weekday = day.weekday()  # Monday=0 ... Sunday=6
    if weekday in (4, 5):
        multiplier *= 1.3
    elif weekday == 6:
        multiplier *= 0.9

    last_day = monthrange(day.year, day.month)[1]
    if day.day >= last_day - 2:
        multiplier *= 1.2

    return multiplier


def _seasonal_weighted_baseline(history_revenue: list[float]) -> float:
    # Weighted blend of short/medium windows for better responsiveness and stability.
    windows = [
        (7, 0.50),
        (14, 0.30),
        (28, 0.20),
    ]

    weighted_sum = 0.0
    total_weight = 0.0

    for window_size, weight in windows:
        if len(history_revenue) >= window_size:
            weighted_sum += mean(history_revenue[-window_size:]) * weight
            total_weight += weight

    if total_weight == 0:
        raise ValueError("Insufficient history to compute baseline")

    return weighted_sum / total_weight


def _projection_for_horizon(merchant_id: str, horizon_days: int) -> dict:
    grouped = _load_grouped_history()
    history = grouped.get(merchant_id)
    if not history:
        raise KeyError(merchant_id)

    history_revenue = [value for _, value in history]
    baseline = _seasonal_weighted_baseline(history_revenue)
    last_date = history[-1][0]

    projected_daily = []
    for offset in range(1, horizon_days + 1):
        day = last_date + timedelta(days=offset)
        projected_daily.append(baseline * _seasonal_multiplier(day))

    amount = round(sum(projected_daily), 2)
    band = CONFIDENCE_BANDS[horizon_days]

    return {
        "merchant_id": merchant_id,
        "last_historical_date": last_date.isoformat(),
        "history_days": len(history_revenue),
        "baseline_seasonal_weighted": round(baseline, 2),
        "projection": {
            "horizon_days": horizon_days,
            "amount": amount,
            "confidence_low": round(amount * (1.0 - band), 2),
            "confidence_high": round(amount * (1.0 + band), 2),
            "confidence_band": f"+/-{int(band * 100)}%",
        },
    }


def _build_response(horizon_days: int, merchant_id: str | None) -> dict:
    try:
        grouped = _load_grouped_history()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    merchant_id = (merchant_id or "").strip()

    if merchant_id:
        if merchant_id not in grouped:
            raise HTTPException(status_code=404, detail="merchant not found")
        projections = [_projection_for_horizon(merchant_id, horizon_days)]
    else:
        projections = [_projection_for_horizon(mid, horizon_days) for mid in sorted(grouped.keys())]

    return {
        "baseline_method": "seasonal_weighted_baseline",
        "weights": {
            "last_7_days": 0.50,
            "last_14_days": 0.30,
            "last_28_days": 0.20,
        },
        "seasonality": {
            "friday_saturday": 1.3,
            "sunday": 0.9,
            "month_end_last_3_days": 1.2,
        },
        "horizon_days": horizon_days,
        "merchant_count": len(projections),
        "projections": projections,
    }


@cashflow_router.get("/api/cashflow-30")
def get_cashflow_30(merchant_id: str | None = None):
    return _build_response(30, merchant_id)


@cashflow_router.get("/api/cashflow-60")
def get_cashflow_60(merchant_id: str | None = None):
    return _build_response(60, merchant_id)


@cashflow_router.get("/api/cashflow-90")
def get_cashflow_90(merchant_id: str | None = None):
    return _build_response(90, merchant_id)
