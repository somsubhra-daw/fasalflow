from fastapi import APIRouter
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.farmer import router as farmer_router
from app.api.v1.endpoints.cold_store import router as cold_store_router
from app.api.v1.endpoints.market import market_router, buyer_router
from app.api.v1.endpoints.intelligence import router as intelligence_router
from app.api.v1.endpoints.health import health_router

api_router = APIRouter()

# Core routes
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(farmer_router)
api_router.include_router(cold_store_router)
api_router.include_router(market_router)
api_router.include_router(buyer_router)
api_router.include_router(intelligence_router)