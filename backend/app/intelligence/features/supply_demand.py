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
    Buyer,
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
# Minimum price change in INR/kg required to declare an UPWARD or DOWNWARD trend
PRICE_TREND_THRESHOLD = Decimal("0.50")


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

    # 1. Expected Fresh Supply: sum of farmer remaining supply in district harvesting within window
    fresh_supply_query = (
        db.query(func.coalesce(func.sum(FarmerSupply.remaining_quantity_kg), Decimal(0)))
        .join(Farm, FarmerSupply.farm_id == Farm.id)
        .filter(
            FarmerSupply.commodity_id == commodity_id,
            Farm.district.ilike(f"%{district.strip()}%"),
            FarmerSupply.expected_harvest_date >= ref_date,
            FarmerSupply.expected_harvest_date <= end_date,
            FarmerSupply.status.in_([SupplyStatus.PLANNED, SupplyStatus.READY, SupplyStatus.PARTIALLY_SOLD]),
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

    # 4. Forecast Demand: active buyer demands strictly scoped to the target district overlapping the window
    norm_district = district.strip().lower()
    demand_query = (
        db.query(func.coalesce(func.sum(BuyerDemand.quantity_kg), Decimal(0)))
        .join(Buyer, BuyerDemand.buyer_id == Buyer.id)
        .filter(
            BuyerDemand.commodity_id == commodity_id,
            func.lower(func.trim(Buyer.district)) == norm_district,
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
    # Daily-aggregate modal prices across all markets in the district before comparing consecutive dates.
    # Comparing different markets on the same date creates false trends; we must group by date first.
    daily_price_rows = (
        db.query(
            MarketPrice.date,
            func.avg(MarketPrice.modal_price_per_kg).label("avg_modal_price"),
        )
        .join(Market, MarketPrice.market_id == Market.id)
        .filter(
            MarketPrice.commodity_id == commodity_id,
            Market.district.ilike(f"%{district.strip()}%"),
        )
        .group_by(MarketPrice.date)
        .order_by(MarketPrice.date.desc())
        .limit(2)
        .all()
    )

    current_modal_price = None
    price_trend = None
    if daily_price_rows:
        price_trend = "STABLE"
        current_modal_price = Decimal(str(round(daily_price_rows[0].avg_modal_price, 2)))
        if len(daily_price_rows) > 1:
            prev_modal_price = Decimal(str(round(daily_price_rows[1].avg_modal_price, 2)))
            diff = current_modal_price - prev_modal_price
            if diff > PRICE_TREND_THRESHOLD:
                price_trend = "UPWARD"
            elif diff < -PRICE_TREND_THRESHOLD:
                price_trend = "DOWNWARD"
            else:
                price_trend = "STABLE"

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
