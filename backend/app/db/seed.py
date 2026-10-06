from datetime import date, timedelta
from decimal import Decimal
import logging
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.core.security import hash_password
from app.models.enums import (
    UserRole,
    CommodityCode,
    SupplyStatus,
    BuyerType,
    DemandStatus,
    ColdStoreEventType,
)
from app.models.models import (
    User,
    Commodity,
    Farmer,
    Farm,
    FarmerSupply,
    ColdStoreOperator,
    ColdStore,
    ColdStoreInventory,
    ColdStoreEvent,
    Buyer,
    BuyerDemand,
    Market,
    MarketPrice,
    MarketArrival,
)

logger = logging.getLogger("fasalflow.seed")


def seed_database(db: Session) -> dict[str, int]:
    """Idempotently seed realistic development data for Purba Bardhaman pilot."""
    stats = {}

    # 1. Commodities
    potato = db.query(Commodity).filter(Commodity.code == CommodityCode.POTATO.value).first()
    if not potato:
        potato = Commodity(name="Potato", code=CommodityCode.POTATO.value, default_unit="kg")
        db.add(potato)
        db.flush()
    stats["commodities"] = 1

    # 2. Markets (Purba Bardhaman)
    markets_data = [
        {"name": "Memari Regulated Market", "district": "Purba Bardhaman", "block": "Memari-I"},
        {"name": "Burdwan Sadar Market", "district": "Purba Bardhaman", "block": "Burdwan-I"},
        {"name": "Kalna Krishi Mandi", "district": "Purba Bardhaman", "block": "Kalna-I"},
        {"name": "Katwa Sub-Divisional Market", "district": "Purba Bardhaman", "block": "Katwa"},
    ]
    created_markets = []
    for m in markets_data:
        market = db.query(Market).filter(Market.name == m["name"]).first()
        if not market:
            market = Market(
                name=m["name"],
                district=m["district"],
                block=m["block"],
                active=True,
            )
            db.add(market)
            db.flush()
        created_markets.append(market)
    stats["markets"] = len(created_markets)

    # 3. Market Prices & Arrivals (Last 14 days)
    today = date.today()
    prices_count = 0
    arrivals_count = 0
    for market in created_markets:
        for day_back in range(14, -1, -1):
            curr_date = today - timedelta(days=day_back)
            # Check price exists
            existing_price = (
                db.query(MarketPrice)
                .filter(MarketPrice.market_id == market.id, MarketPrice.date == curr_date)
                .first()
            )
            if not existing_price:
                # Modal price between 19.00 and 23.00
                modal = Decimal("20.00") + Decimal((day_back * 3 + market.id * 2) % 7) * Decimal("0.50")
                min_p = modal - Decimal("2.00")
                max_p = modal + Decimal("2.50")
                db.add(
                    MarketPrice(
                        market_id=market.id,
                        commodity_id=potato.id,
                        date=curr_date,
                        min_price_per_kg=min_p,
                        modal_price_per_kg=modal,
                        max_price_per_kg=max_p,
                        source="synthetic",
                    )
                )
                prices_count += 1

            existing_arrival = (
                db.query(MarketArrival)
                .filter(MarketArrival.market_id == market.id, MarketArrival.date == curr_date)
                .first()
            )
            if not existing_arrival:
                qty = Decimal("40000.00") + Decimal((day_back * 5000 + market.id * 10000) % 50000)
                db.add(
                    MarketArrival(
                        market_id=market.id,
                        commodity_id=potato.id,
                        date=curr_date,
                        quantity_kg=qty,
                        source="synthetic",
                    )
                )
                arrivals_count += 1
    stats["market_prices"] = prices_count
    stats["market_arrivals"] = arrivals_count

    # 4. Institutional & Wholesale Buyers
    buyers_data = [
        {"name": "Bengal Food Processing Ltd", "type": BuyerType.PROCESSOR, "district": "Purba Bardhaman"},
        {"name": "Damodar Valley Agri Trade", "type": BuyerType.WHOLESALER, "district": "Purba Bardhaman"},
        {"name": "Kolkata Metro Fresh Chain", "type": BuyerType.RETAILER, "district": "Kolkata"},
        {"name": "Eastern Agro Exports Corp", "type": BuyerType.INSTITUTION, "district": "Howrah"},
    ]
    created_buyers = []
    for b in buyers_data:
        buyer = db.query(Buyer).filter(Buyer.name == b["name"]).first()
        if not buyer:
            buyer = Buyer(
                name=b["name"],
                buyer_type=b["type"],
                district=b["district"],
                active=True,
            )
            db.add(buyer)
            db.flush()
        created_buyers.append(buyer)
    stats["buyers"] = len(created_buyers)

    # 5. Buyer Demands (Active windows covering current/upcoming dates)
    demands_count = 0
    for idx, buyer in enumerate(created_buyers):
        existing_demand = db.query(BuyerDemand).filter(BuyerDemand.buyer_id == buyer.id).first()
        if not existing_demand:
            db.add(
                BuyerDemand(
                    buyer_id=buyer.id,
                    commodity_id=potato.id,
                    quantity_kg=Decimal(50000 + idx * 25000),
                    required_from=today,
                    required_until=today + timedelta(days=14),
                    quality_grade="A",
                    max_price_per_kg=Decimal("22.50") + Decimal(idx),
                    status=DemandStatus.ACTIVE,
                )
            )
            demands_count += 1
    stats["buyer_demands"] = demands_count

    # 6. Cold Store Operators & Facilities
    op_user = db.query(User).filter(User.identifier == "operator@bardhaman-cold.com").first()
    if not op_user:
        op_user = User(
            name="Ratan Sen",
            identifier="operator@bardhaman-cold.com",
            password_hash=hash_password("password123"),
            role=UserRole.COLD_STORE_OPERATOR,
            is_active=True,
        )
        db.add(op_user)
        db.flush()

        operator = ColdStoreOperator(
            user_id=op_user.id,
            organization_name="Bardhaman Kisan Cold Storage Pvt Ltd",
            district="Purba Bardhaman",
            phone="9830012345",
        )
        db.add(operator)
        db.flush()

        # 2 cold storage facilities
        cs1 = ColdStore(
            operator_id=operator.id,
            name="Memari Unit 1 Cold Storage",
            district="Purba Bardhaman",
            block="Memari-I",
            capacity_kg=Decimal("10000000.00"),  # 10,000 MT
            active=True,
        )
        cs2 = ColdStore(
            operator_id=operator.id,
            name="Galsi Facility 2",
            district="Purba Bardhaman",
            block="Galsi-II",
            capacity_kg=Decimal("8000000.00"),   # 8,000 MT
            active=True,
        )
        db.add_all([cs1, cs2])
        db.flush()

        # Initial inventory balance & loading event for CS1 (e.g. 6,500,000 kg loaded = 65% capacity)
        inv1 = ColdStoreInventory(
            cold_store_id=cs1.id,
            commodity_id=potato.id,
            current_quantity_kg=Decimal("6500000.00"),
        )
        ev1 = ColdStoreEvent(
            cold_store_id=cs1.id,
            commodity_id=potato.id,
            event_type=ColdStoreEventType.LOADING,
            quantity_kg=Decimal("6500000.00"),
            event_date=today - timedelta(days=20),
            reference="Initial Season Stocking",
        )
        # Release event (500,000 kg released yesterday)
        inv1.current_quantity_kg = Decimal("6000000.00")
        ev2 = ColdStoreEvent(
            cold_store_id=cs1.id,
            commodity_id=potato.id,
            event_type=ColdStoreEventType.RELEASE,
            quantity_kg=Decimal("500000.00"),
            event_date=today - timedelta(days=1),
            reference="Dispatched to Kolkata Mandi",
        )
        db.add_all([inv1, ev1, ev2])

        # CS2 inventory: 4,000,000 kg (50% capacity)
        inv2 = ColdStoreInventory(
            cold_store_id=cs2.id,
            commodity_id=potato.id,
            current_quantity_kg=Decimal("4000000.00"),
        )
        ev3 = ColdStoreEvent(
            cold_store_id=cs2.id,
            commodity_id=potato.id,
            event_type=ColdStoreEventType.LOADING,
            quantity_kg=Decimal("4000000.00"),
            event_date=today - timedelta(days=15),
            reference="Pre-season Farmer Storage Batch 1",
        )
        db.add_all([inv2, ev3])
    stats["cold_stores"] = 2

    # 7. Sample Farmers, Farms & Supplies
    farmers_data = [
        {"name": "Anil Mahato", "email": "anil.mahato@fasalflow.in", "village": "Rayna", "block": "Rayna-I", "acres": 6.5, "qty": 35000},
        {"name": "Bikash Ghosh", "email": "bikash.ghosh@fasalflow.in", "village": "Bagila", "block": "Memari-I", "acres": 10.0, "qty": 60000},
        {"name": "Sunil Murmu", "email": "sunil.murmu@fasalflow.in", "village": "Bhatar", "block": "Bhatar", "acres": 4.0, "qty": 20000},
    ]
    for f_info in farmers_data:
        f_user = db.query(User).filter(User.identifier == f_info["email"]).first()
        if not f_user:
            f_user = User(
                name=f_info["name"],
                identifier=f_info["email"],
                password_hash=hash_password("password123"),
                role=UserRole.FARMER,
                is_active=True,
            )
            db.add(f_user)
            db.flush()

            farmer = Farmer(
                user_id=f_user.id,
                district="Purba Bardhaman",
                block=f_info["block"],
                village=f_info["village"],
            )
            db.add(farmer)
            db.flush()

            farm = Farm(
                farmer_id=farmer.id,
                name=f"{f_info['village']} Agri Field",
                district="Purba Bardhaman",
                block=f_info["block"],
                village=f_info["village"],
                area_acres=Decimal(str(f_info["acres"])),
            )
            db.add(farm)
            db.flush()

            # Declare supply for harvest coming in 5-10 days
            supply = FarmerSupply(
                farm_id=farm.id,
                commodity_id=potato.id,
                quantity_kg=Decimal(str(f_info["qty"])),
                expected_harvest_date=today + timedelta(days=7),
                quality_grade="A",
                status=SupplyStatus.PLANNED,
            )
            db.add(supply)
    stats["farmers"] = len(farmers_data)

    db.commit()
    logger.info("Database seeding completed successfully: %s", stats)
    return stats


if __name__ == "__main__":
    from app.db.session import SessionLocal
    with SessionLocal() as db_session:
        seed_database(db_session)
