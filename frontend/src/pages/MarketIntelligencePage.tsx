import React, { useEffect, useState } from "react";
import {
  fetchMarkets,
  fetchMarketPrices,
  fetchMarketArrivals,
  fetchBuyerDemands,
  type MarketItem,
  type MarketPriceItem,
  type MarketArrivalItem,
  type BuyerDemandItem,
} from "../lib/api/market";
import { fetchPriceForecast, type PriceForecastData } from "../lib/api/intelligence";
import { formatWeight, formatCurrency, formatPercent } from "../lib/formatters";

export const MarketIntelligencePage: React.FC = () => {
  const [markets, setMarkets] = useState<MarketItem[]>([]);
  const [selectedMarketId, setSelectedMarketId] = useState<number | null>(null);
  const [prices, setPrices] = useState<MarketPriceItem[]>([]);
  const [arrivals, setArrivals] = useState<MarketArrivalItem[]>([]);
  const [forecast, setForecast] = useState<PriceForecastData | null>(null);
  const [demands, setDemands] = useState<BuyerDemandItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function init() {
      try {
        setLoading(true);
        setError(null);
        // 1. Fetch Purba Bardhaman Mandis
        const marketList = await fetchMarkets("Purba Bardhaman");
        setMarkets(marketList || []);
        if (marketList && marketList.length > 0) {
          setSelectedMarketId(marketList[0].id);
        }
      } catch (err: any) {
        setError(err?.message || "Failed to load market intelligence data");
      } finally {
        setLoading(false);
      }

      // 2. Fetch Price Forecast independently
      try {
        const forecastData = await fetchPriceForecast(1, "Purba Bardhaman", 7);
        setForecast(forecastData);
      } catch (err) {
        console.warn("Non-fatal: could not load price forecast:", err);
      }

      // 3. Fetch Buyer Demands independently
      try {
        const demandList = await fetchBuyerDemands(1);
        setDemands(demandList || []);
      } catch (err) {
        console.warn("Non-fatal: could not load buyer demands:", err);
      }
    }
    init();
  }, []);

  // When selected market changes, load its prices and arrivals
  useEffect(() => {
    if (!selectedMarketId) return;

    async function loadMarketDetails() {
      try {
        const [pricesData, arrivalsData] = await Promise.all([
          fetchMarketPrices(selectedMarketId!, 1),
          fetchMarketArrivals(selectedMarketId!, 1),
        ]);
        setPrices(pricesData);
        setArrivals(arrivalsData);
      } catch (err: any) {
        console.error("Failed to load mandi details:", err);
      }
    }
    loadMarketDetails();
  }, [selectedMarketId]);

  if (loading) {
    return (
      <div className="loading-box">
        <div className="spinner"></div>
        <p>Fetching Purba Bardhaman Mandi & Demand Data...</p>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <div style={{ marginBottom: "24px" }}>
        <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--primary-700)", textTransform: "uppercase" }}>
          Mandi & Buyer Intelligence
        </span>
        <h1 style={{ fontSize: "1.85rem", fontWeight: 800, color: "var(--slate-900)" }}>
          Purba Bardhaman • Potato Market Analytics
        </h1>
        <p style={{ fontSize: "0.88rem", color: "var(--slate-500)" }}>
          Live mandi prices, daily harvest arrivals, statistical price forecasts, and verified procurement contracts.
        </p>
      </div>

      {error && <div className="alert-error">{error}</div>}

      {/* Statistical Price Forecast Card */}
      {forecast && (
        <section className="card" style={{ marginBottom: "24px", borderLeft: "4px solid var(--primary-600)" }}>
          <div className="card-header">
            <div>
              <div className="card-title">7-Day Statistical Price Forecast • {forecast.commodity_name}</div>
              <div className="card-subtitle">
                Volume-weighted moving average model calculated for Purba Bardhaman
              </div>
            </div>
            <span className="trend-badge RISING">
              Confidence: {formatPercent(forecast.confidence * 100)}
            </span>
          </div>

          <div className="metrics-grid" style={{ marginBottom: "16px" }}>
            <div className="metric-card" style={{ background: "var(--slate-50)" }}>
              <div className="metric-label">Target Metric</div>
              <div className="metric-value" style={{ fontSize: "1.4rem" }}>
                {forecast.target_metric.replace(/_/g, " ")}
              </div>
              <div className="metric-subtext">Mandi benchmark metric</div>
            </div>

            <div className="metric-card" style={{ background: "var(--slate-50)" }}>
              <div className="metric-label">Forecasted Modal Price</div>
              <div className="metric-value" style={{ color: "var(--primary-700)" }}>
                {formatCurrency(Number(forecast.forecast_value))}
              </div>
              <div className="metric-subtext">Estimated price horizon ({forecast.period})</div>
            </div>

            <div className="metric-card" style={{ background: "var(--slate-50)" }}>
              <div className="metric-label">Model Confidence</div>
              <div className="metric-value" style={{ fontSize: "1.4rem" }}>
                {formatPercent(forecast.confidence * 100)}
              </div>
              <div className="metric-subtext">Statistical reliability rating</div>
            </div>

            <div className="metric-card" style={{ background: "var(--slate-50)" }}>
              <div className="metric-label">Data Points Used</div>
              <div className="metric-value" style={{ fontSize: "1.4rem" }}>
                {forecast.data_points_used} records
              </div>
              <div className="metric-subtext">Historical mandi observations</div>
            </div>
          </div>

          <div style={{ fontSize: "0.82rem", color: "var(--slate-600)", background: "#f8fafc", padding: "10px 14px", borderRadius: "var(--radius-sm)", display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
            <div>
              <strong>Methodology:</strong> {forecast.method.replace(/_/g, " ")}
            </div>
            <div>
              <strong>Generated:</strong> {forecast.generated_at_date}
            </div>
          </div>
        </section>
      )}

      {/* Market Selector & Live Data */}
      <div className="card" style={{ marginBottom: "24px" }}>
        <div className="card-header">
          <div>
            <div className="card-title">Regulated Mandis in Purba Bardhaman</div>
            <div className="card-subtitle">Select a mandi to view recent quotes and recorded arrivals</div>
          </div>
        </div>

        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginBottom: "20px" }}>
          {markets.map((m) => (
            <button
              key={m.id}
              onClick={() => setSelectedMarketId(m.id)}
              className={selectedMarketId === m.id ? "btn-primary" : "btn-secondary"}
              style={{ fontSize: "0.9rem", padding: "8px 16px" }}
            >
              🏛️ {m.name} {m.block ? `(${m.block})` : ""}
            </button>
          ))}
        </div>

        {/* Prices and Arrivals for Selected Market */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "20px" }}>
          <div>
            <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "10px", color: "var(--slate-800)" }}>
              Recorded Prices (₹/kg)
            </h3>
            {prices.length > 0 ? (
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Min</th>
                      <th>Modal (Key)</th>
                      <th>Max</th>
                      <th>Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {prices.map((p) => (
                      <tr key={p.id}>
                        <td>{p.date}</td>
                        <td>{formatCurrency(p.min_price_per_kg)}</td>
                        <td style={{ fontWeight: 800, color: "var(--primary-800)" }}>
                          {formatCurrency(p.modal_price_per_kg)}
                        </td>
                        <td>{formatCurrency(p.max_price_per_kg)}</td>
                        <td><span className="badge-neutral">{p.source}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p style={{ color: "var(--slate-500)", fontSize: "0.85rem" }}>No price records found for this market.</p>
            )}
          </div>

          <div>
            <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: "10px", color: "var(--slate-800)" }}>
              Daily Arrivals
            </h3>
            {arrivals.length > 0 ? (
              <div className="table-responsive">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Arrival Volume</th>
                      <th>Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {arrivals.map((a) => (
                      <tr key={a.id}>
                        <td>{a.date}</td>
                        <td style={{ fontWeight: 700 }}>{formatWeight(a.quantity_kg)}</td>
                        <td><span className="badge-neutral">{a.source}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p style={{ color: "var(--slate-500)", fontSize: "0.85rem" }}>No arrival logs recorded for this market.</p>
            )}
          </div>
        </div>
      </div>

      {/* Active Buyer Demand Ledger */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">Active Buyer Demand Contracts (District & Regional)</div>
            <div className="card-subtitle">
              Verified procurement orders registered in the FasalFlow buyer network
            </div>
          </div>
        </div>

        {demands.length > 0 ? (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Buyer Name</th>
                  <th>Buyer District</th>
                  <th>Quantity Needed</th>
                  <th>Grade</th>
                  <th>Price Ceiling</th>
                  <th>Validity Period</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {demands.map((d) => {
                  const districtName = d.buyer_district || "District Not Specified";
                  const isLocal = districtName.toLowerCase().includes("bardhaman");
                  return (
                    <tr key={d.id}>
                      <td style={{ fontWeight: 700 }}>{d.buyer_name}</td>
                      <td>
                        <span className={isLocal ? "badge-risk-low" : "badge-neutral"}>
                          {districtName}
                        </span>
                      </td>
                      <td style={{ fontWeight: 600 }}>{formatWeight(d.quantity_kg)}</td>
                      <td>{d.quality_grade || "All Grades"}</td>
                      <td style={{ color: "var(--primary-700)", fontWeight: 700 }}>
                        {d.max_price_per_kg ? formatCurrency(d.max_price_per_kg) : "Negotiable"}
                      </td>
                      <td style={{ fontSize: "0.82rem", color: "var(--slate-600)" }}>
                        {d.required_from} to {d.required_until}
                      </td>
                      <td>
                        <span className="badge-neutral">{d.status}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p style={{ color: "var(--slate-500)", fontSize: "0.88rem" }}>No active buyer procurement orders.</p>
        )}
      </div>
    </div>
  );
};
