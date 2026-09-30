"""
FastAPI REST API Routes for FleetMind.
Decouples Streamlit dashboards from direct database access.
"""

from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, status

from app.models.schemas import (
    DriverSummary,
    DriverDetail,
    DriverRiskResponse,
    VehicleSummary,
    VehicleDetail,
    RiskEventCreate,
    RiskEventResponse,
    TelemetryRiskUpdate,
    FleetStatusResponse,
    ManagerCommandCreate,
    ManagerCommandResponse,
    HealthCheckResponse
)
from app.services.database_service import get_database_service
from app.services.risk_service import get_risk_service

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["System"],
    summary="System Health Check"
)
def health_check():
    """Returns system status, service name, and server time."""
    return HealthCheckResponse(
        status="ok",
        service="FleetMind API",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat()
    )


# -----------------------------------------------------------------------------
# Drivers Endpoints
# -----------------------------------------------------------------------------
@router.get(
    "/drivers",
    response_model=List[DriverSummary],
    tags=["Drivers"],
    summary="List all registered drivers"
)
def list_drivers(
    status: Optional[str] = Query(None, description="Filter by status: Safe, Warning, Critical"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level: NOMINAL, ELEVATED, CRITICAL")
):
    """Retrieves all drivers in the fleet along with current risk scores and vehicle assignments."""
    db_service = get_database_service()
    return db_service.list_drivers(status=status, risk_level=risk_level)


@router.get(
    "/drivers/{driver_id}",
    response_model=DriverDetail,
    tags=["Drivers"],
    summary="Get single driver profile and details"
)
def get_driver(driver_id: str):
    """Retrieves full profile, active corridor trip, biometrics, and recent events for a driver."""
    db_service = get_database_service()
    driver = db_service.get_driver_by_id(driver_id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Driver with ID '{driver_id}' not found in database."
        )
    return driver


@router.get(
    "/drivers/{driver_id}/risk",
    response_model=DriverRiskResponse,
    tags=["Risk & Biometrics"],
    summary="Get real-time risk evaluation for a driver"
)
def get_driver_risk(driver_id: str):
    """Returns real-time risk index (0-100), risk level, and biometric indicators (EAR, MAR, yawning, microsleep)."""
    risk_service = get_risk_service()
    risk_data = risk_service.get_driver_risk(driver_id)
    if not risk_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Driver with ID '{driver_id}' not found in database."
        )
    return risk_data


# -----------------------------------------------------------------------------
# Vehicles Endpoints
# -----------------------------------------------------------------------------
@router.get(
    "/vehicles",
    response_model=List[VehicleSummary],
    tags=["Vehicles"],
    summary="List all fleet vehicles"
)
def list_vehicles(
    status: Optional[str] = Query(None, description="Filter by vehicle status: IN_TRANSIT, SAFE_STOP, STATIONARY")
):
    """Retrieves all fleet vehicles with live speed, coordinates, cargo description, and assigned operator."""
    db_service = get_database_service()
    return db_service.list_vehicles(status=status)


@router.get(
    "/vehicles/{vehicle_id}",
    response_model=VehicleDetail,
    tags=["Vehicles"],
    summary="Get vehicle telemetry specifications and manifest"
)
def get_vehicle(vehicle_id: str):
    """Retrieves full vehicle telematics record, route status, and diagnostics."""
    db_service = get_database_service()
    veh = db_service.get_vehicle_by_id(vehicle_id)
    if not veh:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle with ID '{vehicle_id}' not found in registry."
        )
    return veh


# -----------------------------------------------------------------------------
# Alerts & Events Endpoints
# -----------------------------------------------------------------------------
@router.get(
    "/alerts",
    response_model=List[RiskEventResponse],
    tags=["Alerts & Events"],
    summary="Query recent alerts and safety interventions"
)
def get_alerts(
    limit: int = Query(50, ge=1, le=200, description="Max alerts to retrieve"),
    severity: Optional[str] = Query(None, description="Filter by severity: INFO, WARNING, CRITICAL"),
    driver_id: Optional[str] = Query(None, description="Filter alerts by driver ID")
):
    """Returns chronological audit log of alerts, microsleep detections, hard braking, and safety directives."""
    risk_service = get_risk_service()
    return risk_service.list_alerts(limit=limit, severity=severity, driver_id=driver_id)


@router.post(
    "/events",
    response_model=RiskEventResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Alerts & Events"],
    summary="Record a driver safety or sensor event"
)
def record_event(event_in: RiskEventCreate):
    """Ingests a driver event (e.g. microsleep episode, yawning cluster, hard brake, safe stop)."""
    risk_service = get_risk_service()
    created_event = risk_service.create_risk_event(event_in.model_dump())
    return created_event


@router.post(
    "/risk",
    tags=["Risk & Biometrics"],
    summary="Ingest live driver telemetry, vision biometrics, and risk updates"
)
def update_telemetry_risk(payload: TelemetryRiskUpdate):
    """
    Called by the Driver Cockpit HUD during live streaming.
    Safely stores current speed, EAR, MAR, microsleep flag, and risk score in the JSON database.
    """
    risk_service = get_risk_service()
    result = risk_service.process_telemetry_and_risk(payload.model_dump())
    return {
        "status": "success",
        "message": "Telemetry and risk index updated",
        "data": result
    }


# -----------------------------------------------------------------------------
# Fleet Summary & Dispatch Commands
# -----------------------------------------------------------------------------
@router.get(
    "/fleet/status",
    response_model=FleetStatusResponse,
    tags=["Fleet Management"],
    summary="Get aggregated fleet health and risk overview"
)
def get_fleet_status():
    """Returns aggregated fleet status for the Fleet Manager dashboard."""
    db_service = get_database_service()
    return db_service.get_fleet_status()


@router.post(
    "/commands",
    response_model=ManagerCommandResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Dispatch Commands"],
    summary="Dispatch manager supervisory directive to driver cabin"
)
def dispatch_command(cmd: ManagerCommandCreate):
    """Dispatches a manager directive (e.g. MANDATORY_SAFE_STOP, AUDIO_ADVISORY)."""
    db_service = get_database_service()
    res = db_service.record_manager_command(cmd.model_dump())
    return res


@router.get(
    "/commands",
    response_model=List[ManagerCommandResponse],
    tags=["Dispatch Commands"],
    summary="List recent manager directives"
)
def list_commands(limit: int = Query(10, ge=1, le=50)):
    """Returns recent dispatch supervisory directives."""
    db_service = get_database_service()
    return db_service.list_manager_commands(limit=limit)
