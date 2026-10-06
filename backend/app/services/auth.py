from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import hash_password, verify_password, create_access_token
from app.models.models import User, Farmer, ColdStoreOperator
from app.models.enums import UserRole
from app.schemas.auth import UserRegisterRequest, UserLoginRequest, UserResponse, Token


def register_user(db: Session, req: UserRegisterRequest) -> Token:
    """Register a new user and create their corresponding domain profile atomically."""
    # Check if identifier already exists
    existing_user = db.query(User).filter(User.identifier == req.identifier.strip().lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email/phone already exists",
        )

    # Validate cold store operator requirements
    if req.role == UserRole.COLD_STORE_OPERATOR and not req.organization_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Organization name is required for Cold Store Operators",
        )

    # Create User
    new_user = User(
        name=req.name.strip(),
        identifier=req.identifier.strip().lower(),
        password_hash=hash_password(req.password),
        role=req.role,
        is_active=True,
    )
    db.add(new_user)
    db.flush()  # obtain user id for profile

    # Create associated profile
    if req.role == UserRole.FARMER:
        farmer = Farmer(
            user_id=new_user.id,
            district=req.district.strip(),
            block=req.block.strip() if req.block else None,
            village=req.village.strip() if req.village else None,
            phone=req.phone.strip() if req.phone else req.identifier.strip(),
        )
        db.add(farmer)
    elif req.role == UserRole.COLD_STORE_OPERATOR:
        operator = ColdStoreOperator(
            user_id=new_user.id,
            organization_name=req.organization_name.strip(),
            district=req.district.strip(),
            address=req.village.strip() if req.village else None,
            phone=req.phone.strip() if req.phone else req.identifier.strip(),
        )
        db.add(operator)

    db.commit()
    db.refresh(new_user)

    # Issue JWT token
    token = create_access_token(subject=str(new_user.id), role=new_user.role.value)
    return Token(access_token=token, token_type="bearer", role=new_user.role)


def authenticate_user(db: Session, req: UserLoginRequest) -> Token:
    """Verify credentials and return signed access token."""
    user = db.query(User).filter(User.identifier == req.identifier.strip().lower()).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    token = create_access_token(subject=str(user.id), role=user.role.value)
    return Token(access_token=token, token_type="bearer", role=user.role)


def build_user_response(user: User) -> UserResponse:
    """Format user model and associated domain profile for API response."""
    farmer_id: Optional[int] = None
    operator_id: Optional[int] = None
    district: Optional[str] = None

    if user.farmer_profile:
        farmer_id = user.farmer_profile.id
        district = user.farmer_profile.district
    elif user.operator_profile:
        operator_id = user.operator_profile.id
        district = user.operator_profile.district

    return UserResponse(
        id=user.id,
        name=user.name,
        identifier=user.identifier,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        farmer_id=farmer_id,
        operator_id=operator_id,
        district=district,
    )
