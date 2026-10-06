from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.db.session import Base
from app.models import (
    User,
    UserRole,
    Commodity,
    CommodityCode,
    Farmer,
    Farm,
    FarmerSupply,
    SupplyStatus,
    ColdStoreOperator,
    ColdStore,
    ColdStoreInventory,
    ColdStoreEvent,
    ColdStoreEventType,
    Buyer,
    BuyerType,
    BuyerDemand,
    DemandStatus,
    Market,
    MarketPrice,
    MarketArrival,
)


@pytest.fixture
def db_session():
    """Create fresh in-memory database for testing model schema & constraints."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


def test_user_and_farmer_relationship(db_session):
    user = User(
        name="Ramesh Kumar",
        identifier="ramesh@example.com",
        password_hash="hashed_pw_dummy",
        role=UserRole.FARMER,
    )
    db_session.add(user)
    db_session.commit()

    farmer = Farmer(
        user_id=user.id,
        district="Purba Bardhaman",
        block="Burdwan-I",
        village="Rayna",
    )
    db_session.add(farmer)
    db_session.commit()

    assert user.farmer_profile.id == farmer.id
    assert farmer.user.name == "Ramesh Kumar"


def test_user_unique_identifier_constraint(db_session):
    u1 = User(
        name="Farmer 1",
        identifier="duplicate@example.com",
        password_hash="pw1",
        role=UserRole.FARMER,
    )
    db_session.add(u1)
    db_session.commit()

    u2 = User(
        name="Farmer 2",
        identifier="duplicate@example.com",
        password_hash="pw2",
        role=UserRole.FARMER,
    )
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_commodity_and_supply(db_session):
    user = User(
        name="Farmer Potato",
        identifier="potato_farmer@example.com",
        password_hash="hash",
        role=UserRole.FARMER,
    )
    db_session.add(user)
    db_session.flush()

    farmer = Farmer(user_id=user.id, district="Purba Bardhaman")
    db_session.add(farmer)
    db_session.flush()

    farm = Farm(farmer_id=farmer.id, name="Green Acres", district="Purba Bardhaman", area_acres=Decimal("5.5"))
    db_session.add(farm)

    commodity = Commodity(name="Potato", code=CommodityCode.POTATO.value, default_unit="kg")
    db_session.add(commodity)
    db_session.flush()

    supply = FarmerSupply(
        farm_id=farm.id,
        commodity_id=commodity.id,
        quantity_kg=Decimal("15000.00"),
        expected_harvest_date=date(2026, 11, 15),
        quality_grade="A",
        status=SupplyStatus.PLANNED,
    )
    db_session.add(supply)
    db_session.commit()

    assert supply.id is not None
    assert supply.commodity.name == "Potato"
    assert supply.farm.name == "Green Acres"


def test_cold_store_inventory_and_events(db_session):
    user = User(
        name="Cold Store Owner",
        identifier="operator@example.com",
        password_hash="hash",
        role=UserRole.COLD_STORE_OPERATOR,
    )
    db_session.add(user)
    db_session.flush()

    operator = ColdStoreOperator(
        user_id=user.id,
        organization_name="Bardhaman Agro Cold Storage",
        district="Purba Bardhaman",
    )
    db_session.add(operator)
    db_session.flush()

    cs = ColdStore(
        operator_id=operator.id,
        name="Burdwan Unit 1",
        district="Purba Bardhaman",
        capacity_kg=Decimal("5000000.00"),
    )
    db_session.add(cs)

    commodity = Commodity(name="Potato", code="POTATO", default_unit="kg")
    db_session.add(commodity)
    db_session.flush()

    inv = ColdStoreInventory(
        cold_store_id=cs.id,
        commodity_id=commodity.id,
        current_quantity_kg=Decimal("2000000.00"),
    )
    db_session.add(inv)

    event = ColdStoreEvent(
        cold_store_id=cs.id,
        commodity_id=commodity.id,
        event_type=ColdStoreEventType.LOADING,
        quantity_kg=Decimal("50000.00"),
        event_date=date(2026, 10, 5),
        reference="Lot #401",
    )
    db_session.add(event)
    db_session.commit()

    assert cs.inventories[0].current_quantity_kg == Decimal("2000000.00")
    assert cs.events[0].event_type == ColdStoreEventType.LOADING


def test_market_price_constraints(db_session):
    commodity = Commodity(name="Potato", code="POTATO", default_unit="kg")
    db_session.add(commodity)
    market = Market(name="Burdwan Sadar Market", district="Purba Bardhaman")
    db_session.add(market)
    db_session.flush()

    # Valid price
    price = MarketPrice(
        market_id=market.id,
        commodity_id=commodity.id,
        date=date(2026, 10, 5),
        min_price_per_kg=Decimal("18.00"),
        modal_price_per_kg=Decimal("20.50"),
        max_price_per_kg=Decimal("22.00"),
        source="synthetic",
    )
    db_session.add(price)
    db_session.commit()

    assert price.id is not None
