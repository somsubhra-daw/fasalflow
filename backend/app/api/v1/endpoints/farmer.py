from fastapi import APIRouter

router = APIRouter(prefix="/farmer", tags=["farmer"])

@router.get("/health")
def farmer_module_health() -> dict[str, str]:
    return {"module": "farmer", "status": "ready"}