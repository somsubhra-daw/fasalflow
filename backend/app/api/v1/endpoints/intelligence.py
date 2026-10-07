from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.auth.dependencies import require_farmer, require_cold_store_operator
from app.models.models import (
    User,
    Farmer,
    ColdStoreOperator,
    ColdStore,
    ColdStoreInventory,
    ColdStoreEvent,
    Commodity,
    MarketPrice,
)
from app.models.enums import ColdStoreEventType
from app.intelligence.features.metrics import MarketSupplyDemandMetrics
from app.intelligence.features.supply_demand import calculate_shared_supply_demand
from app.intelligence.features.dashboard_schemas import (
    RiskAssessment,
    ActionRecommendation,
    FarmerIntelligenceDashboard,
    ColdStoreIntelligenceDashboard,
)
from app.intelligence.risk.farmer import evaluate_farmer_risks, generate_farmer_recommendations
from app.intelligence.risk.cold_store import evaluate_cold_store_risks, generate_cold_store_recommendations
from app.intelligence.forecasting.statistical import forecast_price_trend, ForecastResult

router = APIRouter(prefix="/intelligence", tags=["Intelligence Engine"])


# =====================================================================
# FARMER INTELLIGENCE ENDPOINTS
# =====================================================================
@router.get("/farmer/dashboard", response_model=FarmerIntelligenceDashboard)
def farmer_dashboard(
    commodity_id: int = Query(default=1),
    window_days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
) -> FarmerIntelligenceDashboard:
    """Generate farmer decision-support dashboard based on regional supply-demand balance and price trends."""
    farmer = db.query(Farmer).filter(Farmer.user_id == current_user.id).first()
    district = farmer.district if farmer else "Purba Bardhaman"

    # Aggregate this specific farmer's active produce in this commodity
    farmer_active_qty = Decimal(0)
    if farmer:
        from app.models.models import Farm, FarmerSupply
        from app.models.enums import SupplyStatus
        qty_val = (
            db.query(func.coalesce(func.sum(FarmerSupply.remaining_quantity_kg), Decimal(0)))
            .join(Farm, FarmerSupply.farm_id == Farm.id)
            .filter(
                Farm.farmer_id == farmer.id,
                FarmerSupply.commodity_id == commodity_id,
                FarmerSupply.status.in_([SupplyStatus.PLANNED, SupplyStatus.READY, SupplyStatus.PARTIALLY_SOLD]),
            )
            .scalar()
        )
        farmer_active_qty = Decimal(qty_val or Decimal(0))

    metrics = calculate_shared_supply_demand(
        db=db,
        commodity_id=commodity_id,
        district=district,
        window_days=window_days,
    )

    # Calculate farmer exposure metrics
    farmer_share_pct = Decimal(0)
    if metrics.effective_supply_kg > 0:
        farmer_share_pct = round((farmer_active_qty / metrics.effective_supply_kg) * 100, 2)

    farmer_exposure_level = "LOW"
    if farmer_active_qty >= Decimal(25000):
        farmer_exposure_level = "HIGH"
    elif farmer_active_qty >= Decimal(10000):
        farmer_exposure_level = "MEDIUM"

    risks = evaluate_farmer_risks(metrics, farmer_quantity_kg=farmer_active_qty)
    recs = generate_farmer_recommendations(metrics, risks, farmer_quantity_kg=farmer_active_qty)

    return FarmerIntelligenceDashboard(
        commodity_name=metrics.commodity_name,
        district=district,
        window_days=window_days,
        current_modal_price=metrics.current_modal_price,
        price_trend=metrics.price_trend,
        expected_local_supply_kg=metrics.expected_fresh_supply_kg,
        visible_demand_kg=metrics.forecast_demand_kg,
        supply_gap_kg=metrics.supply_gap_kg,
        market_status=metrics.status,
        farmer_active_supply_kg=farmer_active_qty,
        farmer_supply_share_pct=farmer_share_pct,
        farmer_exposure_level=farmer_exposure_level,
        risks=risks,
        recommendations=recs,
    )


@router.get("/farmer/risks", response_model=List[RiskAssessment])
def farmer_risks(
    commodity_id: int = Query(default=1),
    window_days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
) -> List[RiskAssessment]:
    """Retrieve detailed risk assessments for the authenticated farmer."""
    farmer = db.query(Farmer).filter(Farmer.user_id == current_user.id).first()
    district = farmer.district if farmer else "Purba Bardhaman"

    farmer_active_qty = Decimal(0)
    if farmer:
        from app.models.models import Farm, FarmerSupply
        from app.models.enums import SupplyStatus
        qty_val = (
            db.query(func.coalesce(func.sum(FarmerSupply.remaining_quantity_kg), Decimal(0)))
            .join(Farm, FarmerSupply.farm_id == Farm.id)
            .filter(
                Farm.farmer_id == farmer.id,
                FarmerSupply.commodity_id == commodity_id,
                FarmerSupply.status.in_([SupplyStatus.PLANNED, SupplyStatus.READY, SupplyStatus.PARTIALLY_SOLD]),
            )
            .scalar()
        )
        farmer_active_qty = Decimal(qty_val or Decimal(0))

    metrics = calculate_shared_supply_demand(
        db=db, commodity_id=commodity_id, district=district, window_days=window_days
    )
    return evaluate_farmer_risks(metrics, farmer_quantity_kg=farmer_active_qty)


@router.get("/farmer/recommendations", response_model=List[ActionRecommendation])
def farmer_recommendations(
    commodity_id: int = Query(default=1),
    window_days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
) -> List[ActionRecommendation]:
    """Retrieve actionable decision recommendations for the authenticated farmer."""
    farmer = db.query(Farmer).filter(Farmer.user_id == current_user.id).first()
    district = farmer.district if farmer else "Purba Bardhaman"

    farmer_active_qty = Decimal(0)
    if farmer:
        from app.models.models import Farm, FarmerSupply
        from app.models.enums import SupplyStatus
        qty_val = (
            db.query(func.coalesce(func.sum(FarmerSupply.remaining_quantity_kg), Decimal(0)))
            .join(Farm, FarmerSupply.farm_id == Farm.id)
            .filter(
                Farm.farmer_id == farmer.id,
                FarmerSupply.commodity_id == commodity_id,
                FarmerSupply.status.in_([SupplyStatus.PLANNED, SupplyStatus.READY, SupplyStatus.PARTIALLY_SOLD]),
            )
            .scalar()
        )
        farmer_active_qty = Decimal(qty_val or Decimal(0))

    metrics = calculate_shared_supply_demand(
        db=db, commodity_id=commodity_id, district=district, window_days=window_days
    )
    risks = evaluate_farmer_risks(metrics, farmer_quantity_kg=farmer_active_qty)
    return generate_farmer_recommendations(metrics, risks, farmer_quantity_kg=farmer_active_qty)


# =====================================================================
# COLD STORE OPERATOR INTELLIGENCE ENDPOINTS
# =====================================================================
@router.get("/cold-store/dashboard", response_model=ColdStoreIntelligenceDashboard)
def cold_store_dashboard(
    commodity_id: int = Query(default=1),
    window_days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_cold_store_operator),
) -> ColdStoreIntelligenceDashboard:
    """Generate cold store operator decision-support dashboard based on capacity, release pressure, and demand."""
    operator = db.query(ColdStoreOperator).filter(ColdStoreOperator.user_id == current_user.id).first()
    district = operator.district if operator else "Purba Bardhaman"

    # Aggregated facility capacity & inventory for this operator
    stores = db.query(ColdStore).filter(ColdStore.operator_id == operator.id).all()
    store_ids = [s.id for s in stores]
    total_capacity = sum((s.capacity_kg for s in stores), Decimal(0))

    current_inventory = Decimal(0)
    if store_ids:
        current_inventory = (
            db.query(func.coalesce(func.sum(ColdStoreInventory.current_quantity_kg), Decimal(0)))
            .filter(
                ColdStoreInventory.cold_store_id.in_(store_ids),
                ColdStoreInventory.commodity_id == commodity_id,
            )
            .scalar()
            or Decimal(0)
        )

    util_pct = Decimal(0)
    if total_capacity > 0:
        util_pct = round((Decimal(current_inventory) / Decimal(total_capacity)) * 100, 2)

    # Estimate planned releases in window
    planned_releases = Decimal(current_inventory) * Decimal("0.05")

    metrics = calculate_shared_supply_demand(
        db=db,
        commodity_id=commodity_id,
        district=district,
        window_days=window_days,
    )

    risks = evaluate_cold_store_risks(
        capacity_kg=total_capacity,
        occupancy_kg=Decimal(current_inventory),
        utilization_pct=util_pct,
        planned_releases_kg=planned_releases,
        metrics=metrics,
    )
    recs = generate_cold_store_recommendations(risks, planned_releases, metrics)

    release_pressure = "LOW"
    if planned_releases > metrics.forecast_demand_kg:
        release_pressure = "HIGH"
    elif planned_releases > metrics.forecast_demand_kg * Decimal("0.75"):
        release_pressure = "MEDIUM"

    return ColdStoreIntelligenceDashboard(
        commodity_name=metrics.commodity_name,
        district=district,
        window_days=window_days,
        total_capacity_kg=total_capacity,
        current_inventory_kg=Decimal(current_inventory),
        capacity_utilization_pct=util_pct,
        planned_releases_kg=round(planned_releases, 2),
        visible_market_demand_kg=metrics.forecast_demand_kg,
        release_pressure=release_pressure,
        risks=risks,
        recommendations=recs,
    )


@router.get("/cold-store/risks", response_model=List[RiskAssessment])
def cold_store_risks(
    commodity_id: int = Query(default=1),
    window_days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_cold_store_operator),
) -> List[RiskAssessment]:
    """Retrieve detailed risk assessments for the authenticated cold-store operator."""
    dash = cold_store_dashboard(
        commodity_id=commodity_id, window_days=window_days, db=db, current_user=current_user
    )
    return dash.risks


@router.get("/cold-store/recommendations", response_model=List[ActionRecommendation])
def cold_store_recommendations(
    commodity_id: int = Query(default=1),
    window_days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_cold_store_operator),
) -> List[ActionRecommendation]:
    """Retrieve decision recommendations for the authenticated cold-store operator."""
    dash = cold_store_dashboard(
        commodity_id=commodity_id, window_days=window_days, db=db, current_user=current_user
    )
    return dash.recommendations


# =====================================================================
# FORECASTING ENDPOINT
# =====================================================================
@router.get("/forecast/price", response_model=ForecastResult)
def price_forecast(
    commodity_id: int = Query(default=1),
    district: str = Query(default="Purba Bardhaman"),
    db: Session = Depends(get_db),
) -> ForecastResult:
    """Statistical price forecast with confidence metric and metadata."""
    return forecast_price_trend(db=db, commodity_id=commodity_id, district=district)