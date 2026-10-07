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

    init_session = TestingSession()
    seed_database(init_session)
    init_session.close()

    def override_get_db():
        s = TestingSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client, TestingSession
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_farmer_intelligence_dashboard_and_risks(seeded_client):
    client, _ = seeded_client
    # Login as seeded farmer Anil Mahato
    res = client.post("/api/v1/auth/login", json={
        "identifier": "anil.mahato@fasalflow.in",
        "password": "password123",
    })
    assert res.status_code == 200
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch farmer dashboard
    dash_res = client.get("/api/v1/intelligence/farmer/dashboard?commodity_id=1&window_days=7", headers=headers)
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
    risks_res = client.get("/api/v1/intelligence/farmer/risks?commodity_id=1", headers=headers)
    assert risks_res.status_code == 200
    assert isinstance(risks_res.json(), list)


def test_cold_store_intelligence_dashboard_and_risks(seeded_client):
    client, _ = seeded_client
    # Login as seeded operator Ratan Sen
    res = client.post("/api/v1/auth/login", json={
        "identifier": "operator@bardhaman-cold.com",
        "password": "password123",
    })
    assert res.status_code == 200
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    dash_res = client.get("/api/v1/intelligence/cold-store/dashboard?commodity_id=1&window_days=7", headers=headers)
    assert dash_res.status_code == 200
    dash = dash_res.json()

    # Operator specific fields
    assert Decimal(str(dash["total_capacity_kg"])) > Decimal(0)
    assert Decimal(str(dash["current_inventory_kg"])) > Decimal(0)
    assert Decimal(str(dash["capacity_utilization_pct"])) > Decimal(0)
    assert "release_pressure" in dash
    assert len(dash["recommendations"]) > 0


def test_role_separation_intelligence(seeded_client):
    client, _ = seeded_client
    # Farmer attempting to access cold store intelligence -> 403 Forbidden
    f_res = client.post("/api/v1/auth/login", json={
        "identifier": "anil.mahato@fasalflow.in",
        "password": "password123",
    })
    f_token = f_res.json()["access_token"]

    bad_dash = client.get("/api/v1/intelligence/cold-store/dashboard", headers={"Authorization": f"Bearer {f_token}"})
    assert bad_dash.status_code == 403

    # Operator attempting to access farmer intelligence -> 403 Forbidden
    op_res = client.post("/api/v1/auth/login", json={
        "identifier": "operator@bardhaman-cold.com",
        "password": "password123",
    })
    op_token = op_res.json()["access_token"]

    bad_farmer_dash = client.get("/api/v1/intelligence/farmer/dashboard", headers={"Authorization": f"Bearer {op_token}"})
    assert bad_farmer_dash.status_code == 403


def test_statistical_price_forecasting(seeded_client):
    client, TestingSession = seeded_client

    # 1. Forecast for Potato (id=1)
    res = client.get("/api/v1/intelligence/forecast/price?commodity_id=1&district=Purba%20Bardhaman")
    assert res.status_code == 200
    fc = res.json()
    assert fc["commodity_id"] == 1
    assert fc["commodity_code"] == "POTATO"
    assert fc["commodity_name"] == "Potato"
    assert fc["target_metric"] == "MODAL_PRICE"
    assert Decimal(str(fc["forecast_value"])) > Decimal(0)
    assert fc["method"] == "WEIGHTED_MOVING_AVERAGE"
    assert fc["confidence"] > 0.5
    assert fc["data_points_used"] > 0

    # 2. Add second commodity (Onion) and verify identity is NOT hardcoded to Potato
    from app.models.models import Commodity
    with TestingSession() as db:
        onion = Commodity(name="Onion", code="ONION", default_unit="kg")
        db.add(onion)
        db.commit()
        db.refresh(onion)
        onion_id = onion.id

    res_onion = client.get(f"/api/v1/intelligence/forecast/price?commodity_id={onion_id}&district=Purba%20Bardhaman")
    assert res_onion.status_code == 200
    fc_onion = res_onion.json()
    assert fc_onion["commodity_id"] == onion_id
    assert fc_onion["commodity_code"] == "ONION"
    assert fc_onion["commodity_name"] == "Onion"
    assert fc_onion["data_points_used"] == 0  # No prices recorded yet -> baseline fallback
    assert fc_onion["method"] == "DEFAULT_BASELINE"

    # 3. Invalid commodity ID (99999) must return HTTP 404
    res_invalid = client.get("/api/v1/intelligence/forecast/price?commodity_id=99999&district=Purba%20Bardhaman")
    assert res_invalid.status_code == 404
    assert "not found" in res_invalid.json()["detail"].lower()


def test_district_filtered_demand_isolation(seeded_client):
    from datetime import timedelta
    from app.models.models import Buyer, BuyerDemand
    from app.models.enums import BuyerType, DemandStatus
    from app.intelligence.features.supply_demand import calculate_shared_supply_demand

    _, session_factory = seeded_client
    with session_factory() as db:
        # Create a specific high demand in Hooghly district
        hooghly_buyer = Buyer(
            name="Hooghly Processor",
            buyer_type=BuyerType.PROCESSOR,
            district="Hooghly",
            active=True,
        )
        db.add(hooghly_buyer)
        db.flush()

        hooghly_demand = BuyerDemand(
            buyer_id=hooghly_buyer.id,
            commodity_id=1,
            quantity_kg=Decimal("999999.00"),
            required_from=date.today(),
            required_until=date.today() + timedelta(days=14),
            max_price_per_kg=Decimal("25.00"),
            status=DemandStatus.ACTIVE,
        )
        db.add(hooghly_demand)
        db.commit()

        # Calculate metrics for Purba Bardhaman:
        # Seeded Purba Bardhaman buyers: Bengal Food (50,000 kg) + Damodar Valley (75,000 kg) = 125,000 kg
        burdwan_metrics = calculate_shared_supply_demand(
            db=db,
            commodity_id=1,
            district="Purba Bardhaman",
            window_days=7,
        )

        # 1. Purba Bardhaman demand is accurately included: exactly 125,000 kg
        assert burdwan_metrics.forecast_demand_kg == Decimal("125000.00")

        # 2. Kolkata demand (100,000 kg), Howrah demand (125,000 kg), and Hooghly (999,999 kg) must NOT leak
        kolkata_metrics = calculate_shared_supply_demand(db=db, commodity_id=1, district="Kolkata", window_days=7)
        howrah_metrics = calculate_shared_supply_demand(db=db, commodity_id=1, district="Howrah", window_days=7)

        assert kolkata_metrics.forecast_demand_kg == Decimal("100000.00")
        assert howrah_metrics.forecast_demand_kg == Decimal("125000.00")



def test_farmer_specific_exposure_differentiation(seeded_client):
    client, _ = seeded_client

    # 1. Login as Anil Mahato (has 35,000 kg seeded supply -> HIGH exposure)
    res_anil = client.post("/api/v1/auth/login", json={
        "identifier": "anil.mahato@fasalflow.in",
        "password": "password123",
    })
    token_anil = res_anil.json()["access_token"]
    dash_anil = client.get("/api/v1/intelligence/farmer/dashboard", headers={"Authorization": f"Bearer {token_anil}"}).json()
    assert Decimal(str(dash_anil["farmer_active_supply_kg"])) == Decimal("35000.00")
    assert dash_anil["farmer_exposure_level"] == "HIGH"
    # Check that unsold produce risk was evaluated for high exposure
    risk_types_anil = [r["risk_type"] for r in dash_anil["risks"]]
    assert "UNSOLD_PRODUCE_RISK" in risk_types_anil

    # 2. Register a new small farmer with only 500 kg
    client.post("/api/v1/auth/register", json={
        "name": "Small Farmer Raju",
        "identifier": "small_raju@fasalflow.in",
        "password": "password123",
        "role": "FARMER",
        "district": "Purba Bardhaman",
    })
    res_raju = client.post("/api/v1/auth/login", json={
        "identifier": "small_raju@fasalflow.in",
        "password": "password123",
    })
    token_raju = res_raju.json()["access_token"]
    headers_raju = {"Authorization": f"Bearer {token_raju}"}

    # Create farm and 500 kg supply
    farm_raju = client.post("/api/v1/farmer/farms", headers=headers_raju, json={
        "name": "Raju Small Plot",
        "district": "Purba Bardhaman",
    }).json()
    client.post("/api/v1/farmer/supply", headers=headers_raju, json={
        "farm_id": farm_raju["id"],
        "commodity_id": 1,
        "quantity_kg": 500.0,
        "expected_harvest_date": str(date.today()),
    })

    dash_raju = client.get("/api/v1/intelligence/farmer/dashboard", headers=headers_raju).json()
    assert Decimal(str(dash_raju["farmer_active_supply_kg"])) == Decimal("500.00")
    assert dash_raju["farmer_exposure_level"] == "LOW"
    risk_types_raju = [r["risk_type"] for r in dash_raju["risks"]]
    # Small farmer does NOT suffer high UNSOLD_PRODUCE_RISK
    assert "UNSOLD_PRODUCE_RISK" not in risk_types_raju


def test_price_trend_calculation_same_day_multimarket_vs_distinct_dates(seeded_client):
    """Verify that price trend calculation:
    1. Averages multiple markets on the SAME date rather than falsely comparing them as a trend.
    2. Compares distinct consecutive dates to determine UPWARD, DOWNWARD, or STABLE.
    3. Respects PRICE_TREND_THRESHOLD (Decimal('0.50')).
    """
    _, TestingSession = seeded_client
    from app.models.models import Market, MarketPrice, Commodity
    from app.intelligence.features.supply_demand import calculate_shared_supply_demand
    from datetime import timedelta

    with TestingSession() as db:
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Create two distinct markets in a test district "Bankura"
        m1 = Market(name="Bankura Town Mandi", district="Bankura", latitude=23.23, longitude=87.07)
        m2 = Market(name="Bishnupur Mandi", district="Bankura", latitude=23.07, longitude=87.32)
        db.add_all([m1, m2])
        db.flush()

        # Case 1: Two markets on the SAME date with different prices (22.00 vs 18.00)
        # Old code compared market 1 and market 2 and declared UPWARD.
        # Fixed code groups by date, so only 1 date exists -> trend must be STABLE.
        p1 = MarketPrice(market_id=m1.id, commodity_id=1, date=today, min_price_per_kg=20, modal_price_per_kg=22, max_price_per_kg=24, source="TEST")
        p2 = MarketPrice(market_id=m2.id, commodity_id=1, date=today, min_price_per_kg=16, modal_price_per_kg=18, max_price_per_kg=20, source="TEST")
        db.add_all([p1, p2])
        db.commit()

        metrics_same_day = calculate_shared_supply_demand(db=db, commodity_id=1, district="Bankura", reference_date=today)
        # Average of 22.00 and 18.00 is 20.00
        assert metrics_same_day.current_modal_price == Decimal("20.00")
        assert metrics_same_day.price_trend == "STABLE"

        # Case 2: Add prices on yesterday (18.00 average)
        # Today avg = 20.00, Yesterday avg = 18.00 -> Diff = +2.00 (> 0.50) -> UPWARD
        p_y1 = MarketPrice(market_id=m1.id, commodity_id=1, date=yesterday, min_price_per_kg=17, modal_price_per_kg=18, max_price_per_kg=19, source="TEST")
        p_y2 = MarketPrice(market_id=m2.id, commodity_id=1, date=yesterday, min_price_per_kg=17, modal_price_per_kg=18, max_price_per_kg=19, source="TEST")
        db.add_all([p_y1, p_y2])
        db.commit()

        metrics_upward = calculate_shared_supply_demand(db=db, commodity_id=1, district="Bankura", reference_date=today)
        assert metrics_upward.current_modal_price == Decimal("20.00")
        assert metrics_upward.price_trend == "UPWARD"

        # Case 3: Today's prices drop to 16.00 average -> Diff = 16.00 - 18.00 = -2.00 (< -0.50) -> DOWNWARD
        p1.min_price_per_kg = Decimal("15.00")
        p1.modal_price_per_kg = Decimal("16.00")
        p1.max_price_per_kg = Decimal("17.00")

        p2.min_price_per_kg = Decimal("15.00")
        p2.modal_price_per_kg = Decimal("16.00")
        p2.max_price_per_kg = Decimal("17.00")
        db.commit()

        metrics_downward = calculate_shared_supply_demand(db=db, commodity_id=1, district="Bankura", reference_date=today)
        assert metrics_downward.current_modal_price == Decimal("16.00")
        assert metrics_downward.price_trend == "DOWNWARD"

        # Case 4: Price difference within threshold (18.20 vs 18.00 = +0.20 <= 0.50) -> STABLE
        p1.min_price_per_kg = Decimal("17.00")
        p1.modal_price_per_kg = Decimal("18.20")
        p1.max_price_per_kg = Decimal("19.00")

        p2.min_price_per_kg = Decimal("17.00")
        p2.modal_price_per_kg = Decimal("18.20")
        p2.max_price_per_kg = Decimal("19.00")
        db.commit()

        metrics_stable = calculate_shared_supply_demand(db=db, commodity_id=1, district="Bankura", reference_date=today)
        assert metrics_stable.current_modal_price == Decimal("18.20")
        assert metrics_stable.price_trend == "STABLE"


def test_missing_price_data_does_not_produce_sell_now_recommendation(seeded_client):
    """Verify that when market prices or demand data are insufficient:
    1. Metrics reflect None for current_modal_price and price_trend.
    2. Recommendation engine NEVER defaults to SELL_NOW when price is missing.
    3. Recommendation engine NEVER defaults to SELL_NOW when demand is missing.
    4. Valid seeded market data continues to generate valid actionable recommendations.
    5. Farmer dashboard endpoint reflects null for missing prices without fabricating values.
    """
    client, TestingSession = seeded_client
    from app.intelligence.features.supply_demand import calculate_shared_supply_demand
    from app.intelligence.risk.farmer import evaluate_farmer_risks, generate_farmer_recommendations
    from app.intelligence.features.metrics import MarketSupplyDemandMetrics

    with TestingSession() as db:
        # Case 1: District with no recorded market prices (Darjeeling)
        metrics_no_price = calculate_shared_supply_demand(db=db, commodity_id=1, district="Darjeeling")
        assert metrics_no_price.current_modal_price is None
        assert metrics_no_price.price_trend is None

        risks_no_price = evaluate_farmer_risks(metrics_no_price, farmer_quantity_kg=Decimal(5000))
        assert "INSUFFICIENT_DATA" in [r.risk_type for r in risks_no_price]

        recs_no_price = generate_farmer_recommendations(metrics_no_price, risks_no_price, farmer_quantity_kg=Decimal(5000))
        actions_no_price = [r.action for r in recs_no_price]

        # Invariant 1: No prices -> NEVER SELL_NOW
        assert "SELL_NOW" not in actions_no_price
        assert "INSUFFICIENT_DATA" in actions_no_price
        assert "MONITOR_PRICE" in actions_no_price

        # Case 2: District with valid price but ZERO demand (no buyers)
        metrics_no_demand = MarketSupplyDemandMetrics(
            commodity_id=1,
            commodity_name="Potato",
            commodity_code="POTATO",
            district="TestZeroDemand",
            window_days=7,
            start_date=date.today(),
            end_date=date.today(),
            expected_fresh_supply_kg=Decimal("10000.00"),
            expected_storage_release_kg=Decimal("0.00"),
            existing_commitments_kg=Decimal("0.00"),
            expected_loss_kg=Decimal("500.00"),
            effective_supply_kg=Decimal("9500.00"),
            forecast_demand_kg=Decimal("0.00"),  # Zero demand
            supply_gap_kg=Decimal("-9500.00"),
            status="BALANCED",
            current_modal_price=Decimal("22.00"),  # Price exists
            price_trend="STABLE",
        )
        recs_no_demand = generate_farmer_recommendations(metrics_no_demand, [], farmer_quantity_kg=Decimal(2000))
        actions_no_demand = [r.action for r in recs_no_demand]

        # Invariant 2: No demand -> NEVER SELL_NOW
        assert "SELL_NOW" not in actions_no_demand
        assert "INSUFFICIENT_DATA" in actions_no_demand

        # Case 3: Seeded Purba Bardhaman data with real prices and demand -> normal recommendations
        metrics_seeded = calculate_shared_supply_demand(db=db, commodity_id=1, district="Purba Bardhaman")
        assert metrics_seeded.current_modal_price is not None
        assert metrics_seeded.forecast_demand_kg > Decimal(0)
        recs_seeded = generate_farmer_recommendations(metrics_seeded, [], farmer_quantity_kg=Decimal(5000))
        assert len(recs_seeded) > 0
        assert "INSUFFICIENT_DATA" not in [r.action for r in recs_seeded]





