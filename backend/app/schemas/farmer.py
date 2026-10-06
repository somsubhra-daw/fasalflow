from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.enums import SupplyStatus


# Farm Schemas
class FarmCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    district: str = Field(..., min_length=2, max_length=100)
    block: Optional[str] = None
    village: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    area_acres: Optional[Decimal] = Field(None, gt=0)
    irrigation_type: Optional[str] = None


class FarmResponse(BaseModel):
    id: int
    farmer_id: int
    name: str
    district: str
    block: Optional[str] = None
    village: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    area_acres: Optional[Decimal] = None
    irrigation_type: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Commodity Minimal Schema for nested display
class CommoditySummary(BaseModel):
    id: int
    name: str
    code: str
    default_unit: str

    model_config = ConfigDict(from_attributes=True)


# Farmer Supply Schemas
class FarmerSupplyCreate(BaseModel):
    farm_id: int
    commodity_id: int
    quantity_kg: Decimal = Field(..., gt=0, description="Quantity in kg must be > 0")
    expected_harvest_date: date
    quality_grade: str = Field(default="A", max_length=20)
    status: SupplyStatus = Field(default=SupplyStatus.PLANNED)


class FarmerSupplyUpdate(BaseModel):
    quantity_kg: Optional[Decimal] = Field(None, gt=0)
    expected_harvest_date: Optional[date] = None
    quality_grade: Optional[str] = Field(None, max_length=20)
    status: Optional[SupplyStatus] = None


class FarmerSupplyResponse(BaseModel):
    id: int
    farm_id: int
    farm_name: Optional[str] = None
    commodity_id: int
    commodity_name: Optional[str] = None
    commodity_code: Optional[str] = None
    quantity_kg: Decimal
    expected_harvest_date: date
    quality_grade: str
    status: SupplyStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Farmer Profile Schema
class FarmerProfileResponse(BaseModel):
    id: int
    user_id: int
    name: str
    identifier: str
    district: str
    block: Optional[str] = None
    village: Optional[str] = None
    phone: Optional[str] = None
    total_farms: int = 0
    total_active_supplies_kg: Decimal = Decimal(0)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
