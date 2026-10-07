import React, { useState, useEffect } from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { Navbar } from "./components/Navbar";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { FarmerDashboard } from "./pages/FarmerDashboard";
import { ColdStoreDashboard } from "./pages/ColdStoreDashboard";
import { MarketIntelligencePage } from "./pages/MarketIntelligencePage";
import { getCachedUser, getCurrentUser, getStoredToken, type UserProfile } from "./lib/api/auth";

export default function App() {
  const [user, setUser] = useState<UserProfile | null>(getCachedUser());
  const [loadingUser, setLoadingUser] = useState(true);

  const refreshUser = async () => {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      setLoadingUser(false);
      return;
    }
    try {
      const profile = await getCurrentUser();
      setUser(profile);
    } catch {
      setUser(null);
    } finally {
      setLoadingUser(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const handleLogout = () => {
    setUser(null);
  };

  if (loadingUser && getStoredToken()) {
    return (
      <div className="loading-box" style={{ minHeight: "100vh" }}>
        <div className="spinner"></div>
        <p>Restoring session...</p>
      </div>
    );
  }

  return (
    <div className="app-container">
      <Navbar user={user} onLogout={handleLogout} />

      <main className="main-content">
        <Routes>
          {/* Public Landing & Marketing */}
          <Route path="/" element={<LandingPage onLoginSuccess={refreshUser} />} />

          {/* Login */}
          <Route
            path="/login"
            element={
              user ? (
                <Navigate to={user.role === "FARMER" ? "/farmer" : "/cold-store"} replace />
              ) : (
                <LoginPage onLoginSuccess={refreshUser} />
              )
            }
          />

          {/* Farmer Route */}
          <Route
            path="/farmer"
            element={
              user && user.role === "FARMER" ? (
                <FarmerDashboard />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />

          {/* Cold Store Operator Route */}
          <Route
            path="/cold-store"
            element={
              user && user.role === "COLD_STORE_OPERATOR" ? (
                <ColdStoreDashboard />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />

          {/* Market Intelligence Route (Publicly accessible) */}
          <Route path="/market" element={<MarketIntelligencePage />} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      <footer className="footer">
        <div style={{ maxWidth: "1240px", margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
          <div>
            <strong>FasalFlow</strong> • Agricultural Market-Intelligence & Decision-Support System
          </div>
          <div>
            Pilot District: <strong>Purba Bardhaman</strong> (Potato) • HSC-27 Hackathon Demonstration
          </div>
        </div>
      </footer>
    </div>
  );
}