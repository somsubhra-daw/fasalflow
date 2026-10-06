from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import MarketPrice, MarketArrival, Market


class ForecastResult(BaseModel):
    commodity_id: int
    commodity_code: str
    target_metric: str  # "MODAL_PRICE" | "ARRIVALS"
    forecast_value: Decimal
    period: str  # e.g., "7_DAYS"
    method: str  # e.g., "EXPONENTIAL_WEIGHTED_MOVING_AVERAGE"
    confidence: float
    data_points_used: int
    generated_at_date: date

    model_config = ConfigDict(from_attributes=True)


def forecast_price_trend(
    db: Session,
    commodity_id: int,
    district: str,
    lookback_days: int = 14,
) -> ForecastResult:
    """Deterministic statistical price forecasting using weighted moving average over recent market observations."""
    cutoff = date.today() - timedelta(days=lookback_days)

    prices = (
        db.query(MarketPrice.modal_price_per_kg)
        .join(Market, MarketPrice.market_id == Market.id)
        .filter(
            MarketPrice.commodity_id == commodity_id,
            Market.district.ilike(f"%{district.strip()}%"),
            MarketPrice.date >= cutoff,
        )
        .order_by(MarketPrice.date.asc())
        .all()
    )

    if not prices:
        # Fallback default if historical data window is empty
        return ForecastResult(
            commodity_id=commodity_id,
            commodity_code="POTATO",
            target_metric="MODAL_PRICE",
            forecast_value=Decimal("20.00"),
            period="7_DAYS",
            method="DEFAULT_BASELINE",
            confidence=0.50,
            data_points_used=0,
            generated_at_date=date.today(),
        )

    price_values = [p[0] for p in prices]
    # Linear weights: more recent days get higher weights
    weights = list(range(1, len(price_values) + 1))
    weighted_sum = sum(p * w for p, w in zip(price_values, weights))
    weighted_avg = weighted_sum / Decimal(sum(weights))

    return ForecastResult(
        commodity_id=commodity_id,
        commodity_code="POTATO",
        target_metric="MODAL_PRICE",
        forecast_value=round(weighted_avg, 2),
        period="7_DAYS",
        method="WEIGHTED_MOVING_AVERAGE",
        confidence=min(0.92, 0.65 + len(price_values) * 0.02),
        data_points_used=len(price_values),
        generated_at_date=date.today(),
    )
