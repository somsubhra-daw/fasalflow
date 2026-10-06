from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.enums import BuyerType, DemandStatus


# =====================================================================
# MARKETS, PRICES & ARRIVALS SCHEMAS
# =====================================================================
class MarketResponse(BaseModel):
    id: int
    name: str
    district: str
    block: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarketPriceResponse(BaseModel):
    id: int
    market_id: int
    market_name: Optional[str] = None
    commodity_id: int
    commodity_name: Optional[str] = None
    commodity_code: Optional[str] = None
    date: date
    min_price_per_kg: Decimal
    modal_price_per_kg: Decimal
    max_price_per_kg: Decimal
    source: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarketArrivalResponse(BaseModel):
    id: int
    market_id: int
    market_name: Optional[str] = None
    commodity_id: int
    commodity_name: Optional[str] = None
    commodity_code: Optional[str] = None
    date: date
    quantity_kg: Decimal
    source: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =====================================================================
# BUYER & DEMAND SCHEMAS
# =====================================================================
class BuyerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    buyer_type: BuyerType = Field(default=BuyerType.WHOLESALER)
    district: str = Field(..., min_length=2, max_length=100)
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    phone: Optional[str] = None


class BuyerResponse(BaseModel):
    id: int
    name: str
    buyer_type: BuyerType
    district: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    phone: Optional[str] = None
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuyerDemandCreate(BaseModel):
    buyer_id: int
    commodity_id: int
    quantity_kg: Decimal = Field(..., gt=0, description="Demand quantity must be > 0")
    required_from: date
    required_until: date
    quality_grade: str = Field(default="A", max_length=20)
    max_price_per_kg: Decimal = Field(..., ge=0, description="Max price cannot be negative")
    status: DemandStatus = Field(default=DemandStatus.ACTIVE)


class BuyerDemandResponse(BaseModel):
    id: int
    buyer_id: int
    buyer_name: Optional[str] = None
    buyer_type: Optional[BuyerType] = None
    commodity_id: int
    commodity_name: Optional[str] = None
    commodity_code: Optional[str] = None
    quantity_kg: Decimal
    required_from: date
    required_until: date
    quality_grade: str
    max_price_per_kg: Decimal
    status: DemandStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
