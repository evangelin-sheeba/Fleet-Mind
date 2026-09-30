"""
db_setup.py: Enterprise SQLite Database Initializer for FLEETGUARD SENTINEL.
Populates fleet_mind.db with:
1. vehicle_registry (Commercial fleet specs & telemetry status)
2. driver_profiles (Operator credentials, HOS compliance, safety grades)
3. trips (Madurai -> Chennai active corridor manifest)
4. telematics (Complete 1,250+ row time-series from telematics.csv)
5. telematics_stream (High-frequency live polling table)
6. escalation_events & manager_commands (Audit and intervention queues)
"""

import os
import sqlite3
import pandas as pd

CSV_PATH = "telematics.csv"
DB_PATH = "fleet_mind.db"

def setup_database():
    if not os.path.exists(CSV_PATH):
        # Generate if missing
        import generate_dataset
        print(f"[*] {CSV_PATH} not found. Generating complete dataset...")
        df = generate_dataset.generate_telematics_data()
        df.to_csv(CSV_PATH, index=False)
    else:
        df = pd.read_csv(CSV_PATH)

    print(f"[*] Loading {len(df)} telematics records from {CSV_PATH}...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Drop existing tables for a clean rebuild
    cursor.execute("DROP TABLE IF EXISTS vehicle_registry")
    cursor.execute("DROP TABLE IF EXISTS driver_profiles")
    cursor.execute("DROP TABLE IF EXISTS trips")
    cursor.execute("DROP TABLE IF EXISTS telematics")
    cursor.execute("DROP TABLE IF EXISTS telematics_stream")
    cursor.execute("DROP TABLE IF EXISTS escalation_events")
    cursor.execute("DROP TABLE IF EXISTS manager_commands")

    # 1. Vehicle Registry
    cursor.execute("""
    CREATE TABLE vehicle_registry (
        vehicle_id TEXT PRIMARY KEY,
        vin TEXT NOT NULL,
        make_model TEXT NOT NULL,
        plate_state TEXT NOT NULL,
        status TEXT NOT NULL,
        fuel_battery_percent REAL NOT NULL,
        engine_temp_c REAL NOT NULL,
        oil_pressure_psi REAL NOT NULL,
        tire_pressure_psi REAL NOT NULL,
        odometer_km REAL NOT NULL
    )
    """)

    cursor.execute("""
    INSERT INTO vehicle_registry VALUES (
        'TN 58 AA 4920',
        'MB1T2H4A0NP492011',
        'Ashok Leyland 4220 HG (14-Wheeler Heavy Commercial Hauler)',
        'Tamil Nadu',
        'IN_TRANSIT',
        78.5,
        88.5,
        55.0,
        115.0,
        184218.0
    )
    """)

    # 2. Driver Profiles
    cursor.execute("""
    CREATE TABLE driver_profiles (
        driver_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        license_no TEXT NOT NULL,
        phone TEXT NOT NULL,
        hos_driving_hours REAL NOT NULL,
        hos_max_hours REAL NOT NULL,
        safety_score REAL NOT NULL,
        safety_grade TEXT NOT NULL,
        medical_cert_valid INTEGER NOT NULL
    )
    """)

    cursor.execute("""
    INSERT INTO driver_profiles VALUES (
        'DRV-104',
        'Arun Kumar (Operator #104)',
        'TN-58-2016-0049281 (Heavy Commercial Freight CDL)',
        '+91 98401 24920',
        5.2,
        10.0,
        96.4,
        'A+',
        1
    )
    """)

    # 3. Active Trips Manifest
    cursor.execute("""
    CREATE TABLE trips (
        trip_id TEXT PRIMARY KEY,
        vehicle_id TEXT NOT NULL,
        driver_id TEXT NOT NULL,
        origin TEXT NOT NULL,
        destination TEXT NOT NULL,
        highway_corridor TEXT NOT NULL,
        cargo_description TEXT NOT NULL,
        cargo_temp_c REAL NOT NULL,
        total_route_km REAL NOT NULL,
        distance_covered_km REAL NOT NULL,
        remaining_km REAL NOT NULL,
        eta_minutes REAL NOT NULL,
        progress_percent REAL NOT NULL,
        fastag_status TEXT NOT NULL,
        FOREIGN KEY(vehicle_id) REFERENCES vehicle_registry(vehicle_id),
        FOREIGN KEY(driver_id) REFERENCES driver_profiles(driver_id)
    )
    """)

    cursor.execute("""
    INSERT INTO trips VALUES (
        'TRIP-TN-MDU-MAA-2026-0042',
        'TN 58 AA 4920',
        'DRV-104',
        'Madurai Mattuthavani Freight Terminal',
        'Chennai Madhavaram Central Logistics Hub',
        'NH 45 / NH 38 GST Expressway Corridor',
        'Automotive Spares & Precision Castings (18.5 MT)',
        26.8,
        462.0,
        218.0,
        244.0,
        185.0,
        47.2,
        'ACTIVE // SAMAYAPURAM TOLL PAID'
    )
    """)

    # 4. Telematics Time-Series Table
    cursor.execute("""
    CREATE TABLE telematics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        vehicle_id TEXT NOT NULL,
        driver_name TEXT NOT NULL,
        speed_kmh REAL NOT NULL,
        acceleration_kmh_s REAL,
        latitude REAL,
        longitude REAL,
        heading_deg REAL,
        throttle_pct REAL,
        brake_pct REAL,
        rpm INTEGER,
        gear INTEGER,
        engine_temp_c REAL,
        ear REAL,
        mar REAL,
        fatigue_score REAL,
        status TEXT
    )
    """)

    # 5. Telematics Stream Table
    cursor.execute("""
    CREATE TABLE telematics_stream (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        vehicle_id TEXT NOT NULL,
        driver_name TEXT NOT NULL,
        speed_kmh REAL NOT NULL,
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

    # 6. Escalation Events Table
    cursor.execute("""
    CREATE TABLE escalation_events (
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

    # 7. Manager Remote Commands Table
    cursor.execute("""
    CREATE TABLE manager_commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        vehicle_id TEXT NOT NULL,
        command_type TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL
    )
    """)

    # Insert Dataset into telematics
    df.to_sql("telematics", conn, if_exists="append", index=False)

    # Initialize telematics_stream from dataset
    stream_df = df.copy()
    stream_df = stream_df.rename(columns={"fatigue_score": "risk_score"})
    stream_df["distance_covered_km"] = [round((i / (len(stream_df) - 1)) * 462.0, 1) for i in range(len(stream_df))]
    stream_df["risk_level"] = stream_df["status"].apply(lambda s: "CRITICAL" if s == "CRITICAL" else ("ELEVATED" if s == "WARNING" else "NOMINAL"))
    stream_df["intervention_status"] = stream_df["status"].apply(lambda s: "ESCALATED" if s == "CRITICAL" else "MONITORING")
    stream_df["escalation_flag"] = stream_df["status"].apply(lambda s: 1 if s == "CRITICAL" else 0)
    stream_df["driver_action"] = stream_df["status"].apply(
        lambda s: "EMERGENCY: Pull Over & Halt" if s == "CRITICAL" else ("Driver drowsy - warning tone sounded" if s == "WARNING" else "Nominal transit on NH 45")
    )

    stream_cols = [
        "timestamp", "vehicle_id", "driver_name", "speed_kmh", "acceleration_kmh_s",
        "latitude", "longitude", "heading_deg", "distance_covered_km", "ear", "mar",
        "risk_score", "risk_level", "intervention_status", "escalation_flag", "driver_action"
    ]
    stream_df[stream_cols].to_sql("telematics_stream", conn, if_exists="append", index=False)

    # Performance Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_telem_ts ON telematics(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_telem_veh ON telematics(vehicle_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_telem_spd ON telematics(speed_kmh)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stream_ts ON telematics_stream(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_esc_ts ON escalation_events(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cmd_ts ON manager_commands(timestamp)")

    conn.commit()

    # Verification query
    cursor.execute("SELECT COUNT(*) FROM telematics")
    telem_cnt = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM telematics_stream")
    stream_cnt = cursor.fetchone()[0]

    cursor.execute("SELECT vehicle_id, make_model FROM vehicle_registry")
    v_id, v_model = cursor.fetchone()

    cursor.execute("SELECT name, license_no FROM driver_profiles")
    d_name, d_lic = cursor.fetchone()

    cursor.execute("SELECT trip_id, origin, destination, total_route_km FROM trips")
    trip_id, t_orig, t_dest, t_km = cursor.fetchone()

    conn.close()

    print(f"[+] Successfully initialized enterprise database at {DB_PATH}:")
    print(f"    - telematics records: {telem_cnt}")
    print(f"    - stream records: {stream_cnt}")
    print(f"    - vehicle: {v_id} ({v_model})")
    print(f"    - driver: {d_name} ({d_lic})")
    print(f"    - trip: {trip_id} ({t_orig} -> {t_dest}, {t_km} km)")

if __name__ == "__main__":
    setup_database()
