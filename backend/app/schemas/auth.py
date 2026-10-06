from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.enums import UserRole


# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None


# Registration schemas
class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    identifier: str = Field(..., min_length=3, max_length=150, description="Email or unique login phone number")
    password: str = Field(..., min_length=6, max_length=72)
    role: UserRole
    # Role-specific profile details
    district: str = Field(..., min_length=2, max_length=100)
    block: Optional[str] = None
    village: Optional[str] = None
    phone: Optional[str] = None
    organization_name: Optional[str] = None  # Required for COLD_STORE_OPERATOR


class UserLoginRequest(BaseModel):
    identifier: str = Field(..., min_length=3, max_length=150)
    password: str = Field(..., min_length=1, max_length=72)


# User Response schema
class UserResponse(BaseModel):
    id: int
    name: str
    identifier: str
    role: UserRole
    is_active: bool
    created_at: datetime
    # Profile IDs
    farmer_id: Optional[int] = None
    operator_id: Optional[int] = None
    district: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
