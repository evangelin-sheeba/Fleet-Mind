"""
FastAPI Main Application Entry Point for FLEETMIND.
Provides REST API backend for Streamlit Driver Cockpit & Fleet Manager Dashboards.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router as api_router
from app.database.json_repository import get_repository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("fleetmind.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes and verifies JSON database repository on server boot."""
    logger.info("Starting FleetMind FastAPI Backend Service...")
    repo = get_repository()
    drivers = repo.get_all_drivers()
    vehicles = repo.get_all_vehicles()
    logger.info(f"Loaded JSON Database: {len(drivers)} drivers, {len(vehicles)} vehicles.")
    yield
    logger.info("Shutting down FleetMind FastAPI Backend Service...")


app = FastAPI(
    title="FleetMind Sentinel API",
    description="Commercial Fleet Telematics, Edge Vision Driver Monitoring (DMS), and Real-time Risk Assessment API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# -----------------------------------------------------------------------------
# CORS Middleware Configuration
# -----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://localhost:8502",
        "http://127.0.0.1:8501",
        "http://127.0.0.1:8502",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Global Error Handling
# -----------------------------------------------------------------------------
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal Server Error",
            "detail": str(exc),
            "path": request.url.path
        }
    )

# -----------------------------------------------------------------------------
# Root Information Endpoint
# -----------------------------------------------------------------------------
@app.get("/", tags=["System"])
def root():
    return {
        "service": "FleetMind Sentinel API",
        "version": "1.0.0",
        "status": "ONLINE",
        "documentation": "/docs",
        "health_check": "/health",
        "endpoints": [
            "/drivers",
            "/drivers/{driver_id}",
            "/drivers/{driver_id}/risk",
            "/vehicles",
            "/alerts",
            "/events",
            "/risk",
            "/fleet/status",
            "/commands"
        ]
    }

# -----------------------------------------------------------------------------
# Mount Routes
# Mount both at root (e.g. /drivers) and under /api (e.g. /api/drivers) for flexibility
# -----------------------------------------------------------------------------
app.include_router(api_router)
app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
