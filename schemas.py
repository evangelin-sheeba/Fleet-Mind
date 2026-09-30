"""
Pydantic Schemas for Request and Response Validation.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    status: str = "ok"
    service: str = "FleetMind API"
    version: str = "1.0.0"
    timestamp: str


class RiskBreakdown(BaseModel):
    eye_fatigue_score: float = 0.0
    yawn_fatigue_score: float = 0.0
    speed_factor: float = 0.0


class DriverSummary(BaseModel):
    driver_id: str
    driver_name: str
    vehicle_id: str = ""
    trip_id: str = ""
    city: str = ""
    driver_status: str = "Safe"
    risk_score: float = 0.0
    risk_level: str = "NOMINAL"
    current_speed_kph: float = 0.0
    drowsiness_events_count: int = 0
    yawning_events_count: int = 0
    last_updated: str


class DriverRiskResponse(BaseModel):
    driver_id: str
    driver_name: str
    vehicle_id: str = ""
    risk_score: float = 0.0
    risk_level: str = "NOMINAL"
    driver_status: str = "Safe"
    ear: float = 0.30
    mar: float = 0.22
    eye_closed_seconds: float = 0.0
    is_yawning: bool = False
    microsleep_detected: bool = False
    current_speed_kph: float = 0.0
    breakdown: Optional[Dict[str, float]] = None
    last_updated: str


class RiskEventResponse(BaseModel):
    id: int
    timestamp: str
    driver_id: str
    vehicle_id: str = ""
    event_type: str
    severity: str = "INFO"
    risk_score: float = 0.0
    speed_kmh: float = 0.0
    details: str = ""


class DriverDetail(BaseModel):
    driver_id: str
    driver_name: str
    vehicle_id: str = ""
    trip_id: str = ""
    route_id: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    cargo_type: str = ""
    driver_status: str = "Safe"
    risk_score: float = 0.0
    risk_level: str = "NOMINAL"
    ear: float = 0.30
    mar: float = 0.22
    eye_closed_seconds: float = 0.0
    is_yawning: bool = False
    microsleep_detected: bool = False
    current_speed_kph: float = 0.0
    current_latitude: float = 0.0
    current_longitude: float = 0.0
    heading_deg: float = 0.0
    vehicle_status: str = "IN_TRANSIT"
    drowsiness_events_count: int = 0
    yawning_events_count: int = 0
    distraction_events_count: int = 0
    last_updated: str
    recent_events: List[Dict[str, Any]] = Field(default_factory=list)


class VehicleSummary(BaseModel):
    vehicle_id: str
    driver_id: str = ""
    driver_name: str = ""
    vehicle_status: str = "IN_TRANSIT"
    speed_kmh: float = 0.0
    latitude: float = 0.0
    longitude: float = 0.0
    heading_deg: float = 0.0
    cargo_type: str = "General Freight"
    cargo_weight_kg: float = 0.0
    city: str = ""
    last_updated: str


class VehicleDetail(BaseModel):
    vehicle_id: str
    driver_id: str = ""
    driver_name: str = ""
    vehicle_status: str = "IN_TRANSIT"
    speed_kmh: float = 0.0
    latitude: float = 0.0
    longitude: float = 0.0
    heading_deg: float = 0.0
    route_id: str = ""
    trip_id: str = ""
    cargo_type: str = ""
    cargo_weight_kg: float = 0.0
    city: str = ""
    state: str = ""
    country: str = ""
    anomaly_detected: bool = False
    anomaly_type: str = "none"
    last_updated: str


class RiskEventCreate(BaseModel):
    driver_id: str = Field(..., description="Driver Identifier, e.g. D001")
    vehicle_id: Optional[str] = Field(None, description="Vehicle Identifier, e.g. TRK-001")
    event_type: str = Field(..., description="microsleep, yawn, hard_brake, safe_stop, distraction")
    severity: str = Field("INFO", description="INFO, WARNING, CRITICAL")
    risk_score: float = Field(0.0, description="Risk Score from 0 to 100")
    speed_kmh: float = Field(0.0, description="Instantaneous vehicle speed in km/h")
    details: str = Field("", description="Human-readable event description")
    timestamp: Optional[str] = Field(None, description="Optional ISO timestamp")


class TelemetryRiskUpdate(BaseModel):
    driver_id: str = "D001"
    driver_name: Optional[str] = None
    vehicle_id: Optional[str] = "TRK-001"
    speed_kmh: float = 0.0
    acceleration_kmh_s: Optional[float] = 0.0
    latitude: Optional[float] = 11.2335
    longitude: Optional[float] = 78.8817
    heading_deg: Optional[float] = 45.0
    ear: float = 0.30
    mar: float = 0.22
    eye_closed_seconds: float = 0.0
    is_yawning: bool = False
    microsleep_detected: bool = False
    risk_score: float = 0.0
    risk_level: Optional[str] = None
    driver_action: Optional[str] = None
    timestamp: Optional[str] = None


class FleetStatusResponse(BaseModel):
    total_vehicles: int
    active_vehicles: int
    total_drivers: int
    safe_drivers_count: int
    warning_drivers_count: int
    critical_drivers_count: int
    average_risk_score: float
    recent_alerts_count: int
    system_status: str = "ONLINE"
    database_connected: bool = True
    database_file: str
    last_sync_timestamp: str


class ManagerCommandCreate(BaseModel):
    vehicle_id: str = "TN 58 AA 4920"
    command_type: str = Field(..., description="MANDATORY_SAFE_STOP, AUDIO_ADVISORY, VOICE_CONTACT_REQUEST, ACKNOWLEDGE")
    message: str = Field(..., description="Dispatch advisory message to cabin display")


class ManagerCommandResponse(BaseModel):
    id: int
    timestamp: str
    vehicle_id: str
    command_type: str
    message: str
    status: str = "DISPATCHED"
