from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.models import (
    ColdStoreOperator,
    ColdStore,
    ColdStoreInventory,
    ColdStoreEvent,
    Commodity,
    User,
)
from app.models.enums import ColdStoreEventType
from app.schemas.cold_store import (
    ColdStoreCreate,
    ColdStoreResponse,
    ColdStoreInventoryResponse,
    ColdStoreEventCreate,
    ColdStoreEventResponse,
    ColdStoreOperatorProfileResponse,
)


def get_operator_profile(db: Session, current_user: User) -> ColdStoreOperatorProfileResponse:
    """Retrieve cold store operator profile with aggregated capacities and current occupancies."""
    operator = db.query(ColdStoreOperator).filter(ColdStoreOperator.user_id == current_user.id).first()
    if not operator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator profile not found")

    # Aggregated stats
    stores_query = db.query(ColdStore).filter(ColdStore.operator_id == operator.id).all()
    total_stores = len(stores_query)
    total_capacity = sum((s.capacity_kg for s in stores_query), Decimal(0))

    store_ids = [s.id for s in stores_query]
    total_occupancy = Decimal(0)
    if store_ids:
        total_occupancy = (
            db.query(func.coalesce(func.sum(ColdStoreInventory.current_quantity_kg), Decimal(0)))
            .filter(ColdStoreInventory.cold_store_id.in_(store_ids))
            .scalar()
            or Decimal(0)
        )

    utilization = Decimal(0)
    if total_capacity > 0:
        utilization = round((Decimal(total_occupancy) / Decimal(total_capacity)) * 100, 2)

    return ColdStoreOperatorProfileResponse(
        id=operator.id,
        user_id=current_user.id,
        name=current_user.name,
        identifier=current_user.identifier,
        organization_name=operator.organization_name,
        district=operator.district,
        address=operator.address,
        phone=operator.phone,
        total_stores=total_stores,
        total_capacity_kg=total_capacity,
        total_occupancy_kg=Decimal(total_occupancy),
        overall_utilization_percentage=utilization,
        created_at=operator.created_at,
    )


def list_operator_stores(db: Session, current_user: User) -> List[ColdStoreResponse]:
    """List all cold storage facilities managed strictly by the current operator with occupancy metrics."""
    operator = db.query(ColdStoreOperator).filter(ColdStoreOperator.user_id == current_user.id).first()
    if not operator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator profile not found")

    stores = db.query(ColdStore).filter(ColdStore.operator_id == operator.id).all()
    result = []
    for s in stores:
        occupancy = (
            db.query(func.coalesce(func.sum(ColdStoreInventory.current_quantity_kg), Decimal(0)))
            .filter(ColdStoreInventory.cold_store_id == s.id)
            .scalar()
            or Decimal(0)
        )
        util_pct = Decimal(0)
        if s.capacity_kg > 0:
            util_pct = round((Decimal(occupancy) / Decimal(s.capacity_kg)) * 100, 2)

        result.append(
            ColdStoreResponse(
                id=s.id,
                operator_id=s.operator_id,
                name=s.name,
                district=s.district,
                block=s.block,
                village=s.village,
                address=s.address,
                latitude=s.latitude,
                longitude=s.longitude,
                capacity_kg=s.capacity_kg,
                active=s.active,
                current_occupancy_kg=Decimal(occupancy),
                utilization_percentage=util_pct,
                created_at=s.created_at,
            )
        )
    return result


def create_cold_store(db: Session, current_user: User, data: ColdStoreCreate) -> ColdStoreResponse:
    """Register a new cold store under the authenticated operator."""
    operator = db.query(ColdStoreOperator).filter(ColdStoreOperator.user_id == current_user.id).first()
    if not operator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator profile not found")

    if data.capacity_kg <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Capacity must be strictly positive")

    store = ColdStore(
        operator_id=operator.id,
        name=data.name.strip(),
        district=data.district.strip(),
        block=data.block.strip() if data.block else None,
        village=data.village.strip() if data.village else None,
        address=data.address.strip() if data.address else None,
        latitude=data.latitude,
        longitude=data.longitude,
        capacity_kg=data.capacity_kg,
        active=True,
    )
    db.add(store)
    db.commit()
    db.refresh(store)

    return ColdStoreResponse(
        id=store.id,
        operator_id=store.operator_id,
        name=store.name,
        district=store.district,
        block=store.block,
        village=store.village,
        address=store.address,
        latitude=store.latitude,
        longitude=store.longitude,
        capacity_kg=store.capacity_kg,
        active=store.active,
        current_occupancy_kg=Decimal(0),
        utilization_percentage=Decimal(0),
        created_at=store.created_at,
    )


def get_cold_store_by_id(db: Session, current_user: User, store_id: int) -> ColdStoreResponse:
    """Retrieve details of a cold store, verifying operator ownership."""
    operator = db.query(ColdStoreOperator).filter(ColdStoreOperator.user_id == current_user.id).first()
    if not operator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator profile not found")

    store = db.query(ColdStore).filter(ColdStore.id == store_id, ColdStore.operator_id == operator.id).first()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cold store not found or access forbidden")

    occupancy = (
        db.query(func.coalesce(func.sum(ColdStoreInventory.current_quantity_kg), Decimal(0)))
        .filter(ColdStoreInventory.cold_store_id == store.id)
        .scalar()
        or Decimal(0)
    )
    util_pct = Decimal(0)
    if store.capacity_kg > 0:
        util_pct = round((Decimal(occupancy) / Decimal(store.capacity_kg)) * 100, 2)

    return ColdStoreResponse(
        id=store.id,
        operator_id=store.operator_id,
        name=store.name,
        district=store.district,
        block=store.block,
        village=store.village,
        address=store.address,
        latitude=store.latitude,
        longitude=store.longitude,
        capacity_kg=store.capacity_kg,
        active=store.active,
        current_occupancy_kg=Decimal(occupancy),
        utilization_percentage=util_pct,
        created_at=store.created_at,
    )


def get_cold_store_inventory(db: Session, current_user: User, store_id: int) -> List[ColdStoreInventoryResponse]:
    """Retrieve current stock balances per commodity for a cold store."""
    operator = db.query(ColdStoreOperator).filter(ColdStoreOperator.user_id == current_user.id).first()
    if not operator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator profile not found")

    store = db.query(ColdStore).filter(ColdStore.id == store_id, ColdStore.operator_id == operator.id).first()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cold store not found or access forbidden")

    inventories = (
        db.query(ColdStoreInventory)
        .options(joinedload(ColdStoreInventory.commodity))
        .filter(ColdStoreInventory.cold_store_id == store.id)
        .all()
    )

    return [
        ColdStoreInventoryResponse(
            id=inv.id,
            cold_store_id=inv.cold_store_id,
            commodity_id=inv.commodity_id,
            commodity_name=inv.commodity.name if inv.commodity else None,
            commodity_code=inv.commodity.code if inv.commodity else None,
            current_quantity_kg=inv.current_quantity_kg,
            updated_at=inv.updated_at,
        )
        for inv in inventories
    ]


def list_cold_store_events(
    db: Session,
    current_user: User,
    store_id: int,
    limit: int = 50,
    offset: int = 0,
) -> List[ColdStoreEventResponse]:
    """List historical immutable inventory events for a cold store."""
    operator = db.query(ColdStoreOperator).filter(ColdStoreOperator.user_id == current_user.id).first()
    if not operator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator profile not found")

    store = db.query(ColdStore).filter(ColdStore.id == store_id, ColdStore.operator_id == operator.id).first()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cold store not found or access forbidden")

    events = (
        db.query(ColdStoreEvent)
        .filter(ColdStoreEvent.cold_store_id == store.id)
        .order_by(ColdStoreEvent.event_date.desc(), ColdStoreEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Preload commodity names
    commodity_map = {c.id: c for c in db.query(Commodity).all()}

    return [
        ColdStoreEventResponse(
            id=e.id,
            cold_store_id=e.cold_store_id,
            commodity_id=e.commodity_id,
            commodity_name=commodity_map.get(e.commodity_id).name if e.commodity_id in commodity_map else None,
            commodity_code=commodity_map.get(e.commodity_id).code if e.commodity_id in commodity_map else None,
            event_type=e.event_type,
            quantity_kg=e.quantity_kg,
            event_date=e.event_date,
            reference=e.reference,
            created_at=e.created_at,
        )
        for e in events
    ]


def record_cold_store_event(
    db: Session,
    current_user: User,
    store_id: int,
    data: ColdStoreEventCreate,
) -> ColdStoreEventResponse:
    """Record an inventory event (LOADING, RELEASE, ADJUSTMENT) atomically.
    Validates capacity and non-negative constraints.
    Updates the read-optimized ColdStoreInventory balance in the SAME transaction.
    """
    operator = db.query(ColdStoreOperator).filter(ColdStoreOperator.user_id == current_user.id).first()
    if not operator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator profile not found")

    # Verify store ownership
    store = db.query(ColdStore).filter(ColdStore.id == store_id, ColdStore.operator_id == operator.id).first()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cold store not found or access forbidden")

    # Verify commodity exists
    commodity = db.query(Commodity).filter(Commodity.id == data.commodity_id).first()
    if not commodity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commodity not found")

    if data.quantity_kg <= 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Quantity must be strictly greater than 0")

    # Check / lock inventory balance for this store and commodity
    # In SQLite, table/db locks apply; in Postgres, row lock on ColdStoreInventory ensures concurrency safety
    inventory = (
        db.query(ColdStoreInventory)
        .filter(
            ColdStoreInventory.cold_store_id == store.id,
            ColdStoreInventory.commodity_id == data.commodity_id,
        )
        .with_for_update()
        .first()
    )

    current_commodity_qty = inventory.current_quantity_kg if inventory else Decimal(0)

    # Current total occupancy of entire cold store across all commodities
    total_store_occupancy = (
        db.query(func.coalesce(func.sum(ColdStoreInventory.current_quantity_kg), Decimal(0)))
        .filter(ColdStoreInventory.cold_store_id == store.id)
        .scalar()
        or Decimal(0)
    )

    # Business rules evaluation
    if data.event_type == ColdStoreEventType.LOADING:
        new_total_occupancy = Decimal(total_store_occupancy) + data.quantity_kg
        if new_total_occupancy > store.capacity_kg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Loading exceeds cold store capacity. Maximum available capacity is {store.capacity_kg - Decimal(total_store_occupancy):.2f} kg.",
            )
        new_commodity_qty = Decimal(current_commodity_qty) + data.quantity_kg

    elif data.event_type == ColdStoreEventType.RELEASE:
        if data.quantity_kg > current_commodity_qty:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient inventory for this release. Currently available: {current_commodity_qty:.2f} kg.",
            )
        new_commodity_qty = Decimal(current_commodity_qty) - data.quantity_kg

    elif data.event_type == ColdStoreEventType.ADJUSTMENT:
        # Adjustment quantity is positive, but adjustment can be upward or downward based on reference / business logic
        # For our MVP event schema, quantity is > 0, reference specifies type or direction
        # If adjustment reduces stock:
        if "REDUCE" in (data.reference or "").upper() or "SPOILAGE" in (data.reference or "").upper():
            if data.quantity_kg > current_commodity_qty:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Adjustment deduction exceeds available stock: {current_commodity_qty:.2f} kg.",
                )
            new_commodity_qty = Decimal(current_commodity_qty) - data.quantity_kg
        else:
            new_total_occupancy = Decimal(total_store_occupancy) + data.quantity_kg
            if new_total_occupancy > store.capacity_kg:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Adjustment exceeds cold store capacity.",
                )
            new_commodity_qty = Decimal(current_commodity_qty) + data.quantity_kg

    # 1. Update or create inventory balance row
    if inventory:
        inventory.current_quantity_kg = new_commodity_qty
    else:
        inventory = ColdStoreInventory(
            cold_store_id=store.id,
            commodity_id=data.commodity_id,
            current_quantity_kg=new_commodity_qty,
        )
        db.add(inventory)

    # 2. Insert immutable event log
    event = ColdStoreEvent(
        cold_store_id=store.id,
        commodity_id=data.commodity_id,
        event_type=data.event_type,
        quantity_kg=data.quantity_kg,
        event_date=data.event_date,
        reference=data.reference.strip() if data.reference else None,
    )
    db.add(event)

    # 3. Commit atomically
    db.commit()
    db.refresh(event)

    return ColdStoreEventResponse(
        id=event.id,
        cold_store_id=event.cold_store_id,
        commodity_id=event.commodity_id,
        commodity_name=commodity.name,
        commodity_code=commodity.code,
        event_type=event.event_type,
        quantity_kg=event.quantity_kg,
        event_date=event.event_date,
        reference=event.reference,
        created_at=event.created_at,
    )
