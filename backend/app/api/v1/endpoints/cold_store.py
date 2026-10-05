from fastapi import APIRouter

router = APIRouter(prefix="/cold-store", tags=["cold-store"])

@router.get("/health")
def cold_store_module_health() -> dict[str, str]:
    return {"module": "cold-store", "status": "ready"}