import React from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { logout, type UserProfile } from "../lib/api/auth";

interface NavbarProps {
  user: UserProfile | null;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    onLogout();
    navigate("/login");
  };

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <div className="brand-group">
          <Link to="/" className="brand-logo">
            <span className="brand-logo-icon">🌱</span>
            <span>FasalFlow</span>
          </Link>
          <div className="pilot-tag">
            <span className="pilot-tag-pulse"></span>
            <span>WB Pilot • Purba Bardhaman • Potato</span>
          </div>
        </div>

        <nav className="nav-links">
          {user ? (
            <>
              {user.role === "FARMER" && (
                <Link
                  to="/farmer"
                  className={`nav-link ${location.pathname.startsWith("/farmer") ? "active" : ""}`}
                >
                  Farmer Dashboard
                </Link>
              )}
              {user.role === "COLD_STORE_OPERATOR" && (
                <Link
                  to="/cold-store"
                  className={`nav-link ${location.pathname.startsWith("/cold-store") ? "active" : ""}`}
                >
                  Cold Store Dashboard
                </Link>
              )}
              <Link
                to="/market"
                className={`nav-link ${location.pathname.startsWith("/market") ? "active" : ""}`}
              >
                Market Intelligence
              </Link>
              <div className="nav-user">
                <div className="user-badge">
                  <span className="user-name">{user.name}</span>
                  <span className="user-role-label">
                    {user.role === "FARMER" ? "Farmer" : "Cold Store Operator"}
                  </span>
                </div>
                <button onClick={handleLogout} className="btn-logout" title="Log out">
                  Log Out
                </button>
              </div>
            </>
          ) : (
            <>
              <Link
                to="/market"
                className={`nav-link ${location.pathname.startsWith("/market") ? "active" : ""}`}
              >
                Market Intelligence
              </Link>
              <Link to="/login" className="btn-primary" style={{ padding: "7px 16px", fontSize: "0.88rem" }}>
                Sign In
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
};
