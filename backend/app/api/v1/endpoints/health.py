from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import get_db

health_router = APIRouter(tags=["health"])


@health_router.get("/health")
def api_health() -> dict[str, str]:
    """Basic API liveness check.
    Does not depend on the database being reachable.
    """
    return {"status": "ok", "service": "fasalflow-backend"}


@health_router.get("/health/readiness")
def api_readiness(db: Session = Depends(get_db)) -> dict[str, str]:
    """API readiness check.
    Verifies that the database is connected and responsive.
    """
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        ) from exc
