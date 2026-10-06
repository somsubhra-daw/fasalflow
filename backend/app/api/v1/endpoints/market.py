from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.market import (
    MarketResponse,
    MarketPriceResponse,
    MarketArrivalResponse,
    BuyerCreate,
    BuyerResponse,
    BuyerDemandCreate,
    BuyerDemandResponse,
)
from app.services.market import (
    list_markets,
    get_market_by_id,
    list_market_prices,
    list_market_arrivals,
    create_buyer,
    list_buyers,
    create_buyer_demand,
    list_buyer_demands,
)

market_router = APIRouter(prefix="/markets", tags=["Markets"])
buyer_router = APIRouter(prefix="/buyers", tags=["Buyers & Demand"])


# =====================================================================
# MARKET ENDPOINTS
# =====================================================================
@market_router.get("", response_model=List[MarketResponse])
def get_markets(
    district: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> List[MarketResponse]:
    """List operational agricultural mandis/markets."""
    return list_markets(db=db, district=district, limit=limit, offset=offset)


@market_router.get("/{id}", response_model=MarketResponse)
def get_market(
    id: int,
    db: Session = Depends(get_db),
) -> MarketResponse:
    """Get market details by ID."""
    return get_market_by_id(db=db, market_id=id)


@market_router.get("/{id}/prices", response_model=List[MarketPriceResponse])
def get_prices(
    id: int,
    commodity_id: Optional[int] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> List[MarketPriceResponse]:
    """Retrieve historical market price recordings with bounded filters."""
    return list_market_prices(
        db=db,
        market_id=id,
        commodity_id=commodity_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@market_router.get("/{id}/arrivals", response_model=List[MarketArrivalResponse])
def get_arrivals(
    id: int,
    commodity_id: Optional[int] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> List[MarketArrivalResponse]:
    """Retrieve historical mandi arrivals with bounded filters."""
    return list_market_arrivals(
        db=db,
        market_id=id,
        commodity_id=commodity_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


# =====================================================================
# BUYER & DEMAND ENDPOINTS
# =====================================================================
@buyer_router.get("", response_model=List[BuyerResponse])
def get_buyers(
    district: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> List[BuyerResponse]:
    """List registered wholesale/institutional buyers."""
    return list_buyers(db=db, district=district, limit=limit, offset=offset)


@buyer_router.post("", response_model=BuyerResponse, status_code=status.HTTP_201_CREATED)
def add_buyer(
    data: BuyerCreate,
    db: Session = Depends(get_db),
) -> BuyerResponse:
    """Create supporting buyer entity."""
    return create_buyer(db=db, data=data)


@buyer_router.get("/demand", response_model=List[BuyerDemandResponse])
def get_demands(
    commodity_id: Optional[int] = Query(default=None),
    date_window: Optional[date] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> List[BuyerDemandResponse]:
    """List buyer purchase demands."""
    return list_buyer_demands(
        db=db,
        commodity_id=commodity_id,
        date_window=date_window,
        limit=limit,
        offset=offset,
    )


@buyer_router.post("/demand", response_model=BuyerDemandResponse, status_code=status.HTTP_201_CREATED)
def add_demand(
    data: BuyerDemandCreate,
    db: Session = Depends(get_db),
) -> BuyerDemandResponse:
    """Register buyer demand."""
    return create_buyer_demand(db=db, data=data)
