from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.models import User, Farmer, ColdStoreOperator
from app.models.enums import UserRole

bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate bearer JWT and load current active user from database.
    Rejects unauthenticated or inactive users.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return user


def require_farmer(current_user: User = Depends(get_current_user)) -> User:
    """Ensure the authenticated user possesses the FARMER role."""
    if current_user.role != UserRole.FARMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Farmer role required",
        )
    return current_user


def require_cold_store_operator(current_user: User = Depends(get_current_user)) -> User:
    """Ensure the authenticated user possesses the COLD_STORE_OPERATOR role."""
    if current_user.role != UserRole.COLD_STORE_OPERATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Cold Store Operator role required",
        )
    return current_user


from fastapi import Header
from app.core.config import settings

optional_bearer = HTTPBearer(auto_error=False)


def require_market_write_access(
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer),
    db: Session = Depends(get_db),
) -> None:
    """Validate authorization for market/buyer writes.
    Allowed:
    1. Trusted internal key (X-Internal-Key)
    2. Authenticated COLD_STORE_OPERATOR role
    Explicitly forbidden:
    - Farmers (HTTP 403)
    - Unauthenticated clients (HTTP 403)
    """
    # 1. Internal API key authorization
    if x_internal_key and x_internal_key == settings.INTERNAL_API_KEY:
        return

    # 2. Authenticated JWT token authorization
    if credentials:
        try:
            payload = decode_access_token(credentials.credentials)
            user_id = int(payload.get("sub", 0))
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.is_active:
                if user.role == UserRole.FARMER:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access forbidden: Farmers cannot create or modify buyer demand",
                    )
                if user.role == UserRole.COLD_STORE_OPERATOR:
                    return
        except (JWTError, ValueError):
            pass

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access forbidden: Trusted internal worker or operator authorization required",
    )


# Backward-compatible alias
require_internal_worker = require_market_write_access

