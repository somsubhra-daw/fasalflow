from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.dependencies import require_cold_store_operator
from app.models.models import User
from app.schemas.cold_store import (
    ColdStoreCreate,
    ColdStoreResponse,
    ColdStoreInventoryResponse,
    ColdStoreEventCreate,
    ColdStoreEventResponse,
    ColdStoreOperatorProfileResponse,
)
from app.services.cold_store import (
    get_operator_profile,
    list_operator_stores,
    create_cold_store,
    get_cold_store_by_id,
    get_cold_store_inventory,
    list_cold_store_events,
    record_cold_store_event,
)

router = APIRouter(prefix="/cold-store", tags=["Cold Store"])


@router.get("/profile", response_model=ColdStoreOperatorProfileResponse)
def profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_cold_store_operator),
) -> ColdStoreOperatorProfileResponse:
    """Get the authenticated operator's profile, total capacity, and overall occupancy."""
    return get_operator_profile(db=db, current_user=current_user)


@router.get("/stores", response_model=List[ColdStoreResponse])
def get_stores(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_cold_store_operator),
) -> List[ColdStoreResponse]:
    """List all cold storage facilities managed by the operator."""
    return list_operator_stores(db=db, current_user=current_user)


@router.post("/stores", response_model=ColdStoreResponse, status_code=status.HTTP_201_CREATED)
def add_cold_store(
    data: ColdStoreCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_cold_store_operator),
) -> ColdStoreResponse:
    """Create a new cold storage facility under the operator."""
    return create_cold_store(db=db, current_user=current_user, data=data)


@router.get("/stores/{id}", response_model=ColdStoreResponse)
def get_store(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_cold_store_operator),
) -> ColdStoreResponse:
    """Get details and occupancy metrics for a single cold storage facility."""
    return get_cold_store_by_id(db=db, current_user=current_user, store_id=id)


@router.get("/stores/{id}/inventory", response_model=List[ColdStoreInventoryResponse])
def get_inventory(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_cold_store_operator),
) -> List[ColdStoreInventoryResponse]:
    """Get current stock balance per commodity for a cold store."""
    return get_cold_store_inventory(db=db, current_user=current_user, store_id=id)


@router.post("/stores/{id}/events", response_model=ColdStoreEventResponse, status_code=status.HTTP_201_CREATED)
def post_event(
    id: int,
    data: ColdStoreEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_cold_store_operator),
) -> ColdStoreEventResponse:
    """Record an inventory LOADING, RELEASE, or ADJUSTMENT event with atomic balance update and capacity checks."""
    return record_cold_store_event(db=db, current_user=current_user, store_id=id, data=data)


@router.get("/stores/{id}/events", response_model=List[ColdStoreEventResponse])
def get_events(
    id: int,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_cold_store_operator),
) -> List[ColdStoreEventResponse]:
    """List historical audit event log for a cold store."""
    return list_cold_store_events(db=db, current_user=current_user, store_id=id, limit=limit, offset=offset)