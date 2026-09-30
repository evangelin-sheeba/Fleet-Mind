"""
Speedometer & Telematics Analysis Module
Features:
1. SQLite Database integration: Can stream and step directly through fleet_mind.db telematics records.
2. Background vehicle physics simulator (speed km/h, acceleration km/h/s).
3. Live GPS route simulator (interpolates latitude, longitude, heading, ETA along active route).
4. Overspeeding detection (> 80 km/h).
5. Sudden / Hard Braking detection (-15 to -20 km/h/s deceleration).
6. Scenario presets: Cruise, High Speed, Hard Brake, Pull-Over to 0 km/h.
7. Telemetry history buffer for trend graphing.
"""

import os
import time
import collections
import random
import math
import sqlite3


class TelematicsModule:
    """
    Vehicle Telematics simulator, dynamic metrics analyzer, and GPS tracker.
    Supports live database streaming from fleet_mind.db and physics simulation fallback.
    """

    OVERSPEED_LIMIT_KMH = 80.0
    HARD_BRAKE_THRESHOLD_KMH_S = -15.0  # Deceleration of -15 to -20 km/h/s

    # Grand Southern Trunk Road / NH 45 & NH 38 (Madurai -> Tiruchirappalli -> Chennai)
    ROUTE_WAYPOINTS = [
        (9.9325, 78.1633),   # Madurai Mattuthavani Freight Terminal
        (10.0336, 78.3370),  # Melur Toll Plaza
        (10.3673, 78.4800),  # Thuvarankurichi Waypoint
        (10.6033, 78.5436),  # Viralimalai Industrial Zone
        (10.7905, 78.7047),  # Tiruchirappalli (Trichy) Bypass Hub
        (10.9238, 78.7397),  # Samayapuram Expressway Gate
        (11.2335, 78.8817),  # Perambalur Freight Stop
        (11.6917, 79.2900),  # Ulundurpet NH 45 Junction
        (11.9401, 79.4861),  # Villupuram Bypass Depot
        (12.2333, 79.6500),  # Tindivanam Logistics Hub
        (12.4333, 79.8333),  # Melmaruvathur Waypoint
        (12.6819, 79.9888),  # Chengalpattu Toll Plaza
        (12.9249, 80.1000),  # Tambaram Southern Freight Gateway
        (13.0827, 80.2707),  # Chennai Madhavaram Central Freight Complex
    ]
    TOTAL_ROUTE_KM = 462.0
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fleet_mind.db")

    def __init__(self, initial_speed: float = 68.0, history_len: int = 50, use_db_playback: bool = False):
        self.current_speed = float(initial_speed)
        self.target_speed = float(initial_speed)
        self.current_acceleration = 0.0  # km/h per second
        self.last_update_time = time.time()

        # Database playback configuration
        self.use_db_playback = use_db_playback
        self.db_playback_idx = 0
        self.total_db_records = 0

        # CAN-bus auxiliary metrics
        self.throttle_pct = 40.0
        self.brake_pct = 0.0
        self.rpm = 1450
        self.gear = 7
        self.engine_temp_c = 88.5

        # Telemetry history buffer
        self.history_len = history_len
        self.speed_history = collections.deque(maxlen=history_len)
        self.accel_history = collections.deque(maxlen=history_len)
        self.time_history = collections.deque(maxlen=history_len)

        # Event flags
        self.is_overspeeding = False
        self.is_hard_braking = False
        self.hard_brake_start_time = None
        self.last_hard_brake_time = None
        self.total_hard_brakes = 0

        # GPS & Trip Progress State (Madurai -> Chennai corridor)
        self.distance_covered_km = 218.0  # Approaching Perambalur on NH 45 (~47% progress)
        self.current_lat = 11.2335
        self.current_lon = 78.8817
        self.heading_deg = 38.0

        # Prime history
        now = time.time()
        for i in range(history_len):
            t = now - (history_len - i) * 0.2
            self.speed_history.append(self.current_speed)
            self.accel_history.append(0.0)
            self.time_history.append(t)

        self._check_db_capacity()

    def _check_db_capacity(self):
        """Checks if SQLite database exists and counts records."""
        if os.path.exists(self.DB_PATH):
            try:
                with sqlite3.connect(self.DB_PATH) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM telematics")
                    self.total_db_records = cur.fetchone()[0]
            except Exception:
                self.total_db_records = 0

    def enable_db_playback(self, enable: bool = True, start_idx: int = 0):
        """Enables or disables sequential playback from fleet_mind.db."""
        self.use_db_playback = enable
        self.db_playback_idx = max(0, start_idx)
        self._check_db_capacity()

    def reset(self, initial_speed: float = 68.0):
        """Resets telematics flags and speeds to nominal cruising state."""
        self.current_speed = float(initial_speed)
        self.target_speed = float(initial_speed)
        self.current_acceleration = 0.0
        self.is_overspeeding = False
        self.is_hard_braking = False
        self.hard_brake_start_time = None
        self.last_hard_brake_time = None
        self.total_hard_brakes = 0
        self.use_db_playback = False

    def set_target_speed(self, speed_kmh: float):
        """Sets the desired speed for vehicle physics targeting."""
        self.use_db_playback = False
        self.target_speed = max(0.0, float(speed_kmh))

    def trigger_preset_scenario(self, scenario: str):
        """
        Activates preset driving situations:
        - 'cruise': 72 km/h smooth
        - 'overspeed': 94 km/h highway sprint
        - 'hard_brake': Sudden slam on brakes (-18 km/h/s)
        - 'safe_stop': Controlled deceleration until exact 0 km/h
        - 'city_traffic': Variable 42 km/h
        - 'db_stream': Switch to active SQLite database streaming
        """
        if scenario == "db_stream":
            self.enable_db_playback(True)
            return

        self.use_db_playback = False
        if scenario == "cruise":
            self.target_speed = 72.0
        elif scenario == "overspeed":
            self.target_speed = 94.0
        elif scenario == "hard_brake":
            self.target_speed = max(0.0, self.current_speed - 25.0)
        elif scenario == "safe_stop":
            self.target_speed = 0.0
        elif scenario == "city_traffic":
            self.target_speed = 42.0

    def _fetch_next_db_record(self) -> dict:
        """Fetches the next row from telematics table in fleet_mind.db."""
        if not os.path.exists(self.DB_PATH) or self.total_db_records == 0:
            return None

        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                row_id = (self.db_playback_idx % self.total_db_records) + 1
                cur.execute("""
                SELECT speed_kmh, acceleration_kmh_s, latitude, longitude, heading_deg,
                       throttle_pct, brake_pct, rpm, gear, engine_temp_c
                FROM telematics WHERE id = ?
                """, (row_id,))
                row = cur.fetchone()
                if row:
                    self.db_playback_idx += 1
                    return dict(row)
        except Exception:
            return None
        return None

    def _update_gps_coordinates(self, dt: float):
        """Advances vehicle coordinates along planned route waypoints."""
        dist_delta = (self.current_speed / 3600.0) * dt
        self.distance_covered_km = min(self.TOTAL_ROUTE_KM, self.distance_covered_km + dist_delta)

        # Calculate progress ratio [0.0, 1.0]
        progress_ratio = self.distance_covered_km / self.TOTAL_ROUTE_KM
        n_segments = len(self.ROUTE_WAYPOINTS) - 1
        segment_index = min(n_segments - 1, int(progress_ratio * n_segments))
        segment_t = (progress_ratio * n_segments) - segment_index

        p1 = self.ROUTE_WAYPOINTS[segment_index]
        p2 = self.ROUTE_WAYPOINTS[segment_index + 1]

        # Linear interpolation between waypoints
        self.current_lat = round(p1[0] + (p2[0] - p1[0]) * segment_t, 5)
        self.current_lon = round(p1[1] + (p2[1] - p1[1]) * segment_t, 5)

        # Calculate heading
        dy = p2[0] - p1[0]
        dx = (p2[1] - p1[1]) * math.cos(math.radians(p1[0]))
        heading = math.degrees(math.atan2(dx, dy))
        if heading < 0:
            heading += 360
        self.heading_deg = round(heading, 1)

    def step(self, dt: float = None) -> dict:
        """
        Steps the vehicle physics and GPS forward by dt seconds.
        Can step from SQLite database playback if enabled, or simulate dynamically.
        """
        now = time.time()
        if dt is None:
            dt = max(0.01, min(0.5, now - self.last_update_time))
        self.last_update_time = now

        prev_speed = self.current_speed

        if self.use_db_playback:
            rec = self._fetch_next_db_record()
            if rec:
                self.current_speed = float(rec.get("speed_kmh", self.current_speed))
                self.current_acceleration = float(rec.get("acceleration_kmh_s", 0.0))
                self.current_lat = float(rec.get("latitude", self.current_lat))
                self.current_lon = float(rec.get("longitude", self.current_lon))
                self.heading_deg = float(rec.get("heading_deg", self.heading_deg))
                self.throttle_pct = float(rec.get("throttle_pct", 40.0))
                self.brake_pct = float(rec.get("brake_pct", 0.0))
                self.rpm = int(rec.get("rpm", 1450))
                self.gear = int(rec.get("gear", 7))
                self.engine_temp_c = float(rec.get("engine_temp_c", 88.5))
            else:
                self.use_db_playback = False

        if not self.use_db_playback:
            # Physics interpolation
            diff = self.target_speed - self.current_speed

            if self.target_speed == 0.0 and self.current_speed <= 3.0:
                self.current_speed = 0.0
            elif diff < -12.0:
                braking_rate = -17.5 + random.uniform(-1.5, 1.5)
                self.current_speed += braking_rate * dt
                if self.current_speed < self.target_speed:
                    self.current_speed = self.target_speed
            elif abs(diff) < 0.3:
                if self.target_speed == 0.0:
                    self.current_speed = 0.0
                else:
                    jitter = random.uniform(-0.4, 0.4)
                    self.current_speed = max(0.0, self.target_speed + jitter)
            else:
                rate = 5.5 if diff > 0 else -6.0
                self.current_speed += rate * dt
                if (diff > 0 and self.current_speed > self.target_speed) or (diff < 0 and self.current_speed < self.target_speed):
                    self.current_speed = self.target_speed

            self.current_speed = round(max(0.0, min(140.0, self.current_speed)), 1)
            self.current_acceleration = round((self.current_speed - prev_speed) / dt, 2)
            self._update_gps_coordinates(dt)

        # Rule 1: Overspeeding (> 80 km/h)
        self.is_overspeeding = self.current_speed > self.OVERSPEED_LIMIT_KMH

        # Rule 2: Sudden / Hard Braking (deceleration of -15 to -20 km/h/s)
        if self.current_acceleration <= self.HARD_BRAKE_THRESHOLD_KMH_S:
            if not self.is_hard_braking:
                self.is_hard_braking = True
                self.total_hard_brakes += 1
                self.last_hard_brake_time = now
        else:
            if self.last_hard_brake_time and (now - self.last_hard_brake_time > 1.5):
                self.is_hard_braking = False

        # Calculate remaining ETA
        remaining_km = max(0.0, self.TOTAL_ROUTE_KM - self.distance_covered_km)
        effective_speed = max(25.0, self.current_speed)
        eta_minutes = round((remaining_km / effective_speed) * 60.0, 1)

        # Store in history
        self.speed_history.append(self.current_speed)
        self.accel_history.append(self.current_acceleration)
        self.time_history.append(now)

        return {
            "speed_kmh": self.current_speed,
            "target_speed": self.target_speed,
            "acceleration_kmh_s": self.current_acceleration,
            "is_overspeeding": bool(self.is_overspeeding),
            "is_hard_braking": bool(self.is_hard_braking),
            "total_hard_brakes": int(self.total_hard_brakes),
            "speed_history": list(self.speed_history),
            "accel_history": list(self.accel_history),
            # GPS & Trip Telemetry
            "latitude": self.current_lat,
            "longitude": self.current_lon,
            "heading_deg": self.heading_deg,
            "distance_covered_km": round(self.distance_covered_km, 1),
            "remaining_km": round(remaining_km, 1),
            "total_route_km": self.TOTAL_ROUTE_KM,
            "eta_minutes": eta_minutes,
            "route_waypoints": self.ROUTE_WAYPOINTS,
            # CAN-bus channels
            "throttle_pct": self.throttle_pct,
            "brake_pct": self.brake_pct,
            "rpm": self.rpm,
            "gear": self.gear,
            "engine_temp_c": self.engine_temp_c,
            "db_playback_active": self.use_db_playback
        }
