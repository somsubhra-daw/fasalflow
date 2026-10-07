from datetime import date
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base, get_db
from app.models.models import Commodity, Market, MarketPrice, MarketArrival


@pytest.fixture
def client_with_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSession()
    # Baseline commodity
    potato = Commodity(id=1, name="Potato", code="POTATO", default_unit="kg")
    session.add(potato)

    # Baseline market
    market = Market(
        id=1,
        name="Memari Regulated Market",
        district="Purba Bardhaman",
        block="Memari-I",
        active=True,
    )
    session.add(market)
    session.flush()

    # Baseline price & arrival
    price = MarketPrice(
        market_id=market.id,
        commodity_id=potato.id,
        date=date(2026, 10, 5),
        min_price_per_kg=Decimal("18.50"),
        modal_price_per_kg=Decimal("21.00"),
        max_price_per_kg=Decimal("23.00"),
        source="synthetic",
    )
    arrival = MarketArrival(
        market_id=market.id,
        commodity_id=potato.id,
        date=date(2026, 10, 5),
        quantity_kg=Decimal("75000.00"),
        source="synthetic",
    )
    session.add(price)
    session.add(arrival)
    session.commit()
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


def test_market_and_price_and_arrival_endpoints(client_with_db):
    # 1. List markets
    res = client_with_db.get("/api/v1/markets")
    assert res.status_code == 200
    markets = res.json()
    assert len(markets) == 1
    assert markets[0]["name"] == "Memari Regulated Market"

    # Filter district
    res_filt = client_with_db.get("/api/v1/markets?district=Bardhaman")
    assert len(res_filt.json()) == 1
    res_empty = client_with_db.get("/api/v1/markets?district=Kolkata")
    assert len(res_empty.json()) == 0

    # 2. Market Prices with filters
    res_prices = client_with_db.get("/api/v1/markets/1/prices?commodity_id=1")
    assert res_prices.status_code == 200
    prices = res_prices.json()
    assert len(prices) == 1
    assert Decimal(str(prices[0]["modal_price_per_kg"])) == Decimal("21.00")
    assert prices[0]["commodity_name"] == "Potato"
    assert prices[0]["market_name"] == "Memari Regulated Market"

    # 3. Market Arrivals
    res_arr = client_with_db.get("/api/v1/markets/1/arrivals?commodity_id=1")
    assert res_arr.status_code == 200
    arrivals = res_arr.json()
    assert len(arrivals) == 1
    assert Decimal(str(arrivals[0]["quantity_kg"])) == Decimal("75000.00")


def test_buyer_and_demand_authorization(client_with_db):
    # 1. Unauthenticated buyer creation must be rejected (403)
    unauth_buyer = client_with_db.post("/api/v1/buyers", json={
        "name": "Unauthorized Buyer",
        "district": "Purba Bardhaman",
    })
    assert unauth_buyer.status_code == 403
    assert "operator authorization required" in unauth_buyer.json()["detail"].lower()

    # 2. Unauthenticated demand creation must be rejected (403)
    unauth_demand = client_with_db.post("/api/v1/buyers/demand", json={
        "buyer_id": 1,
        "commodity_id": 1,
        "quantity_kg": 5000.0,
        "required_from": "2026-10-10",
        "required_until": "2026-10-20",
        "max_price_per_kg": 20.0,
    })
    assert unauth_demand.status_code == 403

    # 3. Authenticated Farmer cannot create buyer or demand (403)
    farmer_reg = client_with_db.post("/api/v1/auth/register", json={
        "name": "Normal Farmer",
        "identifier": "farmer_auth_test@farm.com",
        "password": "password123",
        "role": "FARMER",
        "district": "Purba Bardhaman",
    })
    farmer_token = farmer_reg.json()["access_token"]
    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}

    farmer_buyer_res = client_with_db.post("/api/v1/buyers", headers=farmer_headers, json={
        "name": "Injected Buyer",
        "district": "Purba Bardhaman",
    })
    assert farmer_buyer_res.status_code == 403

    farmer_demand_res = client_with_db.post("/api/v1/buyers/demand", headers=farmer_headers, json={
        "buyer_id": 1,
        "commodity_id": 1,
        "quantity_kg": 50000.0,
        "required_from": "2026-10-10",
        "required_until": "2026-10-20",
        "max_price_per_kg": 20.0,
    })
    assert farmer_demand_res.status_code == 403

    # 4. Authenticated COLD_STORE_OPERATOR can create buyer and demand (201)
    operator_reg = client_with_db.post("/api/v1/auth/register", json={
        "name": "Storage Operator",
        "identifier": "operator_auth_test@store.com",
        "password": "password123",
        "role": "COLD_STORE_OPERATOR",
        "organization_name": "Bardhaman Cold Storage Ltd",
        "district": "Purba Bardhaman",
    })
    assert operator_reg.status_code == 201
    operator_token = operator_reg.json()["access_token"]
    operator_headers = {"Authorization": f"Bearer {operator_token}"}

    operator_buyer_res = client_with_db.post("/api/v1/buyers", headers=operator_headers, json={
        "name": "Operator Associated Buyer",
        "district": "Purba Bardhaman",
    })
    assert operator_buyer_res.status_code == 201
    created_buyer_id = operator_buyer_res.json()["id"]

    operator_demand_res = client_with_db.post("/api/v1/buyers/demand", headers=operator_headers, json={
        "buyer_id": created_buyer_id,
        "commodity_id": 1,
        "quantity_kg": 15000.0,
        "required_from": "2026-10-10",
        "required_until": "2026-10-20",
        "max_price_per_kg": 22.0,
    })
    assert operator_demand_res.status_code == 201

    # 5. Public READ operations still work without authentication
    public_buyers_res = client_with_db.get("/api/v1/buyers")
    assert public_buyers_res.status_code == 200

    public_demand_res = client_with_db.get("/api/v1/buyers/demand")
    assert public_demand_res.status_code == 200


def test_buyer_and_demand_workflow_with_internal_auth(client_with_db):
    internal_headers = {"X-Internal-Key": "fasalflow_internal_secret_key_change_in_production"}

    # 1. Create buyer via trusted internal worker
    buyer_res = client_with_db.post("/api/v1/buyers", headers=internal_headers, json={
        "name": "Kolkata Agro Processors",
        "buyer_type": "PROCESSOR",
        "district": "Kolkata",
        "phone": "9876543210",
    })
    assert buyer_res.status_code == 201
    buyer = buyer_res.json()
    buyer_id = buyer["id"]
    assert buyer["buyer_type"] == "PROCESSOR"

    # 2. Create demand via trusted internal worker
    demand_res = client_with_db.post("/api/v1/buyers/demand", headers=internal_headers, json={
        "buyer_id": buyer_id,
        "commodity_id": 1,
        "quantity_kg": 50000.0,
        "required_from": "2026-10-10",
        "required_until": "2026-10-25",
        "quality_grade": "A",
        "max_price_per_kg": 24.50,
        "status": "ACTIVE",
    })
    assert demand_res.status_code == 201
    demand = demand_res.json()
    assert Decimal(str(demand["quantity_kg"])) == Decimal("50000.00")
    assert demand["buyer_name"] == "Kolkata Agro Processors"

    # 3. Validation: required_until < required_from -> 422
    invalid_demand = client_with_db.post("/api/v1/buyers/demand", headers=internal_headers, json={
        "buyer_id": buyer_id,
        "commodity_id": 1,
        "quantity_kg": 50000.0,
        "required_from": "2026-10-25",
        "required_until": "2026-10-10",
        "max_price_per_kg": 24.50,
    })
    assert invalid_demand.status_code == 422

    # 4. List demands with date window filter
    active_demands = client_with_db.get("/api/v1/buyers/demand?commodity_id=1&date_window=2026-10-15").json()
    assert len(active_demands) == 1
    assert active_demands[0]["buyer_id"] == buyer_id

    out_of_window = client_with_db.get("/api/v1/buyers/demand?commodity_id=1&date_window=2026-11-01").json()
    assert len(out_of_window) == 0

