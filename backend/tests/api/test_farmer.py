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


def test_farmer_profile_and_farm_crud(client_with_db):
    # 1. Register Farmer A
    reg_a = client_with_db.post("/api/v1/auth/register", json={
        "name": "Farmer Ramesh",
        "identifier": "ramesh@farm.com",
        "password": "password123",
        "role": "FARMER",
        "district": "Purba Bardhaman",
        "block": "Burdwan-I",
        "village": "Rayna",
    })
    token_a = reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Get Profile
    res_prof = client_with_db.get("/api/v1/farmer/profile", headers=headers_a)
    assert res_prof.status_code == 200
    prof = res_prof.json()
    assert prof["name"] == "Farmer Ramesh"
    assert prof["total_farms"] == 0
    assert Decimal(prof["total_active_supplies_kg"]) == Decimal(0)

    # 3. Create Farm for Farmer A
    farm_res = client_with_db.post("/api/v1/farmer/farms", headers=headers_a, json={
        "name": "Rayna Plot 1",
        "district": "Purba Bardhaman",
        "block": "Burdwan-I",
        "village": "Rayna",
        "area_acres": 4.5,
    })
    assert farm_res.status_code == 201
    farm_data = farm_res.json()
    farm_a_id = farm_data["id"]
    assert farm_data["name"] == "Rayna Plot 1"

    # 4. List Farms
    farms_list = client_with_db.get("/api/v1/farmer/farms", headers=headers_a).json()
    assert len(farms_list) == 1
    assert farms_list[0]["id"] == farm_a_id


def test_farmer_cannot_access_or_modify_another_farmers_farms_or_supplies(client_with_db):
    # Register Farmer A
    reg_a = client_with_db.post("/api/v1/auth/register", json={
        "name": "Farmer A",
        "identifier": "farmer_a@test.com",
        "password": "password123",
        "role": "FARMER",
        "district": "Purba Bardhaman",
    })
    headers_a = {"Authorization": f"Bearer {reg_a.json()['access_token']}"}

    # Register Farmer B
    reg_b = client_with_db.post("/api/v1/auth/register", json={
        "name": "Farmer B",
        "identifier": "farmer_b@test.com",
        "password": "password123",
        "role": "FARMER",
        "district": "Purba Bardhaman",
    })
    headers_b = {"Authorization": f"Bearer {reg_b.json()['access_token']}"}

    # Farmer A creates a farm
    farm_a = client_with_db.post("/api/v1/farmer/farms", headers=headers_a, json={
        "name": "Farmer A Farm",
        "district": "Purba Bardhaman",
        "area_acres": 5.0,
    }).json()
    farm_a_id = farm_a["id"]

    # Farmer B attempts to declare supply using Farmer A's farm_id -> Must be REJECTED (HTTP 403)
    hack_res = client_with_db.post("/api/v1/farmer/supply", headers=headers_b, json={
        "farm_id": farm_a_id,
        "commodity_id": 1,
        "quantity_kg": 10000.0,
        "expected_harvest_date": "2026-11-20",
        "quality_grade": "A",
        "status": "PLANNED",
    })
    assert hack_res.status_code == 403
    assert "does not belong to you" in hack_res.json()["detail"]

    # Farmer A declares valid supply
    supply_a = client_with_db.post("/api/v1/farmer/supply", headers=headers_a, json={
        "farm_id": farm_a_id,
        "commodity_id": 1,
        "quantity_kg": 10000.0,
        "expected_harvest_date": "2026-11-20",
        "quality_grade": "A",
        "status": "PLANNED",
    }).json()
    supply_a_id = supply_a["id"]

    # Farmer B attempts to update Farmer A's supply -> Must be 404 (or 403)
    update_hack = client_with_db.patch(f"/api/v1/farmer/supply/{supply_a_id}", headers=headers_b, json={
        "quantity_kg": 50000.0,
    })
    assert update_hack.status_code == 404

    # Farmer B attempts to delete Farmer A's supply -> Must be 404
    delete_hack = client_with_db.delete(f"/api/v1/farmer/supply/{supply_a_id}", headers=headers_b)
    assert delete_hack.status_code == 404

    # Farmer A lists supply -> sees 1 supply
    supplies_a = client_with_db.get("/api/v1/farmer/supply", headers=headers_a).json()
    assert len(supplies_a) == 1
    assert supplies_a[0]["farm_name"] == "Farmer A Farm"
    assert supplies_a[0]["commodity_name"] == "Potato"

    # Farmer B lists supply -> sees 0 supplies
    supplies_b = client_with_db.get("/api/v1/farmer/supply", headers=headers_b).json()
    assert len(supplies_b) == 0


def test_supply_input_validation(client_with_db):
    reg = client_with_db.post("/api/v1/auth/register", json={
        "name": "Validation Farmer",
        "identifier": "valid@farmer.com",
        "password": "password123",
        "role": "FARMER",
        "district": "Purba Bardhaman",
    })
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    farm = client_with_db.post("/api/v1/farmer/farms", headers=headers, json={
        "name": "Validation Farm",
        "district": "Purba Bardhaman",
    }).json()

    # Zero quantity -> 422
    zero_res = client_with_db.post("/api/v1/farmer/supply", headers=headers, json={
        "farm_id": farm["id"],
        "commodity_id": 1,
        "quantity_kg": 0,
        "expected_harvest_date": "2026-11-20",
    })
    assert zero_res.status_code == 422

    # Negative quantity -> 422
    neg_res = client_with_db.post("/api/v1/farmer/supply", headers=headers, json={
        "farm_id": farm["id"],
        "commodity_id": 1,
        "quantity_kg": -500,
        "expected_harvest_date": "2026-11-20",
    })
    assert neg_res.status_code == 422


def test_farmer_partially_sold_quantity_lifecycle(client_with_db):
    """Verify declared vs remaining quantity lifecycle:
    1. Declared harvest initialized.
    2. Partial sell updates remaining quantity and auto-transitions to PARTIALLY_SOLD.
    3. Over-allocation (remaining > declared) is strictly rejected with 400.
    4. Remaining reduced to 0 transitions to SOLD and removes volume from active supply.
    """
    reg = client_with_db.post("/api/v1/auth/register", json={
        "name": "Supply Farmer",
        "identifier": "supply_flow@test.com",
        "password": "password123",
        "role": "FARMER",
        "district": "Hooghly",
    })
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    farm = client_with_db.post("/api/v1/farmer/farms", headers=headers, json={
        "name": "Hooghly Farm",
        "district": "Hooghly",
    }).json()

    # 1. Create supply: 10,000 kg declared
    create_res = client_with_db.post("/api/v1/farmer/supply", headers=headers, json={
        "farm_id": farm["id"],
        "commodity_id": 1,
        "quantity_kg": 10000.0,
        "expected_harvest_date": "2026-11-15",
        "quality_grade": "A",
        "status": "PLANNED",
    })
    assert create_res.status_code == 201
    supply = create_res.json()
    supply_id = supply["id"]
    assert Decimal(str(supply["declared_quantity_kg"])) == Decimal("10000.00")
    assert Decimal(str(supply["remaining_quantity_kg"])) == Decimal("10000.00")
    assert Decimal(str(supply["sold_quantity_kg"])) == Decimal("0")
    assert supply["status"] == "PLANNED"

    # Profile shows 10,000 kg active
    prof = client_with_db.get("/api/v1/farmer/profile", headers=headers).json()
    assert Decimal(str(prof["total_active_supplies_kg"])) == Decimal("10000.00")

    # 2. Reject remaining_quantity_kg > declared_quantity_kg (15,000 > 10,000)
    over_res = client_with_db.patch(f"/api/v1/farmer/supply/{supply_id}", headers=headers, json={
        "remaining_quantity_kg": 15000.0,
    })
    assert over_res.status_code == 400
    assert "cannot exceed declared quantity" in over_res.json()["detail"]

    # 3. Partially sold: 4,000 kg remaining (6,000 sold)
    part_res = client_with_db.patch(f"/api/v1/farmer/supply/{supply_id}", headers=headers, json={
        "remaining_quantity_kg": 4000.0,
    })
    assert part_res.status_code == 200
    part_data = part_res.json()
    assert Decimal(str(part_data["declared_quantity_kg"])) == Decimal("10000.00")
    assert Decimal(str(part_data["remaining_quantity_kg"])) == Decimal("4000.00")
    assert Decimal(str(part_data["sold_quantity_kg"])) == Decimal("6000.00")
    assert part_data["status"] == "PARTIALLY_SOLD"

    # Profile shows active volume is now 4,000 kg, NOT 10,000 kg
    prof_part = client_with_db.get("/api/v1/farmer/profile", headers=headers).json()
    assert Decimal(str(prof_part["total_active_supplies_kg"])) == Decimal("4000.00")

    # 4. Completely sold: remaining 0 kg
    sold_res = client_with_db.patch(f"/api/v1/farmer/supply/{supply_id}", headers=headers, json={
        "remaining_quantity_kg": 0.0,
    })
    assert sold_res.status_code == 200
    sold_data = sold_res.json()
    assert Decimal(str(sold_data["remaining_quantity_kg"])) == Decimal("0")
    assert Decimal(str(sold_data["sold_quantity_kg"])) == Decimal("10000.00")
    assert sold_data["status"] == "SOLD"

    # Profile shows active volume is now 0 kg
    prof_sold = client_with_db.get("/api/v1/farmer/profile", headers=headers).json()
    assert Decimal(str(prof_sold["total_active_supplies_kg"])) == Decimal("0")

