from decimal import Decimal
from typing import List
from app.intelligence.features.metrics import MarketSupplyDemandMetrics
from app.intelligence.features.dashboard_schemas import RiskAssessment, ActionRecommendation


def evaluate_farmer_risks(
    metrics: MarketSupplyDemandMetrics,
    farmer_quantity_kg: Decimal = Decimal(0),
) -> List[RiskAssessment]:
    """Evaluate farmer-specific risks based on shared regional metrics and personal volume exposure."""
    risks: List[RiskAssessment] = []

    # 1. Surplus Risk & Personal Exposure
    if metrics.effective_supply_kg > metrics.forecast_demand_kg:
        ratio = (
            float(metrics.effective_supply_kg / metrics.forecast_demand_kg)
            if metrics.forecast_demand_kg > 0
            else 2.0
        )
        if ratio >= 1.5 or farmer_quantity_kg >= Decimal(30000):
            severity = "HIGH"
            score = min(0.95, 0.70 + (ratio - 1.5) * 0.1)
        elif ratio >= 1.15 or farmer_quantity_kg >= Decimal(10000):
            severity = "MEDIUM"
            score = 0.65
        else:
            severity = "LOW"
            score = 0.35

        risks.append(
            RiskAssessment(
                risk_type="SURPLUS_RISK",
                severity=severity,
                score=round(score, 2),
                message=(
                    f"Regional supply exceeds visible demand by {metrics.effective_supply_kg - metrics.forecast_demand_kg:,.0f} kg. "
                    f"Your active volume is {farmer_quantity_kg:,.0f} kg."
                ),
                data_inputs={
                    "effective_supply_kg": float(metrics.effective_supply_kg),
                    "forecast_demand_kg": float(metrics.forecast_demand_kg),
                    "farmer_active_volume_kg": float(farmer_quantity_kg),
                    "ratio": round(ratio, 2),
                },
            )
        )

    # 2. Price Pressure Risk
    if metrics.price_trend == "DOWNWARD" or metrics.status == "SURPLUS":
        # Severity increases if farmer has large unsold volume exposed to price drops
        is_high_exposure = farmer_quantity_kg >= Decimal(20000)
        risks.append(
            RiskAssessment(
                risk_type="PRICE_PRESSURE_RISK",
                severity="HIGH" if is_high_exposure or (metrics.price_trend == "DOWNWARD" and metrics.status == "SURPLUS") else "MEDIUM",
                score=0.85 if is_high_exposure else 0.65,
                message="Incoming harvest supply is exerting downward pressure on mandi modal prices.",
                data_inputs={
                    "price_trend": metrics.price_trend,
                    "current_modal_price": float(metrics.current_modal_price or Decimal(0)),
                    "farmer_exposed_volume_kg": float(farmer_quantity_kg),
                },
            )
        )

    # 3. Harvest Timing / Unsold Produce Risk
    if farmer_quantity_kg > Decimal(25000) and metrics.status == "SURPLUS":
        risks.append(
            RiskAssessment(
                risk_type="UNSOLD_PRODUCE_RISK",
                severity="HIGH",
                score=0.88,
                message=f"High personal exposure ({farmer_quantity_kg:,.0f} kg) during regional harvest surplus. Strong risk of unsold lots at local mandis.",
                data_inputs={
                    "farmer_active_supply_kg": float(farmer_quantity_kg),
                    "regional_effective_supply_kg": float(metrics.effective_supply_kg),
                },
            )
        )

    # 4. Data sufficiency check
    if metrics.current_modal_price is None:
        risks.append(
            RiskAssessment(
                risk_type="INSUFFICIENT_DATA",
                severity="MEDIUM",
                score=0.50,
                message=f"No recent market price observations recorded for {metrics.commodity_name} in {metrics.district}. Price trend certainty is low.",
                data_inputs={"district": metrics.district, "commodity_id": metrics.commodity_id},
            )
        )

    return risks


def generate_farmer_recommendations(
    metrics: MarketSupplyDemandMetrics,
    risks: List[RiskAssessment],
    farmer_quantity_kg: Decimal = Decimal(0),
) -> List[ActionRecommendation]:
    """Generate transparent, decision-support recommendations tailored to individual farmer exposure."""
    recs: List[ActionRecommendation] = []

    # 1. Safeguard against missing market price or demand data: NEVER recommend SELL_NOW on empty evidence
    if (
        metrics.current_modal_price is None
        or metrics.current_modal_price <= Decimal(0)
        or metrics.forecast_demand_kg <= Decimal(0)
    ):
        recs.append(
            ActionRecommendation(
                action="INSUFFICIENT_DATA",
                priority="HIGH",
                reason="Insufficient market price or visible demand observations found for this commodity in your district. Avoid executing immediate sales without verified price discovery.",
                supporting_data={
                    "district": metrics.district,
                    "commodity_name": metrics.commodity_name,
                    "visible_demand_kg": float(metrics.forecast_demand_kg),
                    "current_modal_price": float(metrics.current_modal_price) if metrics.current_modal_price else None,
                },
                confidence=0.40,
            )
        )
        recs.append(
            ActionRecommendation(
                action="MONITOR_PRICE",
                priority="MEDIUM",
                reason="Monitor local mandi arrivals and wait for clear price and demand discovery before dispatching produce.",
                supporting_data={"district": metrics.district},
                confidence=0.50,
            )
        )
        return recs

    # 2. If regional supply is in surplus
    if metrics.status == "SURPLUS":
        recs.append(
            ActionRecommendation(
                action="PRE_BOOK_BUYER",
                priority="HIGH",
                reason="Visible demand is lower than expected regional supply. Secure purchase commitments early to lock in pricing.",
                supporting_data={"supply_gap_kg": float(metrics.supply_gap_kg)},
                confidence=0.85,
            )
        )
        recs.append(
            ActionRecommendation(
                action="CONSIDER_STORAGE",
                priority="MEDIUM",
                reason="Local mandi prices are vulnerable to harvest glut. Evaluate regional cold storage facilities to defer selling until price recovery.",
                supporting_data={"storage_release_kg": float(metrics.expected_storage_release_kg)},
                confidence=0.80,
            )
        )
        recs.append(
            ActionRecommendation(
                action="CHECK_ALTERNATE_MARKET",
                priority="MEDIUM",
                reason="Check wholesale arrivals in adjacent markets or food processors outside your primary district.",
                supporting_data={"district": metrics.district},
                confidence=0.75,
            )
        )
    else:
        # Deficit or Balanced with verified price observations
        recs.append(
            ActionRecommendation(
                action="SELL_NOW",
                priority="HIGH",
                reason="Market shows strong demand absorption with verified price discovery. Immediate mandi dispatch recommended.",
                supporting_data={"current_modal_price": float(metrics.current_modal_price)},
                confidence=0.88,
            )
        )
        recs.append(
            ActionRecommendation(
                action="MONITOR_PRICE",
                priority="LOW",
                reason="Favorable price realization window open. Monitor daily mandi arrivals closely.",
                supporting_data={"price_trend": metrics.price_trend},
                confidence=0.90,
            )
        )

    return recs
