from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.enums import ColdStoreEventType


# Cold Store CRUD schemas
class ColdStoreCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    district: str = Field(..., min_length=2, max_length=100)
    block: Optional[str] = None
    village: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    capacity_kg: Decimal = Field(..., gt=0, description="Capacity must be strictly positive")


class ColdStoreResponse(BaseModel):
    id: int
    operator_id: int
    name: str
    district: str
    block: Optional[str] = None
    village: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    capacity_kg: Decimal
    active: bool
    current_occupancy_kg: Decimal = Decimal(0)
    utilization_percentage: Decimal = Decimal(0)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Inventory Balance schemas
class ColdStoreInventoryResponse(BaseModel):
    id: int
    cold_store_id: int
    commodity_id: int
    commodity_name: Optional[str] = None
    commodity_code: Optional[str] = None
    current_quantity_kg: Decimal
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Event schemas
class ColdStoreEventCreate(BaseModel):
    commodity_id: int
    event_type: ColdStoreEventType
    quantity_kg: Decimal = Field(..., gt=0, description="Event quantity must be strictly greater than 0")
    event_date: date
    reference: Optional[str] = Field(None, max_length=255)


class ColdStoreEventResponse(BaseModel):
    id: int
    cold_store_id: int
    commodity_id: int
    commodity_name: Optional[str] = None
    commodity_code: Optional[str] = None
    event_type: ColdStoreEventType
    quantity_kg: Decimal
    event_date: date
    reference: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Operator Profile schema
class ColdStoreOperatorProfileResponse(BaseModel):
    id: int
    user_id: int
    name: str
    identifier: str
    organization_name: str
    district: str
    address: Optional[str] = None
    phone: Optional[str] = None
    total_stores: int = 0
    total_capacity_kg: Decimal = Decimal(0)
    total_occupancy_kg: Decimal = Decimal(0)
    overall_utilization_percentage: Decimal = Decimal(0)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
