import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginUser, getCurrentUser } from "../lib/api/auth";

interface LoginPageProps {
  onLoginSuccess: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await loginUser({ identifier, password });
      await getCurrentUser();
      onLoginSuccess();
      if (res.role === "FARMER") {
        navigate("/farmer");
      } else {
        navigate("/cold-store");
      }
    } catch (err: any) {
      setError(err?.message || "Invalid credentials. Please verify your email/password.");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (demoId: string, demoPass: string, role: "FARMER" | "COLD_STORE_OPERATOR") => {
    setError(null);
    setLoading(true);
    setIdentifier(demoId);
    setPassword(demoPass);

    try {
      await loginUser({ identifier: demoId, password: demoPass });
      await getCurrentUser();
      onLoginSuccess();
      navigate(role === "FARMER" ? "/farmer" : "/cold-store");
    } catch (err: any) {
      setError(err?.message || "Demo login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-wrap">
      <div style={{ textAlign: "center", marginBottom: "24px" }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--slate-900)" }}>
          Sign in to FasalFlow
        </h1>
        <p style={{ fontSize: "0.88rem", color: "var(--slate-500)", marginTop: "4px" }}>
          Agricultural Decision Support System
        </p>
      </div>

      {error && <div className="alert-error">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label" htmlFor="identifier">
            Email or Registered Phone
          </label>
          <input
            id="identifier"
            type="text"
            className="form-input"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="e.g. anil.mahato@fasalflow.in"
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            className="form-input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            required
          />
        </div>

        <button
          type="submit"
          className="btn-primary"
          style={{ width: "100%", marginTop: "8px" }}
          disabled={loading}
        >
          {loading ? "Authenticating..." : "Sign In"}
        </button>
      </form>

      {/* Demo shortcuts for evaluators */}
      <div className="demo-credentials-box">
        <div style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--slate-600)", textTransform: "uppercase" }}>
          ⚡ Hackathon Evaluator Quick Access
        </div>
        <div className="demo-btn-group">
          <button
            type="button"
            className="btn-demo-quick"
            onClick={() => handleQuickLogin("anil.mahato@fasalflow.in", "password123", "FARMER")}
            disabled={loading}
          >
            <div>
              <strong>Farmer:</strong> Anil Mahato
              <div style={{ fontSize: "0.75rem", color: "var(--slate-500)" }}>Purba Bardhaman • Potato 35 MT</div>
            </div>
            <span>➔</span>
          </button>

          <button
            type="button"
            className="btn-demo-quick"
            onClick={() => handleQuickLogin("operator@bardhaman-cold.com", "password123", "COLD_STORE_OPERATOR")}
            disabled={loading}
          >
            <div>
              <strong>Cold Store:</strong> Ratan Sen
              <div style={{ fontSize: "0.75rem", color: "var(--slate-500)" }}>Memari & Galsi Units • 18,000 MT</div>
            </div>
            <span>➔</span>
          </button>
        </div>
      </div>
    </div>
  );
};
