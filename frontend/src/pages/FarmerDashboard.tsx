import React, { useEffect, useState } from "react";
import { fetchFarmerDashboard, type FarmerDashboardData } from "../lib/api/intelligence";
import { fetchBuyerDemands, type BuyerDemandItem } from "../lib/api/market";
import { formatWeight, formatCurrency, formatPercent, getRiskBadgeClass, formatActionTitle } from "../lib/formatters";

export const FarmerDashboard: React.FC = () => {
  const [data, setData] = useState<FarmerDashboardData | null>(null);
  const [buyers, setBuyers] = useState<BuyerDemandItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        const dashResult = await fetchFarmerDashboard(1, "Purba Bardhaman", 7);
        setData(dashResult);
      } catch (err: any) {
        setError(err?.message || "Failed to load farmer intelligence");
      } finally {
        setLoading(false);
      }

      // Secondary request: load active buyer demands defensively
      try {
        const buyerResult = await fetchBuyerDemands(1);
        setBuyers(buyerResult || []);
      } catch (err) {
        console.warn("Non-fatal: could not load secondary buyer demand list:", err);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="loading-box">
        <div className="spinner"></div>
        <p>Loading Purba Bardhaman Potato Intelligence...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="card">
        <div className="alert-error">{error || "No data available."}</div>
        <button onClick={() => window.location.reload()} className="btn-secondary">
          Retry
        </button>
      </div>
    );
  }

  const {
    commodity_name,
    district,
    window_days,
    expected_local_supply_kg,
    visible_demand_kg,
    supply_gap_kg,
    market_status,
    current_modal_price,
    price_trend,
    farmer_active_supply_kg,
    farmer_supply_share_pct,
    farmer_exposure_level,
    risks,
    recommendations,
  } = data;

  const numSupply = Number(expected_local_supply_kg) || 0;
  const numDemand = Number(visible_demand_kg) || 0;
  const totalVolume = numSupply + numDemand;
  const supplyPercent = totalVolume > 0 ? ((numSupply / totalVolume) * 100).toFixed(0) : 50;
  const demandPercent = totalVolume > 0 ? ((numDemand / totalVolume) * 100).toFixed(0) : 50;

  const primaryRec = recommendations && recommendations.length > 0 ? recommendations[0] : null;
  const secondaryRecs = recommendations && recommendations.length > 1 ? recommendations.slice(1) : [];

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div style={{ marginBottom: "20px", display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--primary-700)", textTransform: "uppercase" }}>
            Farmer Intelligence Hub • Pilot
          </span>
          <h1 style={{ fontSize: "1.85rem", fontWeight: 800, color: "var(--slate-900)" }}>
            {district} • {commodity_name}
          </h1>
          <p style={{ fontSize: "0.88rem", color: "var(--slate-500)" }}>
            Aggregated mandi prices, harvest forecast, and buyer demand for the next {window_days} days.
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <span className={`badge-status ${market_status}`}>
            MARKET {market_status}
          </span>
          <span className={getRiskBadgeClass(farmer_exposure_level)}>
            YOUR EXPOSURE: {farmer_exposure_level}
          </span>
        </div>
      </div>

      {/* Top Metric Cards */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Local Mandi Price</div>
          <div className="metric-value-row">
            <span className="metric-value">
              {current_modal_price ? formatCurrency(Number(current_modal_price)) : "—"}
            </span>
            {price_trend && (
              <span className={`trend-badge ${price_trend}`}>
                {price_trend === "RISING" ? "▲ RISING" : price_trend === "FALLING" ? "▼ FALLING" : "━ STABLE"}
              </span>
            )}
          </div>
          <div className="metric-subtext">Purba Bardhaman modal price</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Expected Local Supply</div>
          <div className="metric-value-row">
            <span className="metric-value" style={{ color: "#b91c1c" }}>
              {formatWeight(numSupply)}
            </span>
          </div>
          <div className="metric-subtext">Harvests due in next {window_days} days</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Visible Buyer Demand</div>
          <div className="metric-value-row">
            <span className="metric-value" style={{ color: "#1d4ed8" }}>
              {formatWeight(numDemand)}
            </span>
          </div>
          <div className="metric-subtext">Active regional buyer contracts</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Your Active Harvest</div>
          <div className="metric-value-row">
            <span className="metric-value" style={{ color: "var(--primary-800)" }}>
              {formatWeight(Number(farmer_active_supply_kg))}
            </span>
            <span style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--slate-600)" }}>
              {formatPercent(Number(farmer_supply_share_pct))} share
            </span>
          </div>
          <div className="metric-subtext">Your personal volume exposed to market</div>
        </div>
      </div>

      {/* Primary Action Recommendation Banner */}
      {primaryRec && (
        <section className="action-banner">
          <div className="action-banner-badge">
            🎯 Primary Operational Recommendation • {primaryRec.priority} PRIORITY
          </div>
          <div className="action-banner-title">
            {formatActionTitle(primaryRec.action)}
          </div>
          <div className="action-banner-rationale">
            {primaryRec.reason}
          </div>
          <div className="action-banner-meta">
            <div className="action-meta-item">
              Algorithm Confidence: <strong>{formatPercent(primaryRec.confidence * 100)}</strong>
            </div>
            {supply_gap_kg && (
              <div className="action-meta-item">
                District Supply Gap: <strong>{formatWeight(Math.abs(Number(supply_gap_kg)))} {Number(supply_gap_kg) < 0 ? "Surplus" : "Deficit"}</strong>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Supply vs Demand Balance Bar */}
      <section className="balance-card">
        <div className="card-header">
          <div>
            <div className="card-title">Regional Supply vs Buyer Demand Absorption</div>
            <div className="card-subtitle">
              Comparison for {district} over the {window_days}-day planning horizon
            </div>
          </div>
        </div>

        <div className="balance-labels">
          <span style={{ color: "#b91c1c" }}>
            🌾 Expected Supply: {formatWeight(numSupply)} ({supplyPercent}%)
          </span>
          <span style={{ color: "#1d4ed8" }}>
            🛒 Buyer Demand: {formatWeight(numDemand)} ({demandPercent}%)
          </span>
        </div>

        <div className="balance-track">
          <div
            className="balance-segment-supply"
            style={{ width: `${supplyPercent}%` }}
            title={`Supply: ${formatWeight(numSupply)}`}
          />
          <div
            className="balance-segment-demand"
            style={{ width: `${demandPercent}%` }}
            title={`Demand: ${formatWeight(numDemand)}`}
          />
        </div>
      </section>

      {/* Risk Assessments */}
      <div style={{ marginBottom: "24px" }}>
        <h2 style={{ fontSize: "1.2rem", fontWeight: 700, marginBottom: "12px", color: "var(--slate-900)" }}>
          Personal & Market Risk Analysis
        </h2>
        <div className="risks-grid">
          {(risks || []).map((r, idx) => (
            <div key={idx} className="risk-item-card">
              <div className="risk-item-header">
                <span className="risk-item-name">{formatActionTitle(r.risk_type)}</span>
                <span className={getRiskBadgeClass(r.severity)}>{r.severity}</span>
              </div>
              <p style={{ fontSize: "0.85rem", color: "var(--slate-600)", minHeight: "48px" }}>
                {r.message}
              </p>
              <div className="risk-score-bar-bg">
                <div
                  className={`risk-score-bar-fill ${r.severity}`}
                  style={{ width: `${Math.min(r.score * 100, 100)}%` }}
                />
              </div>
              <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--slate-500)" }}>
                Calculated Risk Score: {(r.score * 100).toFixed(0)}/100
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Secondary Recommendations & Buyer Connections */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "20px" }}>
        {/* Additional Recommended Actions */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Alternative Tactical Options</div>
              <div className="card-subtitle">Secondary strategies for harvest distribution</div>
            </div>
          </div>
          {secondaryRecs.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {secondaryRecs.map((rec, idx) => (
                <div key={idx} style={{ padding: "12px 14px", background: "var(--slate-50)", borderRadius: "var(--radius-sm)", border: "1px solid var(--slate-200)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <strong>{formatActionTitle(rec.action)}</strong>
                    <span className={getRiskBadgeClass(rec.priority)}>{rec.priority}</span>
                  </div>
                  <p style={{ fontSize: "0.85rem", color: "var(--slate-600)" }}>{rec.reason}</p>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: "var(--slate-500)", fontSize: "0.88rem" }}>
              Primary recommendation covers the entire optimal course of action.
            </p>
          )}
        </div>

        {/* Active Buyers */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Verified Buyer Procurement Orders</div>
              <div className="card-subtitle">Buyers currently seeking potato in the region</div>
            </div>
          </div>
          {buyers.length > 0 ? (
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Buyer</th>
                    <th>District</th>
                    <th>Volume Needed</th>
                    <th>Max Price</th>
                  </tr>
                </thead>
                <tbody>
                  {buyers.slice(0, 5).map((b) => {
                    const districtName = b.buyer_district || "District Not Specified";
                    const isLocal = districtName.toLowerCase().includes("bardhaman");
                    return (
                      <tr key={b.id}>
                        <td style={{ fontWeight: 600 }}>{b.buyer_name}</td>
                        <td>
                          <span className={isLocal ? "badge-risk-low" : "badge-neutral"}>
                            {districtName}
                          </span>
                        </td>
                        <td>{formatWeight(b.quantity_kg)}</td>
                        <td style={{ fontWeight: 700, color: "var(--primary-700)" }}>
                          {b.max_price_per_kg ? formatCurrency(b.max_price_per_kg) : "Negotiable"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p style={{ color: "var(--slate-500)", fontSize: "0.88rem" }}>
              No active buyers registered in this window.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
