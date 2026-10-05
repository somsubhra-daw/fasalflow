from fastapi import APIRouter

api_router = APIRouter()

@api_router.get("/health")
def api_health() -> dict[str, str]:
    return {"status":"ok"}