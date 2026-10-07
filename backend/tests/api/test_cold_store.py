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
    assert events_list[0]["commodity_name"] == "Potato"
    assert events_list[0]["commodity_code"] == "POTATO"
    assert events_list[1]["commodity_name"] == "Potato"
    assert events_list[1]["commodity_code"] == "POTATO"


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


def test_multi_commodity_capacity_overflow_and_atomicity(client_with_db):
    # Register operator
    reg = client_with_db.post("/api/v1/auth/register", json={
        "name": "Operator Multi",
        "identifier": "multi_op@test.com",
        "password": "password123",
        "role": "COLD_STORE_OPERATOR",
        "district": "Purba Bardhaman",
        "organization_name": "Multi Chamber Ltd",
    })
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Create store with capacity 100,000 kg
    store = client_with_db.post("/api/v1/cold-store/stores", headers=headers, json={
        "name": "Chamber 1",
        "district": "Purba Bardhaman",
        "capacity_kg": 100000.0,
    }).json()
    store_id = store["id"]

    # Load 70,000 kg of Commodity 1 (Potato)
    load1 = client_with_db.post(f"/api/v1/cold-store/stores/{store_id}/events", headers=headers, json={
        "commodity_id": 1,
        "event_type": "LOADING",
        "quantity_kg": 70000.0,
        "event_date": "2026-10-06",
        "reference": "Batch Potato 1",
    })
    assert load1.status_code == 201

    # Attempt to load 40,000 kg of Commodity 1 (70k + 40k = 110k > 100k capacity) -> Rejects 409
    load2 = client_with_db.post(f"/api/v1/cold-store/stores/{store_id}/events", headers=headers, json={
        "commodity_id": 1,
        "event_type": "LOADING",
        "quantity_kg": 40000.0,
        "event_date": "2026-10-06",
        "reference": "Batch Potato 2",
    })
    assert load2.status_code == 409
    assert "exceeds cold store capacity" in load2.json()["detail"]

    # Verify inventory was NOT updated on rejection
    inv = client_with_db.get(f"/api/v1/cold-store/stores/{store_id}/inventory", headers=headers).json()
    assert Decimal(str(inv[0]["current_quantity_kg"])) == Decimal("70000.00")

    # Verify no partial event was logged for the rejected attempt
    events = client_with_db.get(f"/api/v1/cold-store/stores/{store_id}/events", headers=headers).json()
    assert len(events) == 1


def test_operator_multi_store_occupancy_aggregation(client_with_db):
    """Verify that list_operator_stores accurately aggregates occupancy across multiple facilities,
    including stores with zero inventory, in a single SQL operation.
    """
    reg = client_with_db.post("/api/v1/auth/register", json={
        "name": "Operator Multi-Store",
        "identifier": "multi_stores@test.com",
        "password": "password123",
        "role": "COLD_STORE_OPERATOR",
        "district": "Hooghly",
        "organization_name": "Bengal Cold Hubs",
    })
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # 1. Create Store 1 (100k kg capacity)
    s1 = client_with_db.post("/api/v1/cold-store/stores", headers=headers, json={
        "name": "Hub North",
        "district": "Hooghly",
        "capacity_kg": 100000.0,
    }).json()

    # 2. Create Store 2 (50k kg capacity)
    s2 = client_with_db.post("/api/v1/cold-store/stores", headers=headers, json={
        "name": "Hub South",
        "district": "Hooghly",
        "capacity_kg": 50000.0,
    }).json()

    # 3. Create Store 3 (20k kg capacity - left completely empty)
    s3 = client_with_db.post("/api/v1/cold-store/stores", headers=headers, json={
        "name": "Hub West",
        "district": "Hooghly",
        "capacity_kg": 20000.0,
    }).json()

    # Load 40,000 kg into Store 1
    client_with_db.post(f"/api/v1/cold-store/stores/{s1['id']}/events", headers=headers, json={
        "commodity_id": 1,
        "event_type": "LOADING",
        "quantity_kg": 40000.0,
        "event_date": "2026-10-06",
    })

    # Load 25,000 kg into Store 2
    client_with_db.post(f"/api/v1/cold-store/stores/{s2['id']}/events", headers=headers, json={
        "commodity_id": 1,
        "event_type": "LOADING",
        "quantity_kg": 25000.0,
        "event_date": "2026-10-06",
    })

    # Fetch all operator stores
    stores_list = client_with_db.get("/api/v1/cold-store/stores", headers=headers).json()
    assert len(stores_list) == 3

    store_map = {s["id"]: s for s in stores_list}
    # Check Store 1: 40k occupancy (40%)
    assert Decimal(str(store_map[s1["id"]]["current_occupancy_kg"])) == Decimal("40000.00")
    assert Decimal(str(store_map[s1["id"]]["utilization_percentage"])) == Decimal("40.00")

    # Check Store 2: 25k occupancy (50%)
    assert Decimal(str(store_map[s2["id"]]["current_occupancy_kg"])) == Decimal("25000.00")
    assert Decimal(str(store_map[s2["id"]]["utilization_percentage"])) == Decimal("50.00")

    # Check Store 3: 0 occupancy (0%)
    assert Decimal(str(store_map[s3["id"]]["current_occupancy_kg"])) == Decimal("0")
    assert Decimal(str(store_map[s3["id"]]["utilization_percentage"])) == Decimal("0.00")


def test_cold_store_event_commodity_joinedload(client_with_db):
    """Verify that list_cold_store_events eager-loads Commodity relationships across different
    commodities without executing full-table scans.
    """
    from app.models.models import Commodity
    from app.db.session import get_db

    # Register operator
    reg = client_with_db.post("/api/v1/auth/register", json={
        "name": "Operator Multi Commodity",
        "identifier": "multi_comm@test.com",
        "password": "password123",
        "role": "COLD_STORE_OPERATOR",
        "district": "Hooghly",
        "organization_name": "Multi Commodity Cold Store",
    })
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # Add a second commodity (Onion) into DB
    store = client_with_db.post("/api/v1/cold-store/stores", headers=headers, json={
        "name": "Chamber Multi",
        "district": "Hooghly",
        "capacity_kg": 50000.0,
    }).json()
    store_id = store["id"]

    # Record Potato event (Commodity ID 1)
    client_with_db.post(f"/api/v1/cold-store/stores/{store_id}/events", headers=headers, json={
        "commodity_id": 1,
        "event_type": "LOADING",
        "quantity_kg": 15000.0,
        "event_date": "2026-10-06",
        "reference": "Potato Lot 1",
    })

    # Fetch events and check joined commodity attributes
    events = client_with_db.get(f"/api/v1/cold-store/stores/{store_id}/events", headers=headers).json()
    assert len(events) == 1
    assert events[0]["commodity_id"] == 1
    assert events[0]["commodity_name"] == "Potato"
    assert events[0]["commodity_code"] == "POTATO"



