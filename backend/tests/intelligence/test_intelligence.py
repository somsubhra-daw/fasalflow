from datetime import date
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base, get_db
from app.db.seed import seed_database


@pytest.fixture
def seeded_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSession()
    seed_database(session)
    session.close()

    def override_get_db():
        s = TestingSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_farmer_intelligence_dashboard_and_risks(seeded_client):
    # Login as seeded farmer Anil Mahato
    res = seeded_client.post("/api/v1/auth/login", json={
        "identifier": "anil.mahato@fasalflow.in",
        "password": "password123",
    })
    assert res.status_code == 200
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch farmer dashboard
    dash_res = seeded_client.get("/api/v1/intelligence/farmer/dashboard?commodity_id=1&window_days=7", headers=headers)
    assert dash_res.status_code == 200
    dash = dash_res.json()

    assert dash["commodity_name"] == "Potato"
    assert dash["district"] == "Purba Bardhaman"
    assert "risks" in dash
    assert "recommendations" in dash
    assert Decimal(str(dash["expected_local_supply_kg"])) >= Decimal(0)
    assert Decimal(str(dash["visible_demand_kg"])) >= Decimal(0)

    # Check recommendations structure
    assert len(dash["recommendations"]) > 0
    rec = dash["recommendations"][0]
    assert "action" in rec
    assert "reason" in rec
    assert "priority" in rec
    assert "confidence" in rec

    # Direct risks endpoint
    risks_res = seeded_client.get("/api/v1/intelligence/farmer/risks?commodity_id=1", headers=headers)
    assert risks_res.status_code == 200
    assert isinstance(risks_res.json(), list)


def test_cold_store_intelligence_dashboard_and_risks(seeded_client):
    # Login as seeded operator Ratan Sen
    res = seeded_client.post("/api/v1/auth/login", json={
        "identifier": "operator@bardhaman-cold.com",
        "password": "password123",
    })
    assert res.status_code == 200
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    dash_res = seeded_client.get("/api/v1/intelligence/cold-store/dashboard?commodity_id=1&window_days=7", headers=headers)
    assert dash_res.status_code == 200
    dash = dash_res.json()

    # Operator specific fields
    assert Decimal(str(dash["total_capacity_kg"])) > Decimal(0)
    assert Decimal(str(dash["current_inventory_kg"])) > Decimal(0)
    assert Decimal(str(dash["capacity_utilization_pct"])) > Decimal(0)
    assert "release_pressure" in dash
    assert len(dash["recommendations"]) > 0


def test_role_separation_intelligence(seeded_client):
    # Farmer attempting to access cold store intelligence -> 403 Forbidden
    f_res = seeded_client.post("/api/v1/auth/login", json={
        "identifier": "anil.mahato@fasalflow.in",
        "password": "password123",
    })
    f_token = f_res.json()["access_token"]

    bad_dash = seeded_client.get("/api/v1/intelligence/cold-store/dashboard", headers={"Authorization": f"Bearer {f_token}"})
    assert bad_dash.status_code == 403

    # Operator attempting to access farmer intelligence -> 403 Forbidden
    op_res = seeded_client.post("/api/v1/auth/login", json={
        "identifier": "operator@bardhaman-cold.com",
        "password": "password123",
    })
    op_token = op_res.json()["access_token"]

    bad_farmer_dash = seeded_client.get("/api/v1/intelligence/farmer/dashboard", headers={"Authorization": f"Bearer {op_token}"})
    assert bad_farmer_dash.status_code == 403


def test_statistical_price_forecasting(seeded_client):
    res = seeded_client.get("/api/v1/intelligence/forecast/price?commodity_id=1&district=Purba%20Bardhaman")
    assert res.status_code == 200
    fc = res.json()
    assert fc["target_metric"] == "MODAL_PRICE"
    assert Decimal(str(fc["forecast_value"])) > Decimal(0)
    assert fc["method"] == "WEIGHTED_MOVING_AVERAGE"
    assert fc["confidence"] > 0.5
    assert fc["data_points_used"] > 0
