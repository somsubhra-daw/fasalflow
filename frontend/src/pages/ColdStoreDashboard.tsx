import React, { useEffect, useState } from "react";
import { fetchColdStoreDashboard, type ColdStoreDashboardData } from "../lib/api/intelligence";
import { fetchOperatorStores, type ColdStoreItem } from "../lib/api/market";
import { formatWeight, formatPercent, getRiskBadgeClass, formatActionTitle } from "../lib/formatters";

export const ColdStoreDashboard: React.FC = () => {
  const [data, setData] = useState<ColdStoreDashboardData | null>(null);
  const [stores, setStores] = useState<ColdStoreItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        const [dashResult, storesResult] = await Promise.all([
          fetchColdStoreDashboard(1, "Purba Bardhaman", 7),
          fetchOperatorStores(),
        ]);
        setData(dashResult);
        setStores(storesResult);
      } catch (err: any) {
        setError(err?.message || "Failed to load cold storage intelligence");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="loading-box">
        <div className="spinner"></div>
        <p>Loading Cold Storage Operations & Release Intelligence...</p>
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
    total_capacity_kg,
    current_inventory_kg,
    capacity_utilization_pct,
    planned_releases_kg,
    visible_market_demand_kg,
    release_pressure,
    risks,
    recommendations,
  } = data;

  const numTotalCapacity = Number(total_capacity_kg) || 0;
  const numCurrentInventory = Number(current_inventory_kg) || 0;
  const numUtilization = Number(capacity_utilization_pct) || 0;
  const numPlannedReleases = Number(planned_releases_kg) || 0;
  const numDemand = Number(visible_market_demand_kg) || 0;

  const primaryRec = recommendations && recommendations.length > 0 ? recommendations[0] : null;
  const secondaryRecs = recommendations && recommendations.length > 1 ? recommendations.slice(1) : [];

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div style={{ marginBottom: "20px", display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--primary-700)", textTransform: "uppercase" }}>
            Cold Storage Intelligence Hub • Pilot
          </span>
          <h1 style={{ fontSize: "1.85rem", fontWeight: 800, color: "var(--slate-900)" }}>
            {district} • Managed Facilities
          </h1>
          <p style={{ fontSize: "0.88rem", color: "var(--slate-500)" }}>
            Inventory utilization, release timing, and warehouse risk analysis for {commodity_name}.
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <span className="badge-neutral" style={{ fontWeight: 700 }}>
            {stores.length} MANAGED FACILITIES
          </span>
          <span className={getRiskBadgeClass(release_pressure)}>
            RELEASE PRESSURE: {release_pressure}
          </span>
        </div>
      </div>

      {/* Top Metric Cards */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Total Managed Capacity</div>
          <div className="metric-value-row">
            <span className="metric-value">
              {formatWeight(numTotalCapacity)}
            </span>
          </div>
          <div className="metric-subtext">Across {stores.length} storage facilities</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Current Occupancy</div>
          <div className="metric-value-row">
            <span className="metric-value">
              {formatWeight(numCurrentInventory)}
            </span>
            <span style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--primary-700)" }}>
              {formatPercent(numUtilization)}
            </span>
          </div>
          <div className="metric-subtext">Overall capacity utilization</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Projected 7-Day Releases</div>
          <div className="metric-value-row">
            <span className="metric-value" style={{ color: "#d97706" }}>
              {formatWeight(numPlannedReleases)}
            </span>
          </div>
          <div className="metric-subtext">Scheduled stock dispatches</div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Visible Buyer Demand</div>
          <div className="metric-value-row">
            <span className="metric-value" style={{ color: "#2563eb" }}>
              {formatWeight(numDemand)}
            </span>
          </div>
          <div className="metric-subtext">District buyer absorption window</div>
        </div>
      </div>

      {/* Operator Strategic Directive */}
      {primaryRec && (
        <section className="action-banner" style={{ background: "linear-gradient(135deg, #1e3a8a, #1d4ed8)" }}>
          <div className="action-banner-badge" style={{ backgroundColor: "rgba(255, 255, 255, 0.15)" }}>
            🏭 Operator Strategic Directive • {primaryRec.priority} PRIORITY
          </div>
          <div className="action-banner-title">
            {formatActionTitle(primaryRec.action)}
          </div>
          <div className="action-banner-rationale" style={{ color: "#dbeafe" }}>
            {primaryRec.reason}
          </div>
          <div className="action-banner-meta" style={{ borderColor: "rgba(255, 255, 255, 0.2)" }}>
            <div className="action-meta-item">
              Decision Confidence: <strong>{formatPercent(primaryRec.confidence * 100)}</strong>
            </div>
            <div className="action-meta-item">
              Market Planning Window: <strong>Next {window_days} Days</strong>
            </div>
          </div>
        </section>
      )}

      {/* Managed Facilities Table */}
      <div className="card" style={{ marginBottom: "24px" }}>
        <div className="card-header">
          <div>
            <div className="card-title">Managed Cold Storage Facilities</div>
            <div className="card-subtitle">
              Live capacity breakdown across units in {district}
            </div>
          </div>
        </div>
        {stores.length > 0 ? (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Facility Name</th>
                  <th>Block</th>
                  <th>Total Capacity</th>
                  <th>Current Occupancy</th>
                  <th>Space Utilization</th>
                </tr>
              </thead>
              <tbody>
                {stores.map((store) => {
                  const util = Number(store.utilization_percentage) || 0;
                  return (
                    <tr key={store.id}>
                      <td style={{ fontWeight: 700 }}>{store.name}</td>
                      <td>{store.block || "—"}</td>
                      <td>{formatWeight(Number(store.capacity_kg))}</td>
                      <td style={{ fontWeight: 600, color: "var(--primary-700)" }}>
                        {formatWeight(Number(store.current_occupancy_kg))}
                      </td>
                      <td style={{ minWidth: "160px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <div className="risk-score-bar-bg" style={{ flex: 1, margin: 0 }}>
                            <div
                              className="risk-score-bar-fill"
                              style={{
                                width: `${Math.min(util, 100)}%`,
                                backgroundColor:
                                  util > 85 ? "#ef4444" : util > 65 ? "#f59e0b" : "#10b981",
                              }}
                            />
                          </div>
                          <span style={{ fontSize: "0.82rem", fontWeight: 700, minWidth: "45px" }}>
                            {formatPercent(util)}
                          </span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p style={{ color: "var(--slate-500)", fontSize: "0.88rem" }}>No facilities currently assigned.</p>
        )}
      </div>

      {/* Storage Risks Section */}
      <div style={{ marginBottom: "24px" }}>
        <h2 style={{ fontSize: "1.2rem", fontWeight: 700, marginBottom: "12px", color: "var(--slate-900)" }}>
          Warehouse & Release Risk Analysis
        </h2>
        <div className="risks-grid">
          {risks.map((r, idx) => (
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

      {/* Secondary Directives */}
      {secondaryRecs.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">Secondary Operational Directives</div>
              <div className="card-subtitle">Additional facility recommendations</div>
            </div>
          </div>
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
        </div>
      )}
    </div>
  );
};
