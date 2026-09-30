"""
JSON Database Repository Layer for FleetMind.

Provides thread-safe, atomic read/write access to the persistent JSON database
derived from fleet-route-optimization-telematics.json.
Guarantees zero corruption using atomic write-to-temp-then-replace semantics.
"""

import os
import json
import time
import uuid
import logging
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger("fleetmind.database")


def _get_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    if val is None or val == "":
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


class JSONRepository:
    """
    Thread-safe repository managing:
    - fleet_database.json (Persistent driver/vehicle/trip dataset)
    - fleet_events.json (Event/alert history)
    - fleet_commands.json (Manager dispatch directives)
    """

    def __init__(self, data_dir: Optional[str] = None):
        self.lock = threading.RLock()
        
        # Determine paths
        if data_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.data_dir = os.path.join(base_dir, "data")
        else:
            self.data_dir = data_dir

        os.makedirs(self.data_dir, exist_ok=True)
        self.db_path = os.path.join(self.data_dir, "fleet_database.json")
        self.events_path = os.path.join(self.data_dir, "fleet_events.json")
        self.commands_path = os.path.join(self.data_dir, "fleet_commands.json")

        # In-memory caches for fast concurrent access
        self._records: List[Dict[str, Any]] = []
        self._drivers_map: Dict[str, Dict[str, Any]] = {}
        self._vehicles_map: Dict[str, Dict[str, Any]] = {}
        self._events: List[Dict[str, Any]] = []
        self._commands: List[Dict[str, Any]] = []

        self._initialize()

    def _initialize(self):
        """Loads and bootstraps existing JSON database, ensuring schema adaptation."""
        with self.lock:
            # 1. Load or bootstrap fleet_database.json
            if not os.path.exists(self.db_path):
                # Try fallback from Downloads if not in data dir
                downloads_path = r"C:\Users\HEBEYA MERJOLIN\Downloads\fleet-route-optimization-telematics.json"
                if os.path.exists(downloads_path):
                    try:
                        with open(downloads_path, "r", encoding="utf-8") as f:
                            raw_data = json.load(f)
                        self._save_json_atomic(self.db_path, raw_data)
                    except Exception as e:
                        logger.error(f"Failed to copy downloaded JSON: {e}")

            if os.path.exists(self.db_path):
                try:
                    with open(self.db_path, "r", encoding="utf-8") as f:
                        self._records = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading {self.db_path}: {e}")
                    self._records = []
            else:
                self._records = []

            # 2. Enrich/adapt schema fields on records without breaking original fields
            self._adapt_schema()

            # 3. Load events
            if os.path.exists(self.events_path):
                try:
                    with open(self.events_path, "r", encoding="utf-8") as f:
                        self._events = json.load(f)
                except Exception:
                    self._events = []
            else:
                self._events = []

            # 4. Load commands
            if os.path.exists(self.commands_path):
                try:
                    with open(self.commands_path, "r", encoding="utf-8") as f:
                        self._commands = json.load(f)
                except Exception:
                    self._commands = []
            else:
                self._commands = []

    def _adapt_schema(self):
        """
        Enriches records with runtime fields expected by prototype if not already set.
        Original fields (city, trip_id, distance_km, max_speed_kph, etc.) are strictly preserved.
        """
        driver_names = {
            "D001": "Arun Kumar",
            "D002": "Suresh Raina",
            "D003": "Vikram Singh",
            "D004": "Karthik Raja",
            "D005": "Anand Sharma",
        }

        self._drivers_map.clear()
        self._vehicles_map.clear()

        for idx, rec in enumerate(self._records):
            d_id = rec.get("driver_id", f"D{idx+1:03d}")
            v_id = rec.get("vehicle_id", f"TRK-{idx+1:03d}")

            # Assign default driver name if missing
            if "driver_name" not in rec:
                rec["driver_name"] = driver_names.get(d_id, f"Driver {d_id}")

            # Telematics & Risk runtime fields
            rec.setdefault("driver_status", "Safe")  # Safe | Warning | Critical
            rec.setdefault("risk_score", 0.0)
            rec.setdefault("risk_level", "NOMINAL")  # NOMINAL | ELEVATED | CRITICAL
            rec.setdefault("vehicle_status", "IN_TRANSIT" if rec.get("average_speed_kph", 0) > 0 else "STATIONARY")
            rec.setdefault("current_speed_kph", float(rec.get("average_speed_kph", 50.0)))
            rec.setdefault("current_latitude", float(rec.get("start_latitude", 11.2335)))
            rec.setdefault("current_longitude", float(rec.get("start_longitude", 78.8817)))
            rec.setdefault("heading_deg", 45.0)
            rec.setdefault("ear", 0.30)
            rec.setdefault("mar", 0.22)
            rec.setdefault("eye_closed_seconds", 0.0)
            rec.setdefault("is_yawning", False)
            rec.setdefault("microsleep_detected", False)
            rec.setdefault("drowsiness_events_count", 0)
            rec.setdefault("yawning_events_count", 0)
            rec.setdefault("distraction_events_count", 0)
            rec.setdefault("last_updated", rec.get("start_time", _get_utc_iso()))

            # Index primary mapping
            if d_id not in self._drivers_map:
                self._drivers_map[d_id] = rec
            if v_id not in self._vehicles_map:
                self._vehicles_map[v_id] = rec

    def _save_json_atomic(self, file_path: str, data: Any):
        """Writes data to a temporary file and atomically replaces the target."""
        tmp_path = f"{file_path}.{uuid.uuid4().hex}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, file_path)
        except Exception as e:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            logger.error(f"Atomic save error for {file_path}: {e}")
            raise

    def persist_database(self):
        """Flushes in-memory database records to disk atomically."""
        with self.lock:
            self._save_json_atomic(self.db_path, self._records)

    def persist_events(self):
        """Flushes in-memory events to disk atomically."""
        with self.lock:
            self._save_json_atomic(self.events_path, self._events)

    def persist_commands(self):
        """Flushes in-memory manager commands to disk atomically."""
        with self.lock:
            self._save_json_atomic(self.commands_path, self._commands)

    # -------------------------------------------------------------------------
    # Driver Read / Query Operations
    # -------------------------------------------------------------------------
    def get_all_drivers(
        self,
        status: Optional[str] = None,
        risk_level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Returns list of all registered drivers with their telemetry and risk summaries."""
        with self.lock:
            drivers = []
            for d_id, rec in self._drivers_map.items():
                if status and rec.get("driver_status", "").upper() != status.upper():
                    continue
                if risk_level and rec.get("risk_level", "").upper() != risk_level.upper():
                    continue
                drivers.append({
                    "driver_id": d_id,
                    "driver_name": rec.get("driver_name", f"Driver {d_id}"),
                    "vehicle_id": rec.get("vehicle_id", ""),
                    "trip_id": rec.get("trip_id", ""),
                    "city": rec.get("city", "N/A"),
                    "driver_status": rec.get("driver_status", "Safe"),
                    "risk_score": float(rec.get("risk_score", 0.0)),
                    "risk_level": rec.get("risk_level", "NOMINAL"),
                    "current_speed_kph": float(rec.get("current_speed_kph", 0.0)),
                    "drowsiness_events_count": int(rec.get("drowsiness_events_count", 0)),
                    "yawning_events_count": int(rec.get("yawning_events_count", 0)),
                    "last_updated": rec.get("last_updated", _get_utc_iso())
                })
            return sorted(drivers, key=lambda d: d["driver_id"])

    def get_driver(self, driver_id: str) -> Optional[Dict[str, Any]]:
        """Returns comprehensive details for a specific driver."""
        with self.lock:
            rec = self._drivers_map.get(driver_id)
            if not rec:
                return None
            
            # Retrieve recent events for this driver
            recent_events = [
                e for e in self._events if e.get("driver_id") == driver_id
            ][-10:]

            return {
                "driver_id": driver_id,
                "driver_name": rec.get("driver_name", f"Driver {driver_id}"),
                "vehicle_id": rec.get("vehicle_id", ""),
                "trip_id": rec.get("trip_id", ""),
                "route_id": rec.get("route_id", ""),
                "city": rec.get("city", ""),
                "state": rec.get("state", ""),
                "country": rec.get("country", ""),
                "cargo_type": rec.get("cargo_type", ""),
                "driver_status": rec.get("driver_status", "Safe"),
                "risk_score": float(rec.get("risk_score", 0.0)),
                "risk_level": rec.get("risk_level", "NOMINAL"),
                "ear": float(rec.get("ear", 0.30)),
                "mar": float(rec.get("mar", 0.22)),
                "eye_closed_seconds": float(rec.get("eye_closed_seconds", 0.0)),
                "is_yawning": bool(rec.get("is_yawning", False)),
                "microsleep_detected": bool(rec.get("microsleep_detected", False)),
                "current_speed_kph": float(rec.get("current_speed_kph", 0.0)),
                "current_latitude": float(rec.get("current_latitude", 0.0)),
                "current_longitude": float(rec.get("current_longitude", 0.0)),
                "heading_deg": float(rec.get("heading_deg", 0.0)),
                "vehicle_status": rec.get("vehicle_status", "IN_TRANSIT"),
                "drowsiness_events_count": int(rec.get("drowsiness_events_count", 0)),
                "yawning_events_count": int(rec.get("yawning_events_count", 0)),
                "distraction_events_count": int(rec.get("distraction_events_count", 0)),
                "last_updated": rec.get("last_updated", _get_utc_iso()),
                "recent_events": recent_events
            }

    def get_driver_risk(self, driver_id: str) -> Optional[Dict[str, Any]]:
        """Returns real-time risk evaluation metrics for a specific driver."""
        with self.lock:
            rec = self._drivers_map.get(driver_id)
            if not rec:
                return None
            return {
                "driver_id": driver_id,
                "driver_name": rec.get("driver_name", f"Driver {driver_id}"),
                "vehicle_id": rec.get("vehicle_id", ""),
                "risk_score": float(rec.get("risk_score", 0.0)),
                "risk_level": rec.get("risk_level", "NOMINAL"),
                "driver_status": rec.get("driver_status", "Safe"),
                "ear": float(rec.get("ear", 0.30)),
                "mar": float(rec.get("mar", 0.22)),
                "eye_closed_seconds": float(rec.get("eye_closed_seconds", 0.0)),
                "is_yawning": bool(rec.get("is_yawning", False)),
                "microsleep_detected": bool(rec.get("microsleep_detected", False)),
                "current_speed_kph": float(rec.get("current_speed_kph", 0.0)),
                "breakdown": {
                    "eye_fatigue_score": round(min(65.0, (rec.get("eye_closed_seconds", 0.0) / 2.0) * 55.0), 1),
                    "yawn_fatigue_score": round(15.0 if rec.get("is_yawning") else 0.0, 1),
                    "speed_factor": round(float(rec.get("current_speed_kph", 0.0)) * 0.1, 1),
                },
                "last_updated": rec.get("last_updated", _get_utc_iso())
            }

    # -------------------------------------------------------------------------
    # Vehicle Read / Query Operations
    # -------------------------------------------------------------------------
    def get_all_vehicles(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns list of all vehicles with live status, speed, and GPS coordinates."""
        with self.lock:
            vehicles = []
            for v_id, rec in self._vehicles_map.items():
                if status and rec.get("vehicle_status", "").upper() != status.upper():
                    continue
                vehicles.append({
                    "vehicle_id": v_id,
                    "driver_id": rec.get("driver_id", ""),
                    "driver_name": rec.get("driver_name", ""),
                    "vehicle_status": rec.get("vehicle_status", "IN_TRANSIT"),
                    "speed_kmh": float(rec.get("current_speed_kph", 0.0)),
                    "latitude": float(rec.get("current_latitude", 0.0)),
                    "longitude": float(rec.get("current_longitude", 0.0)),
                    "heading_deg": float(rec.get("heading_deg", 0.0)),
                    "cargo_type": rec.get("cargo_type", "General Freight"),
                    "cargo_weight_kg": _safe_float(rec.get("cargo_weight_kg"), 0.0),
                    "city": rec.get("city", "N/A"),
                    "last_updated": rec.get("last_updated", _get_utc_iso())
                })
            return sorted(vehicles, key=lambda v: v["vehicle_id"])

    def get_vehicle(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """Returns details for a single vehicle."""
        with self.lock:
            rec = self._vehicles_map.get(vehicle_id)
            if not rec:
                return None
            return {
                "vehicle_id": vehicle_id,
                "driver_id": rec.get("driver_id", ""),
                "driver_name": rec.get("driver_name", ""),
                "vehicle_status": rec.get("vehicle_status", "IN_TRANSIT"),
                "speed_kmh": _safe_float(rec.get("current_speed_kph"), 0.0),
                "latitude": _safe_float(rec.get("current_latitude"), 0.0),
                "longitude": _safe_float(rec.get("current_longitude"), 0.0),
                "heading_deg": _safe_float(rec.get("heading_deg"), 0.0),
                "route_id": rec.get("route_id", ""),
                "trip_id": rec.get("trip_id", ""),
                "cargo_type": rec.get("cargo_type", "General Freight"),
                "cargo_weight_kg": _safe_float(rec.get("cargo_weight_kg"), 0.0),
                "city": rec.get("city", "N/A"),
                "state": rec.get("state", "N/A"),
                "country": rec.get("country", "N/A"),
                "anomaly_detected": rec.get("anomaly_detected", False),
                "anomaly_type": rec.get("anomaly_type", "none"),
                "last_updated": rec.get("last_updated", _get_utc_iso())
            }

    # -------------------------------------------------------------------------
    # Ingestion / Telemetry & Risk Updates
    # -------------------------------------------------------------------------
    def update_driver_risk_and_telemetry(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Receives continuous telemetry and biometrics from Driver Cockpit.
        Safely updates driver state in JSON database and generates alert events if needed.
        """
        driver_id = update_data.get("driver_id", "D001")
        now_str = update_data.get("timestamp") or _get_utc_iso()

        with self.lock:
            # Ensure driver exists or create fallback
            if driver_id not in self._drivers_map:
                # Add dynamic driver entry
                new_rec = {
                    "driver_id": driver_id,
                    "driver_name": update_data.get("driver_name", f"Driver {driver_id}"),
                    "vehicle_id": update_data.get("vehicle_id", "TRK-001"),
                    "city": "In-Transit",
                    "trip_id": f"T-{driver_id}",
                    "route_id": "R101"
                }
                self._records.append(new_rec)
                self._adapt_schema()

            rec = self._drivers_map[driver_id]
            
            # Update telemetry values
            speed = float(update_data.get("speed_kmh", rec.get("current_speed_kph", 0.0)))
            rec["current_speed_kph"] = speed
            if "latitude" in update_data:
                rec["current_latitude"] = float(update_data["latitude"])
            if "longitude" in update_data:
                rec["current_longitude"] = float(update_data["longitude"])
            if "heading_deg" in update_data:
                rec["heading_deg"] = float(update_data["heading_deg"])

            # Update biometrics
            if "ear" in update_data:
                rec["ear"] = float(update_data["ear"])
            if "mar" in update_data:
                rec["mar"] = float(update_data["mar"])
            if "eye_closed_seconds" in update_data:
                rec["eye_closed_seconds"] = float(update_data["eye_closed_seconds"])
            if "is_yawning" in update_data:
                rec["is_yawning"] = bool(update_data["is_yawning"])
            if "microsleep_detected" in update_data:
                rec["microsleep_detected"] = bool(update_data["microsleep_detected"])

            # Risk calculations
            risk_score = float(update_data.get("risk_score", rec.get("risk_score", 0.0)))
            risk_level = update_data.get("risk_level")
            if not risk_level:
                if risk_score >= 70.0:
                    risk_level = "CRITICAL"
                elif risk_score >= 40.0:
                    risk_level = "ELEVATED"
                else:
                    risk_level = "NOMINAL"

            rec["risk_score"] = risk_score
            rec["risk_level"] = risk_level

            # Determine Driver Status
            if risk_level == "CRITICAL" or rec.get("microsleep_detected"):
                rec["driver_status"] = "Critical"
            elif risk_level == "ELEVATED" or rec.get("is_yawning"):
                rec["driver_status"] = "Warning"
            else:
                rec["driver_status"] = "Safe"

            # Vehicle status
            if speed == 0.0 and risk_level == "CRITICAL":
                rec["vehicle_status"] = "SAFE_STOP"
            elif speed == 0.0:
                rec["vehicle_status"] = "STATIONARY"
            else:
                rec["vehicle_status"] = "IN_TRANSIT"

            rec["last_updated"] = now_str

            # Update corresponding vehicle cache
            v_id = rec.get("vehicle_id")
            if v_id and v_id in self._vehicles_map:
                v_rec = self._vehicles_map[v_id]
                v_rec["current_speed_kph"] = speed
                v_rec["current_latitude"] = rec["current_latitude"]
                v_rec["current_longitude"] = rec["current_longitude"]
                v_rec["vehicle_status"] = rec["vehicle_status"]
                v_rec["last_updated"] = now_str

            # Auto-record alert event on critical conditions (debounced)
            if rec["microsleep_detected"]:
                self._record_debounced_event(
                    driver_id=driver_id,
                    vehicle_id=rec.get("vehicle_id", ""),
                    event_type="microsleep",
                    severity="CRITICAL",
                    risk_score=risk_score,
                    speed_kmh=speed,
                    details=f"Microsleep episode detected ({rec.get('eye_closed_seconds', 0):.1f}s eyes closed)"
                )
                rec["drowsiness_events_count"] = int(rec.get("drowsiness_events_count", 0)) + 1

            elif rec.get("is_yawning"):
                self._record_debounced_event(
                    driver_id=driver_id,
                    vehicle_id=rec.get("vehicle_id", ""),
                    event_type="yawn",
                    severity="WARNING",
                    risk_score=risk_score,
                    speed_kmh=speed,
                    details="Sustained / repeated yawning detected"
                )
                rec["yawning_events_count"] = int(rec.get("yawning_events_count", 0)) + 1

            self.persist_database()

            return {
                "driver_id": driver_id,
                "driver_name": rec.get("driver_name"),
                "driver_status": rec["driver_status"],
                "risk_score": rec["risk_score"],
                "risk_level": rec["risk_level"],
                "vehicle_status": rec["vehicle_status"],
                "speed_kmh": rec["current_speed_kph"],
                "last_updated": rec["last_updated"]
            }

    def _record_debounced_event(
        self,
        driver_id: str,
        vehicle_id: str,
        event_type: str,
        severity: str,
        risk_score: float,
        speed_kmh: float,
        details: str
    ):
        """Prevents logging identical events within a 3-second window."""
        now_ts = time.time()
        for e in reversed(self._events[-5:]):
            if (e.get("driver_id") == driver_id and 
                e.get("event_type") == event_type and 
                now_ts - e.get("_epoch", 0) < 3.0):
                return

        event_entry = {
            "id": len(self._events) + 1,
            "_epoch": now_ts,
            "timestamp": _get_utc_iso(),
            "driver_id": driver_id,
            "vehicle_id": vehicle_id,
            "event_type": event_type,
            "severity": severity,
            "risk_score": float(risk_score),
            "speed_kmh": float(speed_kmh),
            "details": details
        }
        self._events.append(event_entry)
        self.persist_events()

    # -------------------------------------------------------------------------
    # Event & Alert Management
    # -------------------------------------------------------------------------
    def add_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Manually creates an event record (e.g. from POST /events)."""
        with self.lock:
            d_id = event_data.get("driver_id", "D001")
            v_id = event_data.get("vehicle_id") or (self._drivers_map.get(d_id, {}).get("vehicle_id", "TRK-001"))
            
            event_entry = {
                "id": len(self._events) + 1,
                "_epoch": time.time(),
                "timestamp": event_data.get("timestamp") or _get_utc_iso(),
                "driver_id": d_id,
                "vehicle_id": v_id,
                "event_type": event_data.get("event_type", "sensor_event"),
                "severity": event_data.get("severity", "INFO").upper(),
                "risk_score": float(event_data.get("risk_score", 0.0)),
                "speed_kmh": float(event_data.get("speed_kmh", 0.0)),
                "details": event_data.get("details", "")
            }
            self._events.append(event_entry)
            self.persist_events()

            # Update driver counters
            if d_id in self._drivers_map:
                rec = self._drivers_map[d_id]
                e_type = event_entry["event_type"].lower()
                if "microsleep" in e_type or "drowsy" in e_type:
                    rec["drowsiness_events_count"] = int(rec.get("drowsiness_events_count", 0)) + 1
                    rec["driver_status"] = "Critical"
                elif "yawn" in e_type:
                    rec["yawning_events_count"] = int(rec.get("yawning_events_count", 0)) + 1
                    if rec.get("driver_status") != "Critical":
                        rec["driver_status"] = "Warning"
                elif "distract" in e_type:
                    rec["distraction_events_count"] = int(rec.get("distraction_events_count", 0)) + 1
                rec["last_updated"] = event_entry["timestamp"]
                self.persist_database()

            # Clean output (without internal _epoch)
            res = dict(event_entry)
            res.pop("_epoch", None)
            return res

    def get_alerts(
        self,
        limit: int = 50,
        severity: Optional[str] = None,
        driver_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Returns filtered alerts/events list ordered from newest to oldest."""
        with self.lock:
            filtered = []
            for e in reversed(self._events):
                if severity and e.get("severity", "").upper() != severity.upper():
                    continue
                if driver_id and e.get("driver_id") != driver_id:
                    continue
                item = dict(e)
                item.pop("_epoch", None)
                filtered.append(item)
                if len(filtered) >= limit:
                    break
            return filtered

    # -------------------------------------------------------------------------
    # Fleet Summary & Aggregates
    # -------------------------------------------------------------------------
    def get_fleet_summary(self) -> Dict[str, Any]:
        """Calculates global fleet metrics for Fleet Manager dashboard."""
        with self.lock:
            total_drivers = len(self._drivers_map)
            total_vehicles = len(self._vehicles_map)

            safe_count = 0
            warning_count = 0
            critical_count = 0
            risk_sum = 0.0
            active_vehicles = 0

            for rec in self._drivers_map.values():
                status = rec.get("driver_status", "Safe")
                if status == "Critical":
                    critical_count += 1
                elif status == "Warning":
                    warning_count += 1
                else:
                    safe_count += 1
                risk_sum += float(rec.get("risk_score", 0.0))

            for v_rec in self._vehicles_map.values():
                if v_rec.get("vehicle_status") == "IN_TRANSIT" or float(v_rec.get("current_speed_kph", 0)) > 0:
                    active_vehicles += 1

            avg_risk = round(risk_sum / total_drivers, 1) if total_drivers > 0 else 0.0

            return {
                "total_vehicles": total_vehicles,
                "active_vehicles": active_vehicles,
                "total_drivers": total_drivers,
                "safe_drivers_count": safe_count,
                "warning_drivers_count": warning_count,
                "critical_drivers_count": critical_count,
                "average_risk_score": avg_risk,
                "recent_alerts_count": len(self._events),
                "system_status": "ONLINE",
                "database_connected": True,
                "database_file": "data/fleet_database.json",
                "last_sync_timestamp": _get_utc_iso()
            }

    # -------------------------------------------------------------------------
    # Manager Dispatch Directives Queue
    # -------------------------------------------------------------------------
    def add_command(self, cmd_data: Dict[str, Any]) -> Dict[str, Any]:
        """Logs a manager supervisory command (safe stop, cabin audio, etc.)."""
        with self.lock:
            cmd_entry = {
                "id": len(self._commands) + 1,
                "timestamp": cmd_data.get("timestamp") or _get_utc_iso(),
                "vehicle_id": cmd_data.get("vehicle_id", "TN 58 AA 4920"),
                "command_type": cmd_data.get("command_type", "NOTIFICATION"),
                "message": cmd_data.get("message", ""),
                "status": "DISPATCHED"
            }
            self._commands.append(cmd_entry)
            self.persist_commands()
            return cmd_entry

    def get_commands(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns recent manager supervisory commands."""
        with self.lock:
            return list(reversed(self._commands[-limit:]))


# Global singleton instance
_repository_instance: Optional[JSONRepository] = None


def get_repository() -> JSONRepository:
    """Returns or creates the shared JSONRepository instance."""
    global _repository_instance
    if _repository_instance is None:
        _repository_instance = JSONRepository()
    return _repository_instance
