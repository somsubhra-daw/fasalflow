from datetime import date
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import Base, get_db
from app.models.models import Commodity


@pytest.fixture
def client_with_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Seed baseline commodity
    session = TestingSession()
    potato = Commodity(id=1, name="Potato", code="POTATO", default_unit="kg")
    session.add(potato)
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


def test_cold_store_crud_and_events_workflow(client_with_db):
    # 1. Register Operator A
    reg_a = client_with_db.post("/api/v1/auth/register", json={
        "name": "Operator Subhash",
        "identifier": "subhash@coldchain.com",
        "password": "password123",
        "role": "COLD_STORE_OPERATOR",
        "district": "Purba Bardhaman",
        "organization_name": "Burdwan Kisan Cold Storage",
    })
    token_a = reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Check profile
    prof = client_with_db.get("/api/v1/cold-store/profile", headers=headers_a).json()
    assert prof["organization_name"] == "Burdwan Kisan Cold Storage"
    assert prof["total_stores"] == 0

    # 3. Create Cold Store: capacity 100,000 kg
    store_res = client_with_db.post("/api/v1/cold-store/stores", headers=headers_a, json={
        "name": "Unit 1 Memari",
        "district": "Purba Bardhaman",
        "capacity_kg": 100000.0,
    })
    assert store_res.status_code == 201
    store_id = store_res.json()["id"]

    # 4. Load stock: 60,000 kg Potato
    load_res = client_with_db.post(f"/api/v1/cold-store/stores/{store_id}/events", headers=headers_a, json={
        "commodity_id": 1,
        "event_type": "LOADING",
        "quantity_kg": 60000.0,
        "event_date": "2026-10-06",
        "reference": "Farmer Batch A-10",
    })
    assert load_res.status_code == 201
    assert Decimal(str(load_res.json()["quantity_kg"])) == Decimal("60000.00")

    # Verify inventory balance is now 60,000 kg
    inv = client_with_db.get(f"/api/v1/cold-store/stores/{store_id}/inventory", headers=headers_a).json()
    assert len(inv) == 1
    assert Decimal(str(inv[0]["current_quantity_kg"])) == Decimal("60000")

    # Verify store occupancy & utilization: 60,000 kg / 100,000 kg = 60.0%
    store_detail = client_with_db.get(f"/api/v1/cold-store/stores/{store_id}", headers=headers_a).json()
    assert Decimal(str(store_detail["current_occupancy_kg"])) == Decimal("60000")
    assert Decimal(str(store_detail["utilization_percentage"])) == Decimal("60")

    # 5. Test Capacity Overflow: try loading another 50,000 kg (60k + 50k = 110k > 100k) -> Must reject 409
    overflow_res = client_with_db.post(f"/api/v1/cold-store/stores/{store_id}/events", headers=headers_a, json={
        "commodity_id": 1,
        "event_type": "LOADING",
        "quantity_kg": 50000.0,
        "event_date": "2026-10-06",
        "reference": "Overflow batch",
    })
    assert overflow_res.status_code == 409
    assert "exceeds cold store capacity" in overflow_res.json()["detail"]

    # Inventory must remain exactly 60,000 kg
    inv_check = client_with_db.get(f"/api/v1/cold-store/stores/{store_id}/inventory", headers=headers_a).json()
    assert Decimal(str(inv_check[0]["current_quantity_kg"])) == Decimal("60000")

    # 6. Release Stock: 20,000 kg
    release_res = client_with_db.post(f"/api/v1/cold-store/stores/{store_id}/events", headers=headers_a, json={
        "commodity_id": 1,
        "event_type": "RELEASE",
        "quantity_kg": 20000.0,
        "event_date": "2026-10-07",
        "reference": "Wholesaler Buyer Pickup",
    })
    assert release_res.status_code == 201

    # Inventory should now be exactly 40,000 kg
    inv_after_rel = client_with_db.get(f"/api/v1/cold-store/stores/{store_id}/inventory", headers=headers_a).json()
    assert Decimal(str(inv_after_rel[0]["current_quantity_kg"])) == Decimal("40000")

    # 7. Test Insufficient Stock: attempt to release 50,000 kg when only 40,000 kg exists -> Must reject 409
    over_release = client_with_db.post(f"/api/v1/cold-store/stores/{store_id}/events", headers=headers_a, json={
        "commodity_id": 1,
        "event_type": "RELEASE",
        "quantity_kg": 50000.0,
        "event_date": "2026-10-08",
        "reference": "Invalid excessive release",
    })
    assert over_release.status_code == 409
    assert "Insufficient inventory" in over_release.json()["detail"]

    # 8. Check events audit history: 2 successful events (1 loading, 1 release)
    events_list = client_with_db.get(f"/api/v1/cold-store/stores/{store_id}/events", headers=headers_a).json()
    assert len(events_list) == 2


def test_operator_ownership_isolation(client_with_db):
    # Register Operator A
    reg_a = client_with_db.post("/api/v1/auth/register", json={
        "name": "Operator A",
        "identifier": "op_a@test.com",
        "password": "password123",
        "role": "COLD_STORE_OPERATOR",
        "district": "Purba Bardhaman",
        "organization_name": "Agro A",
    })
    headers_a = {"Authorization": f"Bearer {reg_a.json()['access_token']}"}

    # Register Operator B
    reg_b = client_with_db.post("/api/v1/auth/register", json={
        "name": "Operator B",
        "identifier": "op_b@test.com",
        "password": "password123",
        "role": "COLD_STORE_OPERATOR",
        "district": "Purba Bardhaman",
        "organization_name": "Agro B",
    })
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}

    # Operator A creates store
    store_a = client_with_db.post("/api/v1/cold-store/stores", headers=headers_a, json={
        "name": "Store A",
        "district": "Purba Bardhaman",
        "capacity_kg": 50000.0,
    }).json()
    store_a_id = store_a["id"]

    # Operator B attempts to post event to Store A -> 404 forbidden
    hack_event = client_with_db.post(f"/api/v1/cold-store/stores/{store_a_id}/events", headers=headers_b, json={
        "commodity_id": 1,
        "event_type": "LOADING",
        "quantity_kg": 1000.0,
        "event_date": "2026-10-06",
    })
    assert hack_event.status_code == 404

    # Operator B attempts to view Store A details -> 404 forbidden
    hack_view = client_with_db.get(f"/api/v1/cold-store/stores/{store_a_id}", headers=headers_b)
    assert hack_view.status_code == 404
