import { apiClient } from "./client";

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

export interface RiskAssessment {
  risk_type: string;
  severity: RiskLevel;
  score: number;
  message: string;
  data_inputs: Record<string, any>;
}

export interface ActionRecommendation {
  action: string;
  priority: RiskLevel;
  reason: string;
  supporting_data: Record<string, any>;
  confidence: number;
}

export interface FarmerDashboardData {
  commodity_name: string;
  district: string;
  window_days: number;
  current_modal_price: number | string | null;
  price_trend: string | null;
  expected_local_supply_kg: number | string;
  visible_demand_kg: number | string;
  supply_gap_kg: number | string;
  market_status: string;
  farmer_active_supply_kg: number | string;
  farmer_supply_share_pct: number | string;
  farmer_exposure_level: string;
  risks: RiskAssessment[];
  recommendations: ActionRecommendation[];
}

export interface ColdStoreDashboardData {
  commodity_name: string;
  district: string;
  window_days: number;
  total_capacity_kg: number | string;
  current_inventory_kg: number | string;
  capacity_utilization_pct: number | string;
  planned_releases_kg: number | string;
  visible_market_demand_kg: number | string;
  release_pressure: string;
  risks: RiskAssessment[];
  recommendations: ActionRecommendation[];
}

export interface PriceForecastData {
  commodity_id: number;
  commodity_code: string;
  commodity_name: string;
  target_metric: string;
  forecast_value: number | string;
  period: string;
  method: string;
  confidence: number;
  data_points_used: number;
  generated_at_date: string;
}

export async function fetchFarmerDashboard(
  commodityId: number = 1,
  district: string = "Purba Bardhaman",
  daysAhead: number = 7
): Promise<FarmerDashboardData> {
  const query = new URLSearchParams({
    commodity_id: String(commodityId),
    district,
    window_days: String(daysAhead),
  });
  return apiClient<FarmerDashboardData>(`/intelligence/farmer/dashboard?${query.toString()}`);
}

export async function fetchColdStoreDashboard(
  commodityId: number = 1,
  district: string = "Purba Bardhaman",
  daysAhead: number = 7
): Promise<ColdStoreDashboardData> {
  const query = new URLSearchParams({
    commodity_id: String(commodityId),
    district,
    window_days: String(daysAhead),
  });
  return apiClient<ColdStoreDashboardData>(`/intelligence/cold-store/dashboard?${query.toString()}`);
}

export async function fetchPriceForecast(
  commodityId: number = 1,
  district: string = "Purba Bardhaman",
  daysAhead: number = 7
): Promise<PriceForecastData> {
  const query = new URLSearchParams({
    commodity_id: String(commodityId),
    district,
    window_days: String(daysAhead),
  });
  return apiClient<PriceForecastData>(`/intelligence/forecast/price?${query.toString()}`);
}
