from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.models import Farmer, Farm, FarmerSupply, Commodity, User
from app.models.enums import SupplyStatus
from app.schemas.farmer import (
    FarmCreate,
    FarmResponse,
    FarmerSupplyCreate,
    FarmerSupplyUpdate,
    FarmerSupplyResponse,
    FarmerProfileResponse,
)


def get_farmer_profile(db: Session, current_user: User) -> FarmerProfileResponse:
    """Retrieve farmer profile with aggregated farms and supply stats in one efficient query."""
    farmer = db.query(Farmer).filter(Farmer.user_id == current_user.id).first()
    if not farmer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer profile not found")

    total_farms = db.query(func.count(Farm.id)).filter(Farm.farmer_id == farmer.id).scalar() or 0

    # Aggregate active supplies (PLANNED, READY, or PARTIALLY_SOLD)
    active_qty = (
        db.query(func.coalesce(func.sum(FarmerSupply.remaining_quantity_kg), Decimal(0)))
        .join(Farm, FarmerSupply.farm_id == Farm.id)
        .filter(Farm.farmer_id == farmer.id, FarmerSupply.status.in_([SupplyStatus.PLANNED, SupplyStatus.READY, SupplyStatus.PARTIALLY_SOLD]))
        .scalar()
    )

    return FarmerProfileResponse(
        id=farmer.id,
        user_id=current_user.id,
        name=current_user.name,
        identifier=current_user.identifier,
        district=farmer.district,
        block=farmer.block,
        village=farmer.village,
        phone=farmer.phone,
        total_farms=total_farms,
        total_active_supplies_kg=Decimal(active_qty),
        created_at=farmer.created_at,
    )


def list_farmer_farms(db: Session, current_user: User) -> List[FarmResponse]:
    """List all farms belonging strictly to the current authenticated farmer."""
    farmer = db.query(Farmer).filter(Farmer.user_id == current_user.id).first()
    if not farmer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer profile not found")

    farms = db.query(Farm).filter(Farm.farmer_id == farmer.id).order_by(Farm.created_at.desc()).all()
    return [FarmResponse.model_validate(f) for f in farms]


def create_farm(db: Session, current_user: User, data: FarmCreate) -> FarmResponse:
    """Create a new farm under the authenticated farmer."""
    farmer = db.query(Farmer).filter(Farmer.user_id == current_user.id).first()
    if not farmer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer profile not found")

    farm = Farm(
        farmer_id=farmer.id,
        name=data.name.strip(),
        district=data.district.strip(),
        block=data.block.strip() if data.block else None,
        village=data.village.strip() if data.village else None,
        latitude=data.latitude,
        longitude=data.longitude,
        area_acres=data.area_acres,
        irrigation_type=data.irrigation_type,
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return FarmResponse.model_validate(farm)


def list_farmer_supplies(
    db: Session,
    current_user: User,
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[SupplyStatus] = None,
) -> List[FarmerSupplyResponse]:
    """List produce supplies for farms owned by the farmer, with eager-loaded commodity & farm details."""
    farmer = db.query(Farmer).filter(Farmer.user_id == current_user.id).first()
    if not farmer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer profile not found")

    query = (
        db.query(FarmerSupply)
        .join(Farm, FarmerSupply.farm_id == Farm.id)
        .options(joinedload(FarmerSupply.farm), joinedload(FarmerSupply.commodity))
        .filter(Farm.farmer_id == farmer.id)
    )

    if status_filter:
        query = query.filter(FarmerSupply.status == status_filter)

    supplies = query.order_by(FarmerSupply.expected_harvest_date.asc()).offset(offset).limit(limit).all()
    return [
        FarmerSupplyResponse(
            id=s.id,
            farm_id=s.farm_id,
            farm_name=s.farm.name if s.farm else None,
            commodity_id=s.commodity_id,
            commodity_name=s.commodity.name if s.commodity else None,
            commodity_code=s.commodity.code if s.commodity else None,
            declared_quantity_kg=s.declared_quantity_kg,
            remaining_quantity_kg=s.remaining_quantity_kg,
            quantity_kg=s.remaining_quantity_kg,
            sold_quantity_kg=s.declared_quantity_kg - s.remaining_quantity_kg,
            expected_harvest_date=s.expected_harvest_date,
            quality_grade=s.quality_grade,
            status=s.status,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in supplies
    ]


def create_farmer_supply(db: Session, current_user: User, data: FarmerSupplyCreate) -> FarmerSupplyResponse:
    """Create supply declaration, rigorously verifying that the farm belongs to the current farmer."""
    farmer = db.query(Farmer).filter(Farmer.user_id == current_user.id).first()
    if not farmer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer profile not found")

    # STRICT OWNERSHIP CHECK: Farm must exist and belong to this farmer
    farm = db.query(Farm).filter(Farm.id == data.farm_id, Farm.farmer_id == farmer.id).first()
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Farm does not exist or does not belong to you",
        )

    # Verify commodity exists
    commodity = db.query(Commodity).filter(Commodity.id == data.commodity_id).first()
    if not commodity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified commodity does not exist")

    supply = FarmerSupply(
        farm_id=farm.id,
        commodity_id=commodity.id,
        declared_quantity_kg=data.quantity_kg,
        remaining_quantity_kg=data.quantity_kg,
        expected_harvest_date=data.expected_harvest_date,
        quality_grade=data.quality_grade.strip(),
        status=data.status,
    )
    db.add(supply)
    db.commit()
    db.refresh(supply)

    return FarmerSupplyResponse(
        id=supply.id,
        farm_id=supply.farm_id,
        farm_name=farm.name,
        commodity_id=supply.commodity_id,
        commodity_name=commodity.name,
        commodity_code=commodity.code,
        declared_quantity_kg=supply.declared_quantity_kg,
        remaining_quantity_kg=supply.remaining_quantity_kg,
        quantity_kg=supply.remaining_quantity_kg,
        sold_quantity_kg=Decimal(0),
        expected_harvest_date=supply.expected_harvest_date,
        quality_grade=supply.quality_grade,
        status=supply.status,
        created_at=supply.created_at,
        updated_at=supply.updated_at,
    )


def update_farmer_supply(
    db: Session,
    current_user: User,
    supply_id: int,
    data: FarmerSupplyUpdate,
) -> FarmerSupplyResponse:
    """Update a supply declaration after verifying ownership."""
    farmer = db.query(Farmer).filter(Farmer.user_id == current_user.id).first()
    if not farmer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer profile not found")

    supply = (
        db.query(FarmerSupply)
        .join(Farm, FarmerSupply.farm_id == Farm.id)
        .options(joinedload(FarmerSupply.farm), joinedload(FarmerSupply.commodity))
        .filter(FarmerSupply.id == supply_id, Farm.farmer_id == farmer.id)
        .first()
    )

    if not supply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supply declaration not found or does not belong to your farms",
        )

    # Validate declared and remaining volume boundaries
    target_declared = data.quantity_kg if data.quantity_kg is not None else supply.declared_quantity_kg
    target_remaining = data.remaining_quantity_kg if data.remaining_quantity_kg is not None else supply.remaining_quantity_kg

    if target_remaining > target_declared:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Remaining quantity ({target_remaining} kg) cannot exceed declared quantity ({target_declared} kg)",
        )
    if target_remaining < Decimal(0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Remaining quantity cannot be negative",
        )

    supply.declared_quantity_kg = target_declared
    supply.remaining_quantity_kg = target_remaining

    if data.expected_harvest_date is not None:
        supply.expected_harvest_date = data.expected_harvest_date
    if data.quality_grade is not None:
        supply.quality_grade = data.quality_grade.strip()

    if data.status is not None:
        supply.status = data.status
        if supply.status == SupplyStatus.SOLD:
            supply.remaining_quantity_kg = Decimal(0)
    else:
        # Automatic state transitions based on remaining quantity
        if supply.remaining_quantity_kg == Decimal(0):
            supply.status = SupplyStatus.SOLD
        elif Decimal(0) < supply.remaining_quantity_kg < supply.declared_quantity_kg:
            if supply.status in (SupplyStatus.PLANNED, SupplyStatus.READY):
                supply.status = SupplyStatus.PARTIALLY_SOLD

    db.commit()
    db.refresh(supply)

    return FarmerSupplyResponse(
        id=supply.id,
        farm_id=supply.farm_id,
        farm_name=supply.farm.name,
        commodity_id=supply.commodity_id,
        commodity_name=supply.commodity.name,
        commodity_code=supply.commodity.code,
        declared_quantity_kg=supply.declared_quantity_kg,
        remaining_quantity_kg=supply.remaining_quantity_kg,
        quantity_kg=supply.remaining_quantity_kg,
        sold_quantity_kg=supply.declared_quantity_kg - supply.remaining_quantity_kg,
        expected_harvest_date=supply.expected_harvest_date,
        quality_grade=supply.quality_grade,
        status=supply.status,
        created_at=supply.created_at,
        updated_at=supply.updated_at,
    )


def delete_farmer_supply(db: Session, current_user: User, supply_id: int) -> None:
    """Delete a supply record after verifying ownership."""
    farmer = db.query(Farmer).filter(Farmer.user_id == current_user.id).first()
    if not farmer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farmer profile not found")

    supply = (
        db.query(FarmerSupply)
        .join(Farm, FarmerSupply.farm_id == Farm.id)
        .filter(FarmerSupply.id == supply_id, Farm.farmer_id == farmer.id)
        .first()
    )

    if not supply:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supply declaration not found or does not belong to your farms",
        )

    db.delete(supply)
    db.commit()
