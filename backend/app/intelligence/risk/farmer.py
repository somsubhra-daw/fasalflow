from decimal import Decimal
from typing import List
from app.intelligence.features.metrics import MarketSupplyDemandMetrics
from app.intelligence.features.dashboard_schemas import RiskAssessment, ActionRecommendation


def evaluate_farmer_risks(metrics: MarketSupplyDemandMetrics) -> List[RiskAssessment]:
    """Evaluate farmer-specific risks based on shared market supply-demand metrics."""
    risks: List[RiskAssessment] = []

    # 1. Surplus Risk
    if metrics.effective_supply_kg > metrics.forecast_demand_kg:
        ratio = (
            float(metrics.effective_supply_kg / metrics.forecast_demand_kg)
            if metrics.forecast_demand_kg > 0
            else 2.0
        )
        if ratio >= 1.5:
            severity = "HIGH"
            score = min(0.95, 0.70 + (ratio - 1.5) * 0.1)
        elif ratio >= 1.15:
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
                message=f"Regional expected supply exceeds visible demand by {metrics.effective_supply_kg - metrics.forecast_demand_kg:,.0f} kg.",
                data_inputs={
                    "effective_supply_kg": float(metrics.effective_supply_kg),
                    "forecast_demand_kg": float(metrics.forecast_demand_kg),
                    "ratio": round(ratio, 2),
                },
            )
        )

    # 2. Price Pressure Risk
    if metrics.price_trend == "DOWNWARD" or metrics.status == "SURPLUS":
        risks.append(
            RiskAssessment(
                risk_type="PRICE_PRESSURE_RISK",
                severity="HIGH" if metrics.price_trend == "DOWNWARD" and metrics.status == "SURPLUS" else "MEDIUM",
                score=0.80 if metrics.price_trend == "DOWNWARD" else 0.60,
                message="Incoming harvest supply is exerting downward pressure on mandi modal prices.",
                data_inputs={
                    "price_trend": metrics.price_trend,
                    "current_modal_price": float(metrics.current_modal_price or Decimal(0)),
                },
            )
        )

    # 3. Harvest Timing / Unsold Produce Risk
    if metrics.expected_fresh_supply_kg > Decimal(50000) and metrics.forecast_demand_kg < Decimal(30000):
        risks.append(
            RiskAssessment(
                risk_type="UNSOLD_PRODUCE_RISK",
                severity="HIGH",
                score=0.85,
                message="Harvest volume sharply exceeds immediate mandi absorption capacity without pre-arranged buyers.",
                data_inputs={
                    "expected_fresh_supply_kg": float(metrics.expected_fresh_supply_kg),
                    "forecast_demand_kg": float(metrics.forecast_demand_kg),
                },
            )
        )

    return risks


def generate_farmer_recommendations(
    metrics: MarketSupplyDemandMetrics,
    risks: List[RiskAssessment],
) -> List[ActionRecommendation]:
    """Generate transparent, decision-support recommendations tailored to farmers."""
    recs: List[ActionRecommendation] = []

    # If surplus or price pressure
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
        # Deficit or Balanced
        recs.append(
            ActionRecommendation(
                action="SELL_NOW",
                priority="HIGH",
                reason="Market shows strong demand absorption with stable/upward price trends. Immediate mandi dispatch recommended.",
                supporting_data={"current_modal_price": float(metrics.current_modal_price or Decimal(0))},
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
