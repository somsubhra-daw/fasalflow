from enum import Enum

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["authentication"])


class UserRole(str, Enum):
    FARMER = "FARMER"
    COLD_STORE_OPERATOR = "COLD_STORE_OPERATOR"


@router.get("/roles")
def available_roles() -> dict[str, list[str]]:
    return {"roles": [role.value for role in UserRole]}