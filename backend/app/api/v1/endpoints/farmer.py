from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.dependencies import require_farmer
from app.models.models import User
from app.models.enums import SupplyStatus
from app.schemas.farmer import (
    FarmCreate,
    FarmResponse,
    FarmerSupplyCreate,
    FarmerSupplyUpdate,
    FarmerSupplyResponse,
    FarmerProfileResponse,
)
from app.services.farmer import (
    get_farmer_profile,
    list_farmer_farms,
    create_farm,
    list_farmer_supplies,
    create_farmer_supply,
    update_farmer_supply,
    delete_farmer_supply,
)

router = APIRouter(prefix="/farmer", tags=["Farmer"])


@router.get("/profile", response_model=FarmerProfileResponse)
def profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
) -> FarmerProfileResponse:
    """Get the authenticated farmer's profile, including farm counts and active supplies."""
    return get_farmer_profile(db=db, current_user=current_user)


@router.get("/farms", response_model=List[FarmResponse])
def get_farms(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
) -> List[FarmResponse]:
    """List all farms owned by the authenticated farmer."""
    return list_farmer_farms(db=db, current_user=current_user)


@router.post("/farms", response_model=FarmResponse, status_code=status.HTTP_201_CREATED)
def add_farm(
    data: FarmCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
) -> FarmResponse:
    """Create a new farm under the authenticated farmer."""
    return create_farm(db=db, current_user=current_user, data=data)


@router.get("/supply", response_model=List[FarmerSupplyResponse])
def get_supplies(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[SupplyStatus] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
) -> List[FarmerSupplyResponse]:
    """List declared produce supplies for all farms owned by the farmer."""
    return list_farmer_supplies(
        db=db,
        current_user=current_user,
        limit=limit,
        offset=offset,
        status_filter=status,
    )


@router.post("/supply", response_model=FarmerSupplyResponse, status_code=status.HTTP_201_CREATED)
def add_supply(
    data: FarmerSupplyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
) -> FarmerSupplyResponse:
    """Declare produce supply for a farm. Farm ownership is strictly validated."""
    return create_farmer_supply(db=db, current_user=current_user, data=data)


@router.patch("/supply/{id}", response_model=FarmerSupplyResponse)
def update_supply(
    id: int,
    data: FarmerSupplyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
) -> FarmerSupplyResponse:
    """Update a produce supply declaration. Ownership is verified."""
    return update_farmer_supply(db=db, current_user=current_user, supply_id=id, data=data)


@router.delete("/supply/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supply(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_farmer),
) -> None:
    """Delete a produce supply declaration. Ownership is verified."""
    delete_farmer_supply(db=db, current_user=current_user, supply_id=id)