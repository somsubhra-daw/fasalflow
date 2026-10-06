from datetime import date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.models import Market, MarketPrice, MarketArrival, Buyer, BuyerDemand, Commodity
from app.models.enums import DemandStatus
from app.schemas.market import (
    MarketResponse,
    MarketPriceResponse,
    MarketArrivalResponse,
    BuyerCreate,
    BuyerResponse,
    BuyerDemandCreate,
    BuyerDemandResponse,
)


# =====================================================================
# MARKETS, PRICES & ARRIVALS SERVICE
# =====================================================================
def list_markets(
    db: Session,
    district: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[MarketResponse]:
    """List operational agricultural markets with optional district filter."""
    query = db.query(Market).filter(Market.active == True)
    if district:
        query = query.filter(Market.district.ilike(f"%{district.strip()}%"))
    markets = query.order_by(Market.name.asc()).offset(offset).limit(limit).all()
    return [MarketResponse.model_validate(m) for m in markets]


def get_market_by_id(db: Session, market_id: int) -> MarketResponse:
    """Get single market by ID."""
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")
    return MarketResponse.model_validate(market)


def list_market_prices(
    db: Session,
    market_id: int,
    commodity_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[MarketPriceResponse]:
    """Retrieve historical market prices with bounded filtering and joined relations."""
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")

    query = (
        db.query(MarketPrice)
        .options(joinedload(MarketPrice.market), joinedload(MarketPrice.commodity))
        .filter(MarketPrice.market_id == market_id)
    )

    if commodity_id:
        query = query.filter(MarketPrice.commodity_id == commodity_id)
    if date_from:
        query = query.filter(MarketPrice.date >= date_from)
    if date_to:
        query = query.filter(MarketPrice.date <= date_to)

    prices = query.order_by(MarketPrice.date.desc()).offset(offset).limit(limit).all()

    return [
        MarketPriceResponse(
            id=p.id,
            market_id=p.market_id,
            market_name=p.market.name if p.market else None,
            commodity_id=p.commodity_id,
            commodity_name=p.commodity.name if p.commodity else None,
            commodity_code=p.commodity.code if p.commodity else None,
            date=p.date,
            min_price_per_kg=p.min_price_per_kg,
            modal_price_per_kg=p.modal_price_per_kg,
            max_price_per_kg=p.max_price_per_kg,
            source=p.source,
            created_at=p.created_at,
        )
        for p in prices
    ]


def list_market_arrivals(
    db: Session,
    market_id: int,
    commodity_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[MarketArrivalResponse]:
    """Retrieve historical market arrivals with bounded filtering and joined relations."""
    market = db.query(Market).filter(Market.id == market_id).first()
    if not market:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Market not found")

    query = (
        db.query(MarketArrival)
        .options(joinedload(MarketArrival.market), joinedload(MarketArrival.commodity))
        .filter(MarketArrival.market_id == market_id)
    )

    if commodity_id:
        query = query.filter(MarketArrival.commodity_id == commodity_id)
    if date_from:
        query = query.filter(MarketArrival.date >= date_from)
    if date_to:
        query = query.filter(MarketArrival.date <= date_to)

    arrivals = query.order_by(MarketArrival.date.desc()).offset(offset).limit(limit).all()

    return [
        MarketArrivalResponse(
            id=a.id,
            market_id=a.market_id,
            market_name=a.market.name if a.market else None,
            commodity_id=a.commodity_id,
            commodity_name=a.commodity.name if a.commodity else None,
            commodity_code=a.commodity.code if a.commodity else None,
            date=a.date,
            quantity_kg=a.quantity_kg,
            source=a.source,
            created_at=a.created_at,
        )
        for a in arrivals
    ]


# =====================================================================
# BUYER & DEMAND SERVICE
# =====================================================================
def create_buyer(db: Session, data: BuyerCreate) -> BuyerResponse:
    """Create supporting buyer record."""
    buyer = Buyer(
        name=data.name.strip(),
        buyer_type=data.buyer_type,
        district=data.district.strip(),
        latitude=data.latitude,
        longitude=data.longitude,
        phone=data.phone.strip() if data.phone else None,
        active=True,
    )
    db.add(buyer)
    db.commit()
    db.refresh(buyer)
    return BuyerResponse.model_validate(buyer)


def list_buyers(
    db: Session,
    district: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[BuyerResponse]:
    """List buyers with optional district filter."""
    query = db.query(Buyer).filter(Buyer.active == True)
    if district:
        query = query.filter(Buyer.district.ilike(f"%{district.strip()}%"))
    buyers = query.order_by(Buyer.name.asc()).offset(offset).limit(limit).all()
    return [BuyerResponse.model_validate(b) for b in buyers]


def create_buyer_demand(db: Session, data: BuyerDemandCreate) -> BuyerDemandResponse:
    """Register buyer demand with validation."""
    buyer = db.query(Buyer).filter(Buyer.id == data.buyer_id).first()
    if not buyer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyer not found")

    commodity = db.query(Commodity).filter(Commodity.id == data.commodity_id).first()
    if not commodity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commodity not found")

    if data.required_until < data.required_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="required_until cannot be earlier than required_from",
        )

    if data.quantity_kg <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Demand quantity must be greater than 0",
        )

    demand = BuyerDemand(
        buyer_id=data.buyer_id,
        commodity_id=data.commodity_id,
        quantity_kg=data.quantity_kg,
        required_from=data.required_from,
        required_until=data.required_until,
        quality_grade=data.quality_grade.strip(),
        max_price_per_kg=data.max_price_per_kg,
        status=data.status,
    )
    db.add(demand)
    db.commit()
    db.refresh(demand)

    return BuyerDemandResponse(
        id=demand.id,
        buyer_id=demand.buyer_id,
        buyer_name=buyer.name,
        buyer_type=buyer.buyer_type,
        commodity_id=demand.commodity_id,
        commodity_name=commodity.name,
        commodity_code=commodity.code,
        quantity_kg=demand.quantity_kg,
        required_from=demand.required_from,
        required_until=demand.required_until,
        quality_grade=demand.quality_grade,
        max_price_per_kg=demand.max_price_per_kg,
        status=demand.status,
        created_at=demand.created_at,
    )


def list_buyer_demands(
    db: Session,
    commodity_id: Optional[int] = None,
    status_filter: Optional[DemandStatus] = None,
    date_window: Optional[date] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[BuyerDemandResponse]:
    """List buyer demands with efficient joined loading and optional filtering."""
    query = (
        db.query(BuyerDemand)
        .options(joinedload(BuyerDemand.buyer), joinedload(BuyerDemand.commodity))
    )

    if commodity_id:
        query = query.filter(BuyerDemand.commodity_id == commodity_id)
    if status_filter:
        query = query.filter(BuyerDemand.status == status_filter)
    if date_window:
        query = query.filter(
            BuyerDemand.required_from <= date_window,
            BuyerDemand.required_until >= date_window,
        )

    demands = query.order_by(BuyerDemand.required_from.asc()).offset(offset).limit(limit).all()

    return [
        BuyerDemandResponse(
            id=d.id,
            buyer_id=d.buyer_id,
            buyer_name=d.buyer.name if d.buyer else None,
            buyer_type=d.buyer.buyer_type if d.buyer else None,
            commodity_id=d.commodity_id,
            commodity_name=d.commodity.name if d.commodity else None,
            commodity_code=d.commodity.code if d.commodity else None,
            quantity_kg=d.quantity_kg,
            required_from=d.required_from,
            required_until=d.required_until,
            quality_grade=d.quality_grade,
            max_price_per_kg=d.max_price_per_kg,
            status=d.status,
            created_at=d.created_at,
        )
        for d in demands
    ]
