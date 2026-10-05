from fastapi import FastAPI
from app.api.v1.router import api_router

app = FastAPI(
    title="FasalFlow API",
    version="0.1.0",
    description="Agricultural market intelligence and decision-support backend.",
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status":"ok","service":"fasalflow-backend"}