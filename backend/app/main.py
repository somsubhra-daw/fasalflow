from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup structured logging on startup
    setup_logging()
    logger.info("FasalFlow backend starting up in %s mode...", settings.ENVIRONMENT)
    yield
    logger.info("FasalFlow backend shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="FasalFlow: Agricultural market intelligence and decision-support backend.",
    lifespan=lifespan,
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standardized generic exception handler to avoid leaking tracebacks or internals
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception processing %s %s: %s", request.method, request.url.path, str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )

# Root-level liveness health check
@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fasalflow-backend"}


# Include versioned API router
app.include_router(api_router, prefix="/api/v1")