from decimal import Decimal
from typing import List
from app.intelligence.features.metrics import MarketSupplyDemandMetrics
from app.intelligence.features.dashboard_schemas import RiskAssessment, ActionRecommendation


def evaluate_cold_store_risks(
    capacity_kg: Decimal,
    occupancy_kg: Decimal,
    utilization_pct: Decimal,
    planned_releases_kg: Decimal,
    metrics: MarketSupplyDemandMetrics,
) -> List[RiskAssessment]:
    """Evaluate cold storage operator risks (capacity, release pressure, demand weakness)."""
    risks: List[RiskAssessment] = []

    # 1. Capacity Risk
    if utilization_pct >= Decimal("90.0"):
        risks.append(
            RiskAssessment(
                risk_type="CAPACITY_RISK",
                severity="HIGH",
                score=0.92,
                message=f"Cold storage capacity utilization is critically high at {utilization_pct:.1f}%. Risk of rejecting inbound incoming crop.",
                data_inputs={
                    "capacity_kg": float(capacity_kg),
                    "occupancy_kg": float(occupancy_kg),
                    "utilization_pct": float(utilization_pct),
                },
            )
        )
    elif utilization_pct >= Decimal("75.0"):
        risks.append(
            RiskAssessment(
                risk_type="CAPACITY_RISK",
                severity="MEDIUM",
                score=0.70,
                message=f"Storage utilization is at {utilization_pct:.1f}%. Manage chamber allocation carefully.",
                data_inputs={"utilization_pct": float(utilization_pct)},
            )
        )

    # 2. Release Pressure Risk: planned release exceeds visible demand
    if planned_releases_kg > metrics.forecast_demand_kg:
        risks.append(
            RiskAssessment(
                risk_type="RELEASE_PRESSURE_RISK",
                severity="HIGH",
                score=0.88,
                message="Planned stock release exceeds visible market demand in this market window. Rapid release could depress prices.",
                data_inputs={
                    "planned_releases_kg": float(planned_releases_kg),
                    "forecast_demand_kg": float(metrics.forecast_demand_kg),
                },
            )
        )

    # 3. Demand Weakness Risk
    if metrics.status == "SURPLUS" and utilization_pct > Decimal("60.0"):
        risks.append(
            RiskAssessment(
                risk_type="DEMAND_WEAKNESS_RISK",
                severity="MEDIUM",
                score=0.68,
                message="Regional demand is weak relative to aggregate supply. Offloading stored inventory may face slower turnaround.",
                data_inputs={
                    "market_status": metrics.status,
                    "supply_gap_kg": float(metrics.supply_gap_kg),
                },
            )
        )

    return risks


def generate_cold_store_recommendations(
    risks: List[RiskAssessment],
    planned_releases_kg: Decimal,
    metrics: MarketSupplyDemandMetrics,
) -> List[ActionRecommendation]:
    """Generate recommendations tailored for cold storage operators."""
    recs: List[ActionRecommendation] = []

    has_release_pressure = any(r.risk_type == "RELEASE_PRESSURE_RISK" for r in risks)
    has_capacity_risk = any(r.risk_type == "CAPACITY_RISK" and r.severity == "HIGH" for r in risks)

    if has_release_pressure:
        recs.append(
            ActionRecommendation(
                action="STAGGER_RELEASE",
                priority="HIGH",
                reason="Planned release exceeds immediate market demand. Stagger dispatches across 2-3 weeks to protect realization.",
                supporting_data={"planned_releases_kg": float(planned_releases_kg)},
                confidence=0.86,
            )
        )
        recs.append(
            ActionRecommendation(
                action="IDENTIFY_BUYERS",
                priority="HIGH",
                reason="Identify institutional buyers and food processors before offloading additional floor stock.",
                supporting_data={"forecast_demand_kg": float(metrics.forecast_demand_kg)},
                confidence=0.82,
            )
        )

    if has_capacity_risk:
        recs.append(
            ActionRecommendation(
                action="REVIEW_INVENTORY",
                priority="HIGH",
                reason="Facility near capacity threshold. Prioritize expediting older lots to free up floor space.",
                supporting_data={},
                confidence=0.90,
            )
        )

    if not recs:
        recs.append(
            ActionRecommendation(
                action="MONITOR_MARKET_PRICE",
                priority="LOW",
                reason="Storage utilization and market release balance are currently within healthy operating margins.",
                supporting_data={"modal_price": float(metrics.current_modal_price or Decimal(0))},
                confidence=0.85,
            )
        )

    return recs
