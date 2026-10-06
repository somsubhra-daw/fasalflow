from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.models.models import User
from app.models.enums import UserRole
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    Token,
)
from app.services.auth import (
    register_user,
    authenticate_user,
    build_user_response,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/roles")
def available_roles() -> dict[str, list[str]]:
    """Return available user roles for registration."""
    return {"roles": [role.value for role in UserRole]}


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest, db: Session = Depends(get_db)) -> Token:
    """Register a new user as either FARMER or COLD_STORE_OPERATOR."""
    return register_user(db=db, req=req)


@router.post("/login", response_model=Token)
def login(req: UserLoginRequest, db: Session = Depends(get_db)) -> Token:
    """Authenticate with identifier and password to receive JWT token."""
    return authenticate_user(db=db, req=req)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Get current authenticated user profile and role details."""
    return build_user_response(current_user)