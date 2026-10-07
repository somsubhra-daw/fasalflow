import { apiClient } from "./client";

export interface MarketItem {
  id: number;
  name: string;
  district: string;
  block?: string | null;
  active: boolean;
}

export interface MarketPriceItem {
  id: number;
  market_id: number;
  market_name: string;
  commodity_id: number;
  commodity_name: string;
  date: string;
  min_price_per_kg: number;
  modal_price_per_kg: number;
  max_price_per_kg: number;
  source: string;
}

export interface MarketArrivalItem {
  id: number;
  market_id: number;
  commodity_id: number;
  date: string;
  quantity_kg: number;
  source: string;
}

export interface BuyerItem {
  id: number;
  name: string;
  buyer_type: string;
  district: string;
  phone?: string | null;
  is_verified: boolean;
}

export interface BuyerDemandItem {
  id: number;
  buyer_id: number;
  buyer_name: string;
  buyer_district?: string | null;
  commodity_id: number;
  commodity_name: string;
  quantity_kg: number;
  required_from: string;
  required_until: string;
  max_price_per_kg?: number | null;
  quality_grade?: string | null;
  status: string;
}

export async function fetchMarkets(district?: string): Promise<MarketItem[]> {
  const query = district ? `?district=${encodeURIComponent(district)}` : "";
  return apiClient<MarketItem[]>(`/markets${query}`);
}

export async function fetchMarketPrices(
  marketId: number,
  commodityId: number = 1
): Promise<MarketPriceItem[]> {
  return apiClient<MarketPriceItem[]>(`/markets/${marketId}/prices?commodity_id=${commodityId}`);
}

export async function fetchMarketArrivals(
  marketId: number,
  commodityId: number = 1
): Promise<MarketArrivalItem[]> {
  return apiClient<MarketArrivalItem[]>(`/markets/${marketId}/arrivals?commodity_id=${commodityId}`);
}

export async function fetchBuyers(district?: string): Promise<BuyerItem[]> {
  const query = district ? `?district=${encodeURIComponent(district)}` : "";
  return apiClient<BuyerItem[]>(`/buyers${query}`);
}

export interface ColdStoreItem {
  id: number;
  name: string;
  district: string;
  block?: string | null;
  capacity_kg: number | string;
  current_occupancy_kg: number | string;
  utilization_percentage: number | string;
  active: boolean;
}

export async function fetchOperatorStores(): Promise<ColdStoreItem[]> {
  return apiClient<ColdStoreItem[]>("/cold-store/stores");
}

export async function fetchBuyerDemands(
  commodityId: number = 1,
  dateWindow?: string
): Promise<BuyerDemandItem[]> {
  const params = new URLSearchParams({ commodity_id: String(commodityId) });
  if (dateWindow) params.append("date_window", dateWindow);
  return apiClient<BuyerDemandItem[]>(`/buyers/demand?${params.toString()}`);
}
