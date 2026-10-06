from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.models import (
    Commodity,
    FarmerSupply,
    Farm,
    ColdStoreInventory,
    ColdStore,
    BuyerDemand,
    MarketPrice,
    Market,
)
from app.models.enums import SupplyStatus, DemandStatus
from app.intelligence.features.metrics import MarketSupplyDemandMetrics


# Post-harvest loss estimation factor for fresh root vegetables (e.g., 5%)
ESTIMATED_POST_HARVEST_LOSS_RATE = Decimal("0.05")
# Projected release rate from cold stores per week (e.g. 5% of storage balance)
ESTIMATED_STORAGE_RELEASE_RATE = Decimal("0.05")


def calculate_shared_supply_demand(
    db: Session,
    commodity_id: int,
    district: str,
    window_days: int = 7,
    reference_date: Optional[date] = None,
) -> MarketSupplyDemandMetrics:
    """Calculate deterministic Effective Supply, Forecast Demand, and Supply Gap.
    Formula:
        Effective Supply = Expected Fresh Supply + Expected Storage Release - Existing Commitments - Expected Loss
        Supply Gap = Forecast Demand - Effective Supply
    """
    ref_date = reference_date or date.today()
    end_date = ref_date + timedelta(days=window_days)

    commodity = db.query(Commodity).filter(Commodity.id == commodity_id).first()
    if not commodity:
        raise ValueError(f"Commodity ID {commodity_id} not found")

    # 1. Expected Fresh Supply: sum of farmer supply in district harvesting within window
    fresh_supply_query = (
        db.query(func.coalesce(func.sum(FarmerSupply.quantity_kg), Decimal(0)))
        .join(Farm, FarmerSupply.farm_id == Farm.id)
        .filter(
            FarmerSupply.commodity_id == commodity_id,
            Farm.district.ilike(f"%{district.strip()}%"),
            FarmerSupply.expected_harvest_date >= ref_date,
            FarmerSupply.expected_harvest_date <= end_date,
            FarmerSupply.status.in_([SupplyStatus.PLANNED, SupplyStatus.READY]),
        )
        .scalar()
    )
    expected_fresh_supply = Decimal(fresh_supply_query or Decimal(0))

    # 2. Storage stock in district
    storage_stock_query = (
        db.query(func.coalesce(func.sum(ColdStoreInventory.current_quantity_kg), Decimal(0)))
        .join(ColdStore, ColdStoreInventory.cold_store_id == ColdStore.id)
        .filter(
            ColdStoreInventory.commodity_id == commodity_id,
            ColdStore.district.ilike(f"%{district.strip()}%"),
        )
        .scalar()
    )
    storage_stock = Decimal(storage_stock_query or Decimal(0))
    expected_storage_release = round(storage_stock * ESTIMATED_STORAGE_RELEASE_RATE, 2)

    # 3. Existing commitments & post-harvest loss
    existing_commitments = Decimal(0)  # contracts already accounted for
    expected_loss = round(expected_fresh_supply * ESTIMATED_POST_HARVEST_LOSS_RATE, 2)

    # Effective Supply
    effective_supply = (
        expected_fresh_supply
        + expected_storage_release
        - existing_commitments
        - expected_loss
    )
    if effective_supply < 0:
        effective_supply = Decimal(0)

    # 4. Forecast Demand: active buyer demands overlapping the window in district
    demand_query = (
        db.query(func.coalesce(func.sum(BuyerDemand.quantity_kg), Decimal(0)))
        .filter(
            BuyerDemand.commodity_id == commodity_id,
            BuyerDemand.status == DemandStatus.ACTIVE,
            BuyerDemand.required_from <= end_date,
            BuyerDemand.required_until >= ref_date,
        )
        .scalar()
    )
    forecast_demand = Decimal(demand_query or Decimal(0))

    # 5. Supply Gap: Demand - Effective Supply
    supply_gap = forecast_demand - effective_supply

    if supply_gap > 0:
        status = "SHORTAGE"
    elif supply_gap < 0:
        status = "SURPLUS"
    else:
        status = "BALANCED"

    # 6. Current Modal Price & Trend
    latest_prices = (
        db.query(MarketPrice)
        .join(Market, MarketPrice.market_id == Market.id)
        .filter(
            MarketPrice.commodity_id == commodity_id,
            Market.district.ilike(f"%{district.strip()}%"),
        )
        .order_by(MarketPrice.date.desc())
        .limit(2)
        .all()
    )

    current_modal_price = None
    price_trend = "STABLE"
    if latest_prices:
        current_modal_price = latest_prices[0].modal_price_per_kg
        if len(latest_prices) > 1:
            diff = latest_prices[0].modal_price_per_kg - latest_prices[1].modal_price_per_kg
            if diff > Decimal("0.50"):
                price_trend = "UPWARD"
            elif diff < Decimal("-0.50"):
                price_trend = "DOWNWARD"

    return MarketSupplyDemandMetrics(
        commodity_id=commodity.id,
        commodity_name=commodity.name,
        commodity_code=commodity.code,
        district=district,
        window_days=window_days,
        start_date=ref_date,
        end_date=end_date,
        expected_fresh_supply_kg=expected_fresh_supply,
        expected_storage_release_kg=expected_storage_release,
        existing_commitments_kg=existing_commitments,
        expected_loss_kg=expected_loss,
        effective_supply_kg=effective_supply,
        forecast_demand_kg=forecast_demand,
        supply_gap_kg=supply_gap,
        status=status,
        current_modal_price=current_modal_price,
        price_trend=price_trend,
    )
