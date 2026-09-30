"""
Fleet Dashboard Escalation & Telematics Sync Module
Features:
1. SQLite Database integration for logging high-frequency vehicle telemetry and alerts.
2. Synchronizes to primary `fleet_mind.db` enterprise database and `data/fleet_telematics.db`.
3. Real-time JSON export (`fleet_live_state.json`) for downstream Manager Console sync.
4. Manager Remote Command dispatch and acknowledgment queue across both databases.
5. Entity query interfaces for Vehicle Registry, Driver Profiles, and Active Trips from SQLite.
"""

import os
import json
import sqlite3
import datetime


class FleetSyncManager:
    """
    Manages local SQLite telemetry storage and real-time JSON payload publishing
    for fleet integration and manager command dispatch.
    """

    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "fleet_telematics.db")
    MIND_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fleet_mind.db")
    JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fleet_live_state.json")

    def __init__(self, vehicle_id: str = "TN 58 AA 4920", driver_name: str = "Arun Kumar (Operator #104)"):
        self.vehicle_id = vehicle_id
        self.driver_name = driver_name
        self._init_sqlite()

    def _init_sqlite(self):
        """Initializes SQLite database schemas for telemetry, escalations, and manager commands."""
        os.makedirs(os.path.dirname(self.DB_PATH), exist_ok=True)
        with sqlite3.connect(self.DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Telematics time-series stream with GPS
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS telematics_stream (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                vehicle_id TEXT NOT NULL,
                driver_name TEXT NOT NULL,
                speed_kmh REAL,
                acceleration_kmh_s REAL,
                latitude REAL,
                longitude REAL,
                heading_deg REAL,
                distance_covered_km REAL,
                ear REAL,
                mar REAL,
                risk_score REAL,
                risk_level TEXT,
                intervention_status TEXT,
                escalation_flag INTEGER,
                driver_action TEXT
            )
            """)

            # Fleet Escalation incident logs
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS escalation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                vehicle_id TEXT NOT NULL,
                driver_name TEXT NOT NULL,
                speed_kmh REAL,
                risk_score REAL,
                latitude REAL,
                longitude REAL,
                trigger_reason TEXT,
                dispatch_status TEXT,
                payload_json TEXT
            )
            """)

            # Fleet Manager Remote Interventions / Command Queue
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS manager_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                vehicle_id TEXT NOT NULL,
                command_type TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stream_ts ON telematics_stream(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_esc_ts ON escalation_events(timestamp)")
            conn.commit()

    def sync_telematics_frame(
        self,
        telematics_data: dict,
        vision_data: dict,
        risk_data: dict
    ) -> dict:
        """
        Records the current state into SQLite databases and updates the live JSON payload.
        """
        now_iso = datetime.datetime.utcnow().isoformat() + "Z"
        speed = telematics_data.get("speed_kmh", 0.0)
        accel = telematics_data.get("acceleration_kmh_s", 0.0)
        lat = telematics_data.get("latitude", 11.2335)
        lon = telematics_data.get("longitude", 78.8817)
        heading = telematics_data.get("heading_deg", 38.0)
        dist_covered = telematics_data.get("distance_covered_km", 218.0)
        rem_km = telematics_data.get("remaining_km", 244.0)
        eta_min = telematics_data.get("eta_minutes", 185.0)

        ear = vision_data.get("ear", 0.30)
        mar = vision_data.get("mar", 0.25)
        risk_score = risk_data.get("risk_score", 0.0)
        risk_level = risk_data.get("risk_level", "NOMINAL")
        intervention_status = risk_data.get("intervention_status", "MONITORING")
        is_escalated = 1 if risk_data.get("is_escalated", False) else 0
        driver_action = risk_data.get("driver_action", "Nominal transit on NH 45")

        # 1. Update primary data/fleet_telematics.db
        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO telematics_stream (
                    timestamp, vehicle_id, driver_name, speed_kmh, acceleration_kmh_s,
                    latitude, longitude, heading_deg, distance_covered_km,
                    ear, mar, risk_score, risk_level, intervention_status,
                    escalation_flag, driver_action
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    now_iso, self.vehicle_id, self.driver_name, speed, accel,
                    lat, lon, heading, dist_covered,
                    ear, mar, risk_score, risk_level, intervention_status,
                    is_escalated, driver_action
                ))

                if is_escalated == 1:
                    cursor.execute("""
                    INSERT INTO escalation_events (
                        timestamp, vehicle_id, driver_name, speed_kmh, risk_score,
                        latitude, longitude, trigger_reason, dispatch_status, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        now_iso, self.vehicle_id, self.driver_name, speed, risk_score,
                        lat, lon,
                        "Operator unassisted under critical fatigue risk (Speed > 0 km/h)",
                        "ACTIVE_DISPATCH_ALERT",
                        json.dumps({
                            "vehicle_id": self.vehicle_id,
                            "speed": speed,
                            "risk_score": risk_score,
                            "latitude": lat,
                            "longitude": lon,
                            "driver_action": driver_action
                        })
                    ))

                conn.commit()
        except Exception:
            pass

        # 2. Also sync to enterprise fleet_mind.db
        try:
            if os.path.exists(self.MIND_DB_PATH):
                with sqlite3.connect(self.MIND_DB_PATH) as conn_mind:
                    c_mind = conn_mind.cursor()
                    # Insert into telematics table
                    c_mind.execute("""
                    INSERT INTO telematics (
                        timestamp, vehicle_id, driver_name, speed_kmh, acceleration_kmh_s,
                        latitude, longitude, heading_deg, throttle_pct, brake_pct,
                        rpm, gear, engine_temp_c, ear, mar, fatigue_score, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        now_iso, self.vehicle_id, self.driver_name, speed, accel,
                        lat, lon, heading,
                        telematics_data.get("throttle_pct", 40.0),
                        telematics_data.get("brake_pct", 0.0),
                        telematics_data.get("rpm", 1450),
                        telematics_data.get("gear", 7),
                        telematics_data.get("engine_temp_c", 88.5),
                        ear, mar, risk_score, "CRITICAL" if is_escalated else "NOMINAL"
                    ))

                    # Insert into telematics_stream
                    c_mind.execute("""
                    INSERT INTO telematics_stream (
                        timestamp, vehicle_id, driver_name, speed_kmh, acceleration_kmh_s,
                        latitude, longitude, heading_deg, distance_covered_km,
                        ear, mar, risk_score, risk_level, intervention_status,
                        escalation_flag, driver_action
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        now_iso, self.vehicle_id, self.driver_name, speed, accel,
                        lat, lon, heading, dist_covered,
                        ear, mar, risk_score, risk_level, intervention_status,
                        is_escalated, driver_action
                    ))

                    if is_escalated == 1:
                        c_mind.execute("""
                        INSERT INTO escalation_events (
                            timestamp, vehicle_id, driver_name, speed_kmh, risk_score,
                            latitude, longitude, trigger_reason, dispatch_status, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            now_iso, self.vehicle_id, self.driver_name, speed, risk_score,
                            lat, lon,
                            "Operator unassisted under critical fatigue risk (Speed > 0 km/h)",
                            "ACTIVE_DISPATCH_ALERT",
                            json.dumps({
                                "vehicle_id": self.vehicle_id,
                                "speed": speed,
                                "risk_score": risk_score,
                                "latitude": lat,
                                "longitude": lon,
                                "driver_action": driver_action
                            })
                        ))

                    conn_mind.commit()
        except Exception:
            pass

        # 3. Update Comprehensive JSON State Payload
        payload = {
            "version": "2.4.0",
            "last_sync_timestamp": now_iso,
            "vehicle": {
                "id": self.vehicle_id,
                "vin": "MB1T2H4A0NP492011",
                "make_model": "Ashok Leyland 4220 HG (14-Wheeler Heavy Commercial Hauler)",
                "engine_status": "RUNNING" if speed > 0 else "IDLE",
                "status": "IN_TRANSIT" if speed > 0 else "STATIONARY",
                "fuel_battery_percent": 78.5,
                "engine_temp_c": telematics_data.get("engine_temp_c", 88.5),
                "tire_pressure_psi": 115.0,
                "odometer_km": 184200 + round(dist_covered, 1)
            },
            "driver": {
                "name": self.driver_name,
                "license": "TN-58-2016-0049281 (Heavy Commercial Freight CDL)",
                "hos_driving_hours": 5.2,
                "hos_max_hours": 10.0,
                "safety_score": 96.4,
                "safety_grade": "A+",
                "medical_cert_valid": True
            },
            "trip": {
                "route_id": "TN-MDU-MAA-NH45",
                "origin": "Madurai Mattuthavani Freight Terminal",
                "destination": "Chennai Madhavaram Central Logistics Hub",
                "cargo_description": "Automotive Spares & Precision Castings (18.5 MT)",
                "cargo_temp_c": 26.8,
                "total_route_km": 462.0,
                "distance_covered_km": dist_covered,
                "remaining_km": rem_km,
                "eta_minutes": eta_min,
                "progress_percent": round((dist_covered / 462.0) * 100.0, 1)
            },
            "gps": {
                "latitude": lat,
                "longitude": lon,
                "heading_deg": heading,
                "route_waypoints": telematics_data.get("route_waypoints", [])
            },
            "telematics": {
                "speed_kmh": speed,
                "acceleration_kmh_s": accel,
                "is_overspeeding": telematics_data.get("is_overspeeding", False),
                "is_hard_braking": telematics_data.get("is_hard_braking", False),
                "total_hard_brakes": telematics_data.get("total_hard_brakes", 0),
                "throttle_pct": telematics_data.get("throttle_pct", 40.0),
                "brake_pct": telematics_data.get("brake_pct", 0.0),
                "rpm": telematics_data.get("rpm", 1450),
                "gear": telematics_data.get("gear", 7)
            },
            "biometrics": {
                "ear": ear,
                "mar": mar,
                "microsleep_detected": vision_data.get("microsleep_detected", False),
                "eye_closed_seconds": vision_data.get("eye_closed_duration", 0.0),
                "is_yawning": vision_data.get("is_yawning", False),
                "total_yawns": vision_data.get("total_yawns", 0)
            },
            "intervention": {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "intervention_status": intervention_status,
                "escalation_flag": bool(is_escalated),
                "driver_action": driver_action,
                "seconds_in_alert": risk_data.get("seconds_in_alert", 0.0)
            }
        }

        try:
            with open(self.JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass

        return payload

    def send_manager_command(self, command_type: str, message: str) -> bool:
        """Fleet Manager dispatches an active command to the vehicle across SQLite databases."""
        now_iso = datetime.datetime.utcnow().isoformat() + "Z"
        success = False

        # 1. Write to data/fleet_telematics.db
        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO manager_commands (timestamp, vehicle_id, command_type, message, status)
                VALUES (?, ?, ?, ?, ?)
                """, (now_iso, self.vehicle_id, command_type, message, "PENDING_DRIVER_ACK"))
                conn.commit()
                success = True
        except Exception:
            pass

        # 2. Write to fleet_mind.db
        try:
            if os.path.exists(self.MIND_DB_PATH):
                with sqlite3.connect(self.MIND_DB_PATH) as conn_mind:
                    c_mind = conn_mind.cursor()
                    c_mind.execute("""
                    INSERT INTO manager_commands (timestamp, vehicle_id, command_type, message, status)
                    VALUES (?, ?, ?, ?, ?)
                    """, (now_iso, self.vehicle_id, command_type, message, "PENDING_DRIVER_ACK"))
                    conn_mind.commit()
                    success = True
        except Exception:
            pass

        # When acknowledging or resetting, immediately clear lingering emergency flags
        if command_type in ["ACKNOWLEDGE", "CLEAR_ALERT", "RESET"]:
            try:
                if os.path.exists(self.JSON_PATH):
                    with open(self.JSON_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    data["intervention"]["risk_score"] = 5.0
                    data["intervention"]["risk_level"] = "NOMINAL"
                    data["intervention"]["intervention_status"] = "MONITORING"
                    data["intervention"]["escalation_flag"] = False
                    data["intervention"]["driver_action"] = "Alert acknowledged and cleared by dispatch"
                    data["biometrics"]["microsleep_detected"] = False
                    data["biometrics"]["is_yawning"] = False
                    data["biometrics"]["eye_closed_seconds"] = 0.0
                    with open(self.JSON_PATH, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
            except Exception:
                pass

        return success

    def fetch_manager_commands(self, limit: int = 5) -> list:
        """Fetches active commands sent from the manager."""
        target_db = self.MIND_DB_PATH if os.path.exists(self.MIND_DB_PATH) else self.DB_PATH
        try:
            with sqlite3.connect(target_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(f"""
                SELECT id, timestamp, vehicle_id, command_type, message, status
                FROM manager_commands
                ORDER BY id DESC
                LIMIT {limit}
                """)
                return [dict(r) for r in cursor.fetchall()]
        except Exception:
            return []

    def fetch_recent_telematics(self, limit: int = 15) -> list:
        """Retrieves recent stream records as list of dictionaries."""
        target_db = self.MIND_DB_PATH if os.path.exists(self.MIND_DB_PATH) else self.DB_PATH
        try:
            with sqlite3.connect(target_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(f"""
                SELECT timestamp, speed_kmh, acceleration_kmh_s, latitude, longitude, ear, mar, risk_score, risk_level, intervention_status, escalation_flag
                FROM telematics_stream
                ORDER BY id DESC
                LIMIT {limit}
                """)
                return [dict(r) for r in cursor.fetchall()]
        except Exception:
            return []

    def fetch_recent_escalations(self, limit: int = 10) -> list:
        """Retrieves recent escalation incidents."""
        target_db = self.MIND_DB_PATH if os.path.exists(self.MIND_DB_PATH) else self.DB_PATH
        try:
            with sqlite3.connect(target_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(f"""
                SELECT timestamp, vehicle_id, speed_kmh, risk_score, latitude, longitude, trigger_reason, dispatch_status
                FROM escalation_events
                ORDER BY id DESC
                LIMIT {limit}
                """)
                return [dict(r) for r in cursor.fetchall()]
        except Exception:
            return []

    def fetch_vehicle_from_db(self) -> dict:
        """Fetches vehicle details directly from vehicle_registry in fleet_mind.db."""
        if not os.path.exists(self.MIND_DB_PATH):
            return {}
        try:
            with sqlite3.connect(self.MIND_DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM vehicle_registry LIMIT 1")
                row = cur.fetchone()
                return dict(row) if row else {}
        except Exception:
            return {}

    def fetch_driver_from_db(self) -> dict:
        """Fetches driver profile directly from driver_profiles in fleet_mind.db."""
        if not os.path.exists(self.MIND_DB_PATH):
            return {}
        try:
            with sqlite3.connect(self.MIND_DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM driver_profiles LIMIT 1")
                row = cur.fetchone()
                return dict(row) if row else {}
        except Exception:
            return {}

    def fetch_trip_from_db(self) -> dict:
        """Fetches active trip manifest directly from trips in fleet_mind.db."""
        if not os.path.exists(self.MIND_DB_PATH):
            return {}
        try:
            with sqlite3.connect(self.MIND_DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM trips LIMIT 1")
                row = cur.fetchone()
                return dict(row) if row else {}
        except Exception:
            return {}

    def fetch_db_stats(self) -> dict:
        """Fetches live table counts and SQLite file size for fleet_mind.db."""
        if not os.path.exists(self.MIND_DB_PATH):
            return {"connected": False, "size_kb": 0, "telematics_count": 0, "stream_count": 0}
        try:
            size_kb = round(os.path.getsize(self.MIND_DB_PATH) / 1024.0, 1)
            with sqlite3.connect(self.MIND_DB_PATH) as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM telematics")
                telem_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM telematics_stream")
                stream_count = cur.fetchone()[0]
                return {
                    "connected": True,
                    "size_kb": size_kb,
                    "telematics_count": telem_count,
                    "stream_count": stream_count,
                    "db_name": "fleet_mind.db"
                }
        except Exception:
            return {"connected": False, "size_kb": 0, "telematics_count": 0, "stream_count": 0}
