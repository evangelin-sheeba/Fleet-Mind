"""
Automated Verification Suite for FLEETGUARD SENTINEL
Tests all modules:
- FaceAnalysisModule (EAR, MAR, Microsleeps)
- TelematicsModule (Speed, Acceleration, Hard Braking, Overspeed)
- DynamicRiskEngine (Risk Score Fusion, Intervention Loop, Safe Stop, Escalation)
- FleetSyncManager (SQLite persistence, JSON export)
- SentinelSafetyCore (Safety Directive Engine)
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

from modules.vision import FaceAnalysisModule
from modules.telematics import TelematicsModule
from modules.risk_engine import DynamicRiskEngine, RiskLevel, InterventionStatus
from modules.fleet_sync import FleetSyncManager
from modules.safety_core import SentinelSafetyCore


def test_vision_module():
    print("[-] Testing FaceAnalysisModule...")
    vision = FaceAnalysisModule(ear_threshold=0.22, microsleep_duration_sec=2.0)

    nominal_res = vision.generate_synthetic_frame(driver_mode="nominal")
    assert nominal_res["ear"] >= 0.25, f"Expected nominal EAR >= 0.25, got {nominal_res['ear']}"
    assert not nominal_res["microsleep_detected"], "Should not detect microsleep in nominal mode"
    print("    [PASS] Nominal frame check passed.")

    for _ in range(5):
        sim_res = vision.generate_synthetic_frame(driver_mode="microsleep")
        time.sleep(0.5)

    assert sim_res["ear"] < 0.20, f"Expected microsleep EAR < 0.20, got {sim_res['ear']}"
    assert sim_res["microsleep_detected"], "Expected microsleep detected after > 2.0s"
    print("    [PASS] Microsleep detection (>2.0s closed) passed.")

    yawn_vision = FaceAnalysisModule(yawn_min_duration_sec=0.6)
    for _ in range(3):
        yawn_res = yawn_vision.generate_synthetic_frame(driver_mode="yawn")
        time.sleep(0.4)
    assert yawn_res["mar"] >= 0.60, f"Expected MAR >= 0.60, got {yawn_res['mar']}"
    assert yawn_res["total_yawns"] >= 1, "Expected at least 1 yawn recorded"
    print("    [PASS] Yawn detection passed.")


def test_telematics_module():
    print("[-] Testing TelematicsModule...")
    telem = TelematicsModule(initial_speed=70.0)

    telem.trigger_preset_scenario("overspeed")
    for _ in range(10):
        t_data = telem.step(dt=0.3)
    assert t_data["speed_kmh"] > 80.0, f"Expected speed > 80 km/h, got {t_data['speed_kmh']}"
    assert t_data["is_overspeeding"], "Expected overspeeding flag to be True"
    print(f"    [PASS] Overspeeding detection passed (Speed: {t_data['speed_kmh']} km/h).")

    telem.set_target_speed(30.0)
    hard_brake_triggered = False
    for _ in range(5):
        t_data = telem.step(dt=0.2)
        if t_data["is_hard_braking"] or t_data["acceleration_kmh_s"] <= -15.0:
            hard_brake_triggered = True
            break
    assert hard_brake_triggered, "Expected hard braking flag or decel <= -15 km/h/s"
    print(f"    [PASS] Hard braking detection passed (Decel: {t_data['acceleration_kmh_s']} km/h/s).")

    telem.trigger_preset_scenario("safe_stop")
    for _ in range(20):
        t_data = telem.step(dt=0.3)
    assert t_data["speed_kmh"] == 0.0, f"Expected speed == 0.0, got {t_data['speed_kmh']}"
    print("    [PASS] Safe stop deceleration to 0.0 km/h passed.")


def test_risk_engine_and_intervention():
    print("[-] Testing DynamicRiskEngine & Active Intervention Loop...")
    risk_eng = DynamicRiskEngine()

    v_norm = {"ear": 0.32, "eye_closed_duration": 0.0, "microsleep_detected": False, "is_yawning": False, "recent_yawns_count": 0}
    t_norm = {"speed_kmh": 65.0, "acceleration_kmh_s": 0.5, "is_overspeeding": False, "is_hard_braking": False}
    r_norm = risk_eng.compute_risk(v_norm, t_norm)

    assert r_norm["risk_level"] == RiskLevel.NOMINAL, f"Expected NOMINAL, got {r_norm['risk_level']}"
    assert r_norm["risk_score"] < 40.0, f"Expected risk < 40, got {r_norm['risk_score']}"
    print(f"    [PASS] Nominal risk calculation passed (Score: {r_norm['risk_score']}%).")

    v_crit = {"ear": 0.12, "eye_closed_duration": 2.5, "microsleep_detected": True, "is_yawning": True, "recent_yawns_count": 2}
    t_crit = {"speed_kmh": 85.0, "acceleration_kmh_s": -2.0, "is_overspeeding": True, "is_hard_braking": False}
    r_crit = risk_eng.compute_risk(v_crit, t_crit)

    assert r_crit["risk_score"] >= 70.0, f"Expected score >= 70, got {r_crit['risk_score']}"
    assert r_crit["risk_level"] == RiskLevel.CRITICAL, f"Expected CRITICAL, got {r_crit['risk_level']}"
    assert r_crit["is_critical"], "Expected is_critical = True"
    print(f"    [PASS] Critical risk threshold trigger passed (Score: {r_crit['risk_score']}%).")

    t_zero = {"speed_kmh": 0.0, "acceleration_kmh_s": 0.0, "is_overspeeding": False, "is_hard_braking": False}
    r_stop = risk_eng.compute_risk(v_crit, t_zero)
    assert r_stop["intervention_status"] == InterventionStatus.SAFE_STOP_VERIFIED, f"Expected SAFE_STOP_VERIFIED, got {r_stop['intervention_status']}"
    print("    [PASS] Safe Stop verification at exactly 0.0 km/h passed.")

    risk_eng_esc = DynamicRiskEngine()
    risk_eng_esc.ESCALATION_TIMEOUT_SEC = 0.5
    risk_eng_esc.compute_risk(v_crit, t_crit)
    time.sleep(0.6)
    r_esc = risk_eng_esc.compute_risk(v_crit, t_crit)

    assert r_esc["is_escalated"], "Expected escalation flag to be True when speed > 0 post-timeout"
    assert r_esc["intervention_status"] == InterventionStatus.ESCALATED
    print("    [PASS] Auto-escalation flag on ignored alert passed.")


def test_fleet_sync():
    print("[-] Testing FleetSyncManager (SQLite & JSON)...")
    sync_mgr = FleetSyncManager(vehicle_id="TEST-UNIT-01", driver_name="Test Operator")

    t_data = {"speed_kmh": 74.5, "acceleration_kmh_s": -1.2, "is_overspeeding": False, "is_hard_braking": False, "total_hard_brakes": 1}
    v_data = {"ear": 0.28, "mar": 0.31, "eye_closed_duration": 0.0, "microsleep_detected": False, "is_yawning": False, "total_yawns": 2}
    r_data = {"risk_score": 32.5, "risk_level": "NOMINAL", "intervention_status": "MONITORING", "is_escalated": False, "driver_action": "Nominal drive", "seconds_in_alert": 0.0}

    payload = sync_mgr.sync_telematics_frame(t_data, v_data, r_data)

    assert os.path.exists(sync_mgr.DB_PATH), "Database file must exist"
    assert os.path.exists(sync_mgr.JSON_PATH), "JSON export file must exist"
    assert payload["telematics"]["speed_kmh"] == 74.5

    logs = sync_mgr.fetch_recent_telematics(limit=5)
    assert len(logs) > 0, "Logs list should contain recent records"
    print(f"    [PASS] SQLite & JSON sync verified successfully ({len(logs)} records in stream).")


def test_safety_core():
    print("[-] Testing SentinelSafetyCore (Onboard Safety Engine)...")
    core = SentinelSafetyCore()
    res = core.get_safety_directive(risk_score=78.5, issue="Long Eye Closure", speed=84.0, ear=0.15, mar=0.25)
    assert "text" in res, "Result must contain 'text' directive"
    assert "source" in res, "Result must contain 'source'"
    assert len(res["text"]) > 10, "Directive must be substantive"
    print("    [PASS] SentinelSafetyCore directive verified successfully.")


def test_database_integration():
    print("[-] Testing SQLite fleet_mind.db Enterprise Integration...")
    import sqlite3
    db_path = "fleet_mind.db"
    assert os.path.exists(db_path), "fleet_mind.db must exist"

    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        for tbl in ["vehicle_registry", "driver_profiles", "trips", "telematics", "telematics_stream"]:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            cnt = cur.fetchone()[0]
            assert cnt > 0, f"Table {tbl} must not be empty (got {cnt})"
            print(f"    [PASS] Table '{tbl}' verified ({cnt} records).")

    # Test TelematicsModule DB playback
    telem = TelematicsModule()
    telem.enable_db_playback(True, start_idx=10)
    db_step = telem.step(dt=0.2)
    assert "speed_kmh" in db_step, "DB step result must contain speed_kmh"
    assert db_step["db_playback_active"], "DB playback active flag must be True"
    print(f"    [PASS] TelematicsModule DB playback verified (Speed: {db_step['speed_kmh']} km/h, Lat: {db_step['latitude']}).")

    # Test FleetSyncManager entity queries
    sync_mgr = FleetSyncManager()
    veh = sync_mgr.fetch_vehicle_from_db()
    drv = sync_mgr.fetch_driver_from_db()
    trip = sync_mgr.fetch_trip_from_db()
    stats = sync_mgr.fetch_db_stats()

    assert veh.get("vehicle_id") == "TN 58 AA 4920", f"Expected TN 58 AA 4920, got {veh.get('vehicle_id')}"
    assert "Arun Kumar" in drv.get("name", ""), f"Expected Arun Kumar, got {drv.get('name')}"
    assert "TRIP-TN-MDU-MAA" in trip.get("trip_id", ""), f"Expected trip ID, got {trip.get('trip_id')}"
    assert stats.get("telematics_count", 0) >= 1200, f"Expected >= 1200 records, got {stats.get('telematics_count')}"
    print(f"    [PASS] FleetSyncManager entity queries verified ({stats['telematics_count']} records, {stats['size_kb']} KB).")


if __name__ == "__main__":
    print("==================================================")
    print("FLEETGUARD SENTINEL // COMMENCING VERIFICATION")
    print("==================================================")
    test_vision_module()
    test_telematics_module()
    test_risk_engine_and_intervention()
    test_fleet_sync()
    test_safety_core()
    test_database_integration()
    print("==================================================")
    print("ALL MODULE & DATABASE TESTS PASSED SUCCESSFULLY!")
    print("==================================================")
