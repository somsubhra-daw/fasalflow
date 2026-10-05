from fastapi import APIRouter

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

@router.get("/health")
def intelligence_module_health() -> dict[str, str]:
    return {"module": "intelligence", "status": "ready"}