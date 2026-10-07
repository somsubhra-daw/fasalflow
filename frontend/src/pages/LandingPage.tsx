import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { loginUser, getCurrentUser } from "../lib/api/auth";

interface LandingPageProps {
  onLoginSuccess: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onLoginSuccess }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = React.useState<string | null>(null);

  const quickDemoLogin = async (identifier: string, role: "FARMER" | "COLD_STORE_OPERATOR") => {
    try {
      setLoading(role);
      await loginUser({ identifier, password: "password123" });
      await getCurrentUser();
      onLoginSuccess();
      navigate(role === "FARMER" ? "/farmer" : "/cold-store");
    } catch (err) {
      console.error(err);
      navigate("/login");
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="landing-wrap">
      <section className="landing-hero">
        <div className="landing-tagline">HSC-27 Hackathon • Pilot Demonstration</div>
        <h1 className="landing-title">
          Actionable Market Intelligence for Perishable Produce
        </h1>
        <p className="landing-subtitle">
          FasalFlow synchronizes harvest supply, cold-storage inventory, and buyer demand across local districts — delivering customized risk mitigation for both farmers and storage operators.
        </p>

        <div className="landing-actions">
          <button
            onClick={() => quickDemoLogin("anil.mahato@fasalflow.in", "FARMER")}
            className="btn-primary"
            disabled={loading !== null}
          >
            {loading === "FARMER" ? "Authenticating..." : "🧑‍🌾 Launch Farmer Demo"}
          </button>
          <button
            onClick={() => quickDemoLogin("operator@bardhaman-cold.com", "COLD_STORE_OPERATOR")}
            className="btn-secondary"
            disabled={loading !== null}
          >
            {loading === "COLD_STORE_OPERATOR" ? "Authenticating..." : "🏭 Launch Cold Store Demo"}
          </button>
          <Link to="/market" className="btn-secondary">
            📊 View Mandi Intelligence
          </Link>
        </div>
      </section>

      {/* Core Concept: One Data Layer, Role-Specific Decisions */}
      <section className="pipeline-diagram">
        <div style={{ textAlign: "center", marginBottom: "20px" }}>
          <h2 style={{ fontSize: "1.25rem", fontWeight: 800, color: "var(--slate-900)" }}>
            The Core Architecture: Shared Intelligence, Role-Specific Decisions
          </h2>
          <p style={{ fontSize: "0.88rem", color: "var(--slate-600)" }}>
            The same market conditions produce opposite operational recommendations depending on the stakeholder's role.
          </p>
        </div>

        <div className="pipeline-grid">
          <div className="pipeline-node">
            <div className="pipeline-node-title">🌾 Unified Market Data</div>
            <div className="pipeline-node-desc">
              District Harvest Forecasts<br />
              Cold Storage Occupancy<br />
              Local Mandi Prices & Arrivals<br />
              Active Buyer Demand Window
            </div>
          </div>

          <div className="pipeline-arrow">➔</div>

          <div className="pipeline-node highlight">
            <div className="pipeline-node-title">⚡ Intelligence Engine</div>
            <div className="pipeline-node-desc">
              Commodity × Geography × Time<br />
              (Potato • Purba Bardhaman • 7 Days)<br />
              Supply/Demand Ratio & Price Trend<br />
              Role-Specific Risk Matrices
            </div>
          </div>

          <div className="pipeline-arrow">➔</div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div className="pipeline-node" style={{ borderLeft: "4px solid var(--primary-600)" }}>
              <div className="pipeline-node-title">Farmer Action</div>
              <div className="pipeline-node-desc">
                Surplus Risk: <strong>HIGH</strong><br />
                Recommendation: <strong>STAGGER HARVEST</strong> or hold stock in cold store
              </div>
            </div>
            <div className="pipeline-node" style={{ borderLeft: "4px solid #2563eb)" }}>
              <div className="pipeline-node-title">Cold Store Action</div>
              <div className="pipeline-node-desc">
                Release Pressure: <strong>HIGH</strong><br />
                Recommendation: <strong>STAGGER RELEASES</strong> & secure buyer contracts
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pilot Scope Highlights */}
      <div className="metrics-grid">
        <div className="card">
          <div className="card-title">📍 Pilot District</div>
          <p style={{ marginTop: "8px", fontSize: "0.9rem", color: "var(--slate-600)" }}>
            <strong>Purba Bardhaman, West Bengal</strong><br />
            Known as the potato bowl of eastern India. Highly volatile seasonal arrival spikes.
          </p>
        </div>
        <div className="card">
          <div className="card-title">🥔 Target Commodity</div>
          <p style={{ marginTop: "8px", fontSize: "0.9rem", color: "var(--slate-600)" }}>
            <strong>Table & Seed Potato (Jyoti)</strong><br />
            Perishable semi-durable crop with critical dependency on mandi timing and cold facilities.
          </p>
        </div>
        <div className="card">
          <div className="card-title">⏱️ Decision Horizon</div>
          <p style={{ marginTop: "8px", fontSize: "0.9rem", color: "var(--slate-600)" }}>
            <strong>7-Day Forward Horizon</strong><br />
            Synchronized calculation of expected harvest vs warehouse releases against local buyer procurement.
          </p>
        </div>
      </div>
    </div>
  );
};
