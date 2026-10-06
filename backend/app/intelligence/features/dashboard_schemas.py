from decimal import Decimal
from typing import List, Dict, Any
from pydantic import BaseModel, ConfigDict


class RiskAssessment(BaseModel):
    risk_type: str
    severity: str  # "LOW" | "MEDIUM" | "HIGH"
    score: float  # Bounded [0.0, 1.0]
    message: str
    data_inputs: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class ActionRecommendation(BaseModel):
    action: str
    priority: str  # "LOW" | "MEDIUM" | "HIGH"
    reason: str
    supporting_data: Dict[str, Any]
    confidence: float  # Bounded [0.0, 1.0]

    model_config = ConfigDict(from_attributes=True)


class FarmerIntelligenceDashboard(BaseModel):
    commodity_name: str
    district: str
    window_days: int
    current_modal_price: Decimal
    price_trend: str
    expected_local_supply_kg: Decimal
    visible_demand_kg: Decimal
    supply_gap_kg: Decimal
    market_status: str  # "SURPLUS" | "SHORTAGE" | "BALANCED"
    risks: List[RiskAssessment]
    recommendations: List[ActionRecommendation]

    model_config = ConfigDict(from_attributes=True)


class ColdStoreIntelligenceDashboard(BaseModel):
    commodity_name: str
    district: str
    window_days: int
    total_capacity_kg: Decimal
    current_inventory_kg: Decimal
    capacity_utilization_pct: Decimal
    planned_releases_kg: Decimal
    visible_market_demand_kg: Decimal
    release_pressure: str  # "LOW" | "MEDIUM" | "HIGH"
    risks: List[RiskAssessment]
    recommendations: List[ActionRecommendation]

    model_config = ConfigDict(from_attributes=True)
