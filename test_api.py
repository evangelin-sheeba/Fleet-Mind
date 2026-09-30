"""
Automated Integration and Verification Test Suite for FleetMind FastAPI & JSON Database.
Uses standard Python unittest.
"""

import sys
import os
import unittest
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database.json_repository import get_repository


class TestFleetMindAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ONLINE")
        self.assertIn("endpoints", data)

    def test_02_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "FleetMind API")

    def test_03_get_drivers_list(self):
        response = self.client.get("/drivers")
        self.assertEqual(response.status_code, 200)
        drivers = response.json()
        self.assertIsInstance(drivers, list)
        self.assertGreater(len(drivers), 0)
        first = drivers[0]
        self.assertIn("driver_id", first)
        self.assertIn("driver_status", first)
        self.assertIn("risk_score", first)

    def test_04_get_single_driver_found(self):
        response = self.client.get("/drivers/D001")
        self.assertEqual(response.status_code, 200)
        driver = response.json()
        self.assertEqual(driver["driver_id"], "D001")
        self.assertIn("driver_name", driver)
        self.assertIn("risk_score", driver)
        self.assertIn("ear", driver)
        self.assertIn("mar", driver)

    def test_05_get_single_driver_not_found(self):
        response = self.client.get("/drivers/INVALID_DRIVER_XYZ")
        self.assertEqual(response.status_code, 404)
        error = response.json()
        self.assertIn("not found", error["detail"].lower())

    def test_06_get_driver_risk(self):
        response = self.client.get("/drivers/D001/risk")
        self.assertEqual(response.status_code, 200)
        risk_info = response.json()
        self.assertEqual(risk_info["driver_id"], "D001")
        self.assertIn("risk_score", risk_info)
        self.assertIn("risk_level", risk_info)
        self.assertIn("breakdown", risk_info)

    def test_07_get_vehicles_list(self):
        response = self.client.get("/vehicles")
        self.assertEqual(response.status_code, 200)
        vehicles = response.json()
        self.assertIsInstance(vehicles, list)
        self.assertGreater(len(vehicles), 0)
        first = vehicles[0]
        self.assertIn("vehicle_id", first)
        self.assertIn("vehicle_status", first)

    def test_08_get_single_vehicle(self):
        response = self.client.get("/vehicles/TRK-001")
        self.assertEqual(response.status_code, 200)
        veh = response.json()
        self.assertEqual(veh["vehicle_id"], "TRK-001")
        self.assertIn("cargo_type", veh)

    def test_09_post_risk_telemetry_update(self):
        payload = {
            "driver_id": "D001",
            "driver_name": "Arun Kumar",
            "vehicle_id": "TRK-001",
            "speed_kmh": 72.5,
            "acceleration_kmh_s": -0.8,
            "latitude": 11.2335,
            "longitude": 78.8817,
            "heading_deg": 38.0,
            "ear": 0.28,
            "mar": 0.18,
            "eye_closed_seconds": 0.0,
            "is_yawning": False,
            "microsleep_detected": False,
            "risk_score": 12.5,
            "risk_level": "NOMINAL",
            "driver_action": "Cruising on NH 45"
        }
        response = self.client.post("/risk", json=payload)
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data["status"], "success")
        self.assertEqual(res_data["data"]["driver_id"], "D001")
        self.assertEqual(res_data["data"]["risk_score"], 12.5
        )
        self.assertEqual(res_data["data"]["speed_kmh"], 72.5)

    def test_10_post_event_and_get_alerts(self):
        event_payload = {
            "driver_id": "D001",
            "vehicle_id": "TRK-001",
            "event_type": "microsleep",
            "severity": "CRITICAL",
            "risk_score": 85.0,
            "speed_kmh": 68.0,
            "details": "Operator eyes closed for 2.4 seconds while traveling at 68 km/h"
        }
        post_res = self.client.post("/events", json=event_payload)
        self.assertEqual(post_res.status_code, 201)
        evt = post_res.json()
        self.assertEqual(evt["event_type"], "microsleep")
        self.assertEqual(evt["severity"], "CRITICAL")
        self.assertEqual(evt["driver_id"], "D001")

        # Verify event appears in /alerts
        alerts_res = self.client.get("/alerts?limit=10")
        self.assertEqual(alerts_res.status_code, 200)
        alerts = alerts_res.json()
        self.assertGreater(len(alerts), 0)
        self.assertTrue(any(a["event_type"] == "microsleep" and a["driver_id"] == "D001" for a in alerts))

    def test_11_get_fleet_status(self):
        response = self.client.get("/fleet/status")
        self.assertEqual(response.status_code, 200)
        status_data = response.json()
        self.assertGreater(status_data["total_vehicles"], 0)
        self.assertGreater(status_data["total_drivers"], 0)
        self.assertEqual(status_data["system_status"], "ONLINE")
        self.assertTrue(status_data["database_connected"])

    def test_12_manager_command_dispatch_and_fetch(self):
        cmd_payload = {
            "vehicle_id": "TRK-001",
            "command_type": "MANDATORY_SAFE_STOP",
            "message": "Immediate stop required at next corridor rest area"
        }
        post_cmd = self.client.post("/commands", json=cmd_payload)
        self.assertEqual(post_cmd.status_code, 201)
        cmd_data = post_cmd.json()
        self.assertEqual(cmd_data["command_type"], "MANDATORY_SAFE_STOP")
        self.assertEqual(cmd_data["status"], "DISPATCHED")

        # Verify command in list
        get_cmd = self.client.get("/commands?limit=5")
        self.assertEqual(get_cmd.status_code, 200)
        cmds = get_cmd.json()
        self.assertGreater(len(cmds), 0)
        self.assertTrue(any(c["command_type"] == "MANDATORY_SAFE_STOP" for c in cmds))


if __name__ == "__main__":
    unittest.main(verbosity=2)
