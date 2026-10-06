from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict


class MarketSupplyDemandMetrics(BaseModel):
    commodity_id: int
    commodity_name: str
    commodity_code: str
    district: str
    window_days: int
    start_date: date
    end_date: date

    # Supply metrics
    expected_fresh_supply_kg: Decimal
    expected_storage_release_kg: Decimal
    existing_commitments_kg: Decimal
    expected_loss_kg: Decimal
    effective_supply_kg: Decimal

    # Demand metrics
    forecast_demand_kg: Decimal

    # Market gap calculation: Demand - Effective Supply
    # Positive: Shortage (Demand > Supply)
    # Negative: Surplus (Supply > Demand)
    # Zero: Balanced
    supply_gap_kg: Decimal
    status: str  # "SURPLUS" | "SHORTAGE" | "BALANCED"

    # Price indicators
    current_modal_price: Optional[Decimal] = None
    price_trend: Optional[str] = None  # "UPWARD" | "DOWNWARD" | "STABLE"

    model_config = ConfigDict(from_attributes=True)
