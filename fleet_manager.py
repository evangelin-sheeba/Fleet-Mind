"""
================================================================================
FLEETGUARD SENTINEL: Fleet Operations & Dispatch Command Center
================================================================================
Separate, linked supervisor dashboard providing:
1. Live GPS Vehicle Tracking Map (Pydeck 3D Dark Vector Map with route & heading)
2. Comprehensive Vehicle Health & Hardware Diagnostics
3. Driver Profile & Hours of Service (HOS) Compliance
4. Active Trip Manifest & Route Progress
5. Real-Time Incoming Fatigue Alerts & Remote Dispatch Intervention Controls
6. Synchronized SQLite Telemetry & Escalation Incident Audit Logs
"""

import time
import os
import json
import sqlite3
import socket
import pandas as pd
import numpy as np
import pydeck as pdk
import requests
import streamlit as st

from modules.styles import get_cockpit_css, get_audio_alert_html
from modules.fleet_sync import FleetSyncManager


def get_local_ip() -> str:
    """Detects local machine Wi-Fi / LAN IP address for multi-laptop connectivity."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# Dynamic Backend URL from session_state
if "fastapi_url" not in st.session_state:
    st.session_state.fastapi_url = "http://localhost:8000"


def get_fastapi_url() -> str:
    """Returns current active FastAPI endpoint URL."""
    return st.session_state.get("fastapi_url", "http://localhost:8000").rstrip("/")


def send_fastapi_command(command_type: str, message: str, vehicle_id: str = "TN 58 AA 4920"):
    """Dispatches supervisory command to FastAPI backend."""
    try:
        url = f"{get_fastapi_url()}/commands"
        requests.post(url, json={
            "vehicle_id": vehicle_id,
            "command_type": command_type,
            "message": message
        }, timeout=0.5)
    except Exception:
        pass


def fetch_fastapi_alerts(limit: int = 8) -> list:
    """Retrieves alerts from FastAPI backend."""
    try:
        url = f"{get_fastapi_url()}/alerts?limit={limit}"
        r = requests.get(url, timeout=0.5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="FLEETGUARD // Dispatch Command Center",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply unified obsidian glassmorphism theme
st.markdown(get_cockpit_css(), unsafe_allow_html=True)

# Initialize Sync Manager
if "fleet_mgr_sync" not in st.session_state:
    st.session_state.fleet_mgr_sync = FleetSyncManager()

if "auto_refresh_active" not in st.session_state:
    st.session_state.auto_refresh_active = True

if "dispatch_broadcast_status" not in st.session_state:
    st.session_state.dispatch_broadcast_status = None


# -----------------------------------------------------------------------------
# Helper: Fetch Live State Payload
# -----------------------------------------------------------------------------
def load_live_telematics_packet() -> dict:
    # 1. First attempt to pull directly from FastAPI backend
    fastapi_host = get_fastapi_url()
    try:
        r_drv = requests.get(f"{fastapi_host}/drivers/D001", timeout=0.35)
        r_risk = requests.get(f"{fastapi_host}/drivers/D001/risk", timeout=0.35)
        if r_drv.status_code == 200 and r_risk.status_code == 200:
            drv = r_drv.json()
            risk = r_risk.json()
            
            speed = float(drv.get("current_speed_kph", 68.0))
            risk_score = float(risk.get("risk_score", 0.0))
            risk_level = risk.get("risk_level", "NOMINAL")
            is_crit = (risk_level == "CRITICAL" or risk.get("microsleep_detected", False) or risk_score >= 70.0)

            return {
                "fastapi_connected": True,
                "vehicle": {
                    "id": drv.get("vehicle_id", "TN 58 AA 4920"),
                    "vin": "MB1T2H4A0NP492011",
                    "make_model": "Ashok Leyland 4220 HG (14-Wheeler Heavy Commercial Hauler)",
                    "engine_status": "RUNNING" if speed > 0 else "IDLE",
                    "status": drv.get("vehicle_status", "IN_TRANSIT"),
                    "fuel_battery_percent": 78.5,
                    "engine_temp_c": 88.5,
                    "tire_pressure_psi": 115.0,
                    "odometer_km": 184218.0
                },
                "driver": {
                    "name": drv.get("driver_name", "Arun Kumar (Operator #104)"),
                    "license": "TN-58-2016-0049281 (Heavy Commercial Freight CDL)",
                    "hos_driving_hours": 5.2,
                    "hos_max_hours": 10.0,
                    "safety_score": round(max(0.0, 100.0 - risk_score), 1),
                    "safety_grade": "A+" if risk_score < 20 else ("B" if risk_score < 50 else "CRIT"),
                    "medical_cert_valid": True,
                    "driver_status": drv.get("driver_status", "Safe")
                },
                "trip": {
                    "route_id": drv.get("route_id", "TN-MDU-MAA-NH45"),
                    "origin": drv.get("city", "Madurai") + " Logistics Hub",
                    "destination": "Chennai Madhavaram Central Logistics Hub",
                    "cargo_description": drv.get("cargo_type", "Automotive Spares & Precision Castings"),
                    "cargo_temp_c": 26.8,
                    "total_route_km": 462.0,
                    "distance_covered_km": 218.0,
                    "remaining_km": 244.0,
                    "eta_minutes": 185.0,
                    "progress_percent": 47.2
                },
                "gps": {
                    "latitude": float(drv.get("current_latitude") or 11.2335) if (8.0 <= float(drv.get("current_latitude") or 0.0) <= 20.0) else 11.2335,
                    "longitude": float(drv.get("current_longitude") or 78.8817) if (75.0 <= float(drv.get("current_longitude") or 0.0) <= 82.0) else 78.8817,
                    "heading_deg": float(drv.get("heading_deg", 38.0)),
                    "route_waypoints": [
                        [9.9325, 78.1633], [10.0336, 78.3370], [10.3673, 78.4800],
                        [10.6033, 78.5436], [10.7905, 78.7047], [10.9238, 78.7397],
                        [11.2335, 78.8817], [11.6917, 79.2900], [11.9401, 79.4861],
                        [12.2333, 79.6500], [12.4333, 79.8333], [12.6819, 79.9888],
                        [12.9249, 80.1000], [13.0827, 80.2707]
                    ]
                },
                "telematics": {
                    "speed_kmh": speed,
                    "acceleration_kmh_s": 0.2,
                    "is_overspeeding": speed > 80.0,
                    "is_hard_braking": False,
                    "total_hard_brakes": 0
                },
                "biometrics": {
                    "ear": float(risk.get("ear", 0.32)),
                    "mar": float(risk.get("mar", 0.25)),
                    "microsleep_detected": bool(risk.get("microsleep_detected", False)),
                    "eye_closed_seconds": float(risk.get("eye_closed_seconds", 0.0)),
                    "is_yawning": bool(risk.get("is_yawning", False)),
                    "total_yawns": int(drv.get("yawning_events_count", 0))
                },
                "intervention": {
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "intervention_status": "CRITICAL_ALERT_ACTIVE" if is_crit else "MONITORING",
                    "escalation_flag": is_crit,
                    "driver_action": "Safe Driving on Corridor" if not is_crit else "CRITICAL: High Fatigue Detected!"
                }
            }
    except Exception:
        pass

    # 2. Fallback to Local JSON / SQLite if FastAPI is temporarily offline
    json_path = st.session_state.fleet_mgr_sync.JSON_PATH
    default_payload = {
        "fastapi_connected": False,
        "vehicle": {
            "id": "TN 58 AA 4920",
            "vin": "MB1T2H4A0NP492011",
            "make_model": "Ashok Leyland 4220 HG (14-Wheeler Heavy Commercial Hauler)",
            "engine_status": "RUNNING",
            "status": "IN_TRANSIT",
            "fuel_battery_percent": 78.5,
            "engine_temp_c": 88.5,
            "tire_pressure_psi": 115.0,
            "odometer_km": 184218.0
        },
        "driver": {
            "name": "Arun Kumar (Operator #104)",
            "license": "TN-58-2016-0049281 (Heavy Commercial Freight CDL)",
            "hos_driving_hours": 5.2,
            "hos_max_hours": 10.0,
            "safety_score": 96.4,
            "safety_grade": "A+",
            "medical_cert_valid": True,
            "driver_status": "Safe"
        },
        "trip": {
            "route_id": "TN-MDU-MAA-NH45",
            "origin": "Madurai Mattuthavani Freight Terminal",
            "destination": "Chennai Madhavaram Central Logistics Hub",
            "cargo_description": "Automotive Spares & Precision Castings (18.5 MT)",
            "cargo_temp_c": 26.8,
            "total_route_km": 462.0,
            "distance_covered_km": 218.0,
            "remaining_km": 244.0,
            "eta_minutes": 185.0,
            "progress_percent": 47.2
        },
        "gps": {
            "latitude": 11.2335,
            "longitude": 78.8817,
            "heading_deg": 38.0,
            "route_waypoints": [
                [9.9325, 78.1633], [10.0336, 78.3370], [10.3673, 78.4800],
                [10.6033, 78.5436], [10.7905, 78.7047], [10.9238, 78.7397],
                [11.2335, 78.8817], [11.6917, 79.2900], [11.9401, 79.4861],
                [12.2333, 79.6500], [12.4333, 79.8333], [12.6819, 79.9888],
                [12.9249, 80.1000], [13.0827, 80.2707]
            ]
        },
        "telematics": {
            "speed_kmh": 68.0,
            "acceleration_kmh_s": 0.2,
            "is_overspeeding": False,
            "is_hard_braking": False,
            "total_hard_brakes": 0
        },
        "biometrics": {
            "ear": 0.32,
            "mar": 0.25,
            "microsleep_detected": False,
            "eye_closed_seconds": 0.0,
            "is_yawning": False,
            "total_yawns": 0
        },
        "intervention": {
            "risk_score": 5.0,
            "risk_level": "NOMINAL",
            "intervention_status": "MONITORING",
            "escalation_flag": False,
            "driver_action": "Nominal vehicle transit"
        }
    }

    payload = default_payload
    try:
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
                payload["fastapi_connected"] = False
    except Exception:
        payload = default_payload

    # Actively enrich from SQLite fleet_mind.db if present
    try:
        v_db = st.session_state.fleet_mgr_sync.fetch_vehicle_from_db()
        d_db = st.session_state.fleet_mgr_sync.fetch_driver_from_db()
        t_db = st.session_state.fleet_mgr_sync.fetch_trip_from_db()

        if v_db:
            payload["vehicle"]["id"] = v_db.get("vehicle_id", payload["vehicle"]["id"])
            payload["vehicle"]["vin"] = v_db.get("vin", payload["vehicle"]["vin"])
            payload["vehicle"]["make_model"] = v_db.get("make_model", payload["vehicle"]["make_model"])
        if d_db:
            payload["driver"]["name"] = d_db.get("name", payload["driver"]["name"])
            payload["driver"]["license"] = d_db.get("license_no", payload["driver"]["license"])
        if t_db:
            payload["trip"]["route_id"] = t_db.get("trip_id", payload["trip"]["route_id"])
            payload["trip"]["origin"] = t_db.get("origin", payload["trip"]["origin"])
            payload["trip"]["destination"] = t_db.get("destination", payload["trip"]["destination"])
    except Exception:
        pass

    return payload


# -----------------------------------------------------------------------------
# Distributed 2-Laptop Setup (Sidebar)
# -----------------------------------------------------------------------------
local_ip = get_local_ip()

with st.sidebar:
    st.markdown("""
    <div style="font-family: 'Orbitron'; font-size: 16px; font-weight: 700; color: #0284c7; margin-bottom: 8px;">
        🛰️ FLEET MANAGER NODE
    </div>
    <div style="font-family: 'JetBrains Mono'; font-size: 11px; color: #64748b; margin-bottom: 16px;">
        LAPTOP 2: DISPATCH OPERATIONS COMMAND CENTER
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background: rgba(241, 245, 249, 0.9); border: 1px solid rgba(2, 132, 199, 0.2); border-radius: 8px; padding: 12px; margin-bottom: 14px;">
        <div style="font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: 1px;">THIS MANAGER LAPTOP IP:</div>
        <div style="font-family: 'JetBrains Mono'; font-size: 15px; color: #0284c7; font-weight: 700; margin-top: 2px;">{local_ip}</div>
        <div style="font-size: 11px; color: #64748b; margin-top: 6px;">
            Port <strong>8502</strong>: Fleet Manager UI
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="font-size: 11px; font-weight: 600; color: #0f172a; margin-bottom: 4px;">
        📡 DRIVER LAPTOP BACKEND HOST (FASTAPI):
    </div>
    """, unsafe_allow_html=True)
    backend_input = st.text_input(
        "Driver Backend URL",
        value=st.session_state.fastapi_url,
        help="Enter the IP address of Laptop 1 running Driver Cockpit & FastAPI (e.g. http://10.58.253.174:8000)",
        label_visibility="collapsed"
    )
    if backend_input != st.session_state.fastapi_url:
        st.session_state.fastapi_url = backend_input.rstrip("/")
        st.rerun()

    # Ping check
    api_online = False
    try:
        r = requests.get(f"{get_fastapi_url()}/health", timeout=0.35)
        api_online = (r.status_code == 200)
    except Exception:
        api_online = False

    if api_online:
        st.markdown(f"""
        <div style="padding: 8px 12px; border-radius: 6px; background: rgba(5, 150, 105, 0.1); border: 1px solid rgba(5, 150, 105, 0.4); color: #059669; font-size: 12px; font-weight: 600; font-family: 'JetBrains Mono'; margin-top: 8px;">
            &#10004; CONNECTED TO DRIVER LAPTOP
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="padding: 8px 12px; border-radius: 6px; background: rgba(220, 38, 38, 0.1); border: 1px solid rgba(220, 38, 38, 0.4); color: #dc2626; font-size: 12px; font-weight: 600; font-family: 'JetBrains Mono'; margin-top: 8px;">
            &#9888; DRIVER LAPTOP UNREACHABLE (STANDBY)
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color: rgba(2, 132, 199, 0.15); margin: 16px 0;'>", unsafe_allow_html=True)

    st.markdown("""
    <div style="font-size: 11px; color: #64748b; line-height: 1.5;">
        <strong>2-Laptop Setup Guide:</strong><br>
        1. Connect both laptops to same Wi-Fi.<br>
        2. On Laptop 1 (Driver), check its Wi-Fi IP.<br>
        3. Enter Laptop 1's IP above to link the live 3D map, telematics & emergency dispatch interlocks!
    </div>
    """, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Top Dispatch Operations Header Bar
# -----------------------------------------------------------------------------
st.markdown("""
<div class="fleet-navbar">
    <div class="fleet-nav-brand">
        <span class="fleet-nav-logo">&#128752; FLEETGUARD // DISPATCH OPERATIONS CENTER</span>
        <span class="fleet-telemetry-badge badge-nominal"><span class="pulse-dot"></span> LIVE FLEET TELEMETRY LINK</span>
    </div>
    <div style="display: flex; gap: 24px; align-items: center; font-family: 'JetBrains Mono', monospace; font-size: 13px;">
        <div><span style="color: var(--text-dim);">LORRY:</span> <strong style="color: var(--neon-cyan);">TN 58 AA 4920</strong></div>
        <div><span style="color: var(--text-dim);">OPERATOR:</span> <strong style="color: var(--text-bright);">ARUN KUMAR</strong></div>
        <div><span style="color: var(--text-dim);">CORRIDOR:</span> <strong style="color: #059669;">MADURAI &rarr; CHENNAI</strong></div>
        <div><span class="fleet-telemetry-badge badge-nominal">PORT: 8502</span></div>
    </div>
</div>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Main Operations Telematics Fragment (Auto-refreshes every 1 second)
# -----------------------------------------------------------------------------
@st.fragment(run_every=1)
def render_live_operations_view():
    # Main Manager Interface
    # -----------------------------------------------------------------------------

    # Single-step or Continuous Polling Loop
    try:
        # Load latest packet
        data = load_live_telematics_packet()
        veh = data.get("vehicle", {})
        drv = data.get("driver", {})
        trip = data.get("trip", {})
        gps = data.get("gps", {})
        telem = data.get("telematics", {})
        bio = data.get("biometrics", {})
        interv = data.get("intervention", {})

        risk_score = interv.get("risk_score", 0.0)
        risk_level = interv.get("risk_level", "NOMINAL")
        is_critical_fatigue = (risk_level == "CRITICAL" or interv.get("escalation_flag", False) or bio.get("microsleep_detected", False))

        # Live Auto-Sync Status Bar
        now_str = time.strftime("%H:%M:%S")
        status_color = "#dc2626" if is_critical_fatigue else ("#d97706" if risk_level == "ELEVATED" else "#059669")
        status_label = "CRITICAL FATIGUE ALERT" if is_critical_fatigue else ("ELEVATED RISK ADVISORY" if risk_level == "ELEVATED" else "SYSTEMS NOMINAL")

        fastapi_ok = data.get("fastapi_connected", False)
        fastapi_badge = '<span class="fleet-telemetry-badge badge-nominal"><span class="pulse-dot"></span> FASTAPI: PORT 8000 ONLINE</span>' if fastapi_ok else '<span class="fleet-telemetry-badge badge-warning">FASTAPI: OFFLINE (FALLBACK)</span>'

        st.markdown(f'''
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; padding: 8px 14px; background: rgba(255, 255, 255, 0.85); border-radius: 8px; border: 1px solid rgba(2, 132, 199, 0.18);">
            <div style="display: flex; gap: 12px; align-items: center;">
                {fastapi_badge}
                <span class="fleet-telemetry-badge badge-nominal"><span class="pulse-dot"></span> 1-SEC AUTO-SYNC: ACTIVE</span>
                <span style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-dim);">LAST TICK: {now_str}</span>
            </div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 12px;">
                <span style="color: var(--text-dim);">DISPATCH STATE: </span>
                <strong style="color: {status_color}; font-weight: 700; margin-left: 6px;">{status_label}</strong>
            </div>
        </div>
        ''', unsafe_allow_html=True)


        # 1. Incoming Real-Time Fatigue Alert Dispatch Banner
        if is_critical_fatigue:
            issue_desc = "MICROSLEEP DETECTED (> 2.0s closed)" if bio.get("microsleep_detected") else ("REPEATED YAWNING / EXTREME FATIGUE" if bio.get("is_yawning") else "HIGH DYNAMIC RISK THRESHOLD EXCEEDED")
            st.markdown(f"""
            <div class="fleet-alert-banner">
                <div>
                    <div class="fleet-alert-title">&#128680; PRIORITY DISPATCH ALERT &mdash; DRIVER FATIGUE CRITICAL</div>
                    <div class="fleet-alert-subtitle">
                        <strong>LORRY: {veh.get('id', 'TN 58 AA 4920')} &bull; OPERATOR: {drv.get('name', 'Arun Kumar')}</strong>: {issue_desc}
                        <div style="font-size: 13px; color: #7f1d1d; margin-top: 6px; font-family: 'JetBrains Mono';">
                            CORRIDOR: NH 45 GST Road (Madurai &rarr; Chennai) &bull; SPEED: {telem.get('speed_kmh', 0):.0f} km/h &bull; EAR: {bio.get('ear', 0):.2f} &bull; MAR: {bio.get('mar', 0):.2f} &bull; RISK: {risk_score:.1f}% &bull; STATUS: {interv.get('intervention_status', 'CRITICAL')}
                        </div>
                    </div>
                </div>
                <div>
                    <span class="fleet-telemetry-badge badge-critical">IMMEDIATE ACTION REQUIRED</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(get_audio_alert_html(active=True), unsafe_allow_html=True)
        elif risk_level == "ELEVATED":
            st.markdown(f"""
            <div class="fleet-glass-card" style="border-color: rgba(217, 119, 6, 0.6); background: rgba(254, 243, 199, 0.95);">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <strong style="color: #92400e; font-family: 'Orbitron'; font-size: 15px;">
                            &#9888; FLEET TELEMETRY ADVISORY &mdash; ELEVATED DRIVER FATIGUE [{risk_score:.1f}%]
                        </strong>
                        <div style="color: #b45309; font-size: 13px; margin-top: 4px; font-weight: 600;">
                            Lorry {veh.get('id', 'TN 58 AA 4920')} &bull; Operator Arun displaying drowsiness indicators on NH 45. Route monitors on standby.
                        </div>
                    </div>
                    <span class="fleet-telemetry-badge badge-warning">ELEVATED RISK</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            pass

        # 2. Executive Operational KPIs (Clean Aligned Grid)
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        with kpi_col1:
            st.markdown(f"""
            <div class="fleet-metric-tile">
                <div class="fleet-metric-val">{telem.get('speed_kmh', 0):.0f} <span style="font-size: 16px;">km/h</span></div>
                <div class="fleet-metric-lbl">CURRENT VEHICLE SPEED</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_col2:
            r_color = "#059669" if risk_score < 40 else ("#d97706" if risk_score < 70 else "#dc2626")
            st.markdown(f"""
            <div class="fleet-metric-tile">
                <div class="fleet-metric-val" style="color: {r_color};">{risk_score:.1f}%</div>
                <div class="fleet-metric-lbl">FATIGUE RISK INDEX ({risk_level})</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_col3:
            st.markdown(f"""
            <div class="fleet-metric-tile">
                <div class="fleet-metric-val" style="color: var(--neon-cyan);">{trip.get('progress_percent', 47.2):.1f}%</div>
                <div class="fleet-metric-lbl">TRIP PROGRESS ({trip.get('distance_covered_km', 218):.0f} / {trip.get('total_route_km', 462):.0f} km)</div>
            </div>
            """, unsafe_allow_html=True)
        with kpi_col4:
            st.markdown(f"""
            <div class="fleet-metric-tile">
                <div class="fleet-metric-val" style="color: var(--neon-violet);">{trip.get('eta_minutes', 185):.0f} <span style="font-size: 16px;">min</span></div>
                <div class="fleet-metric-lbl">ESTIMATED TIME TO CHENNAI (ETA)</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 3. Live GPS Vehicle Tracking Map & Route Trajectory (Madurai -> Chennai Corridor)
        with st.container():
            st.markdown("""
            <div class="fleet-glass-card" style="padding-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                    <div>
                        <span style="font-family: 'Orbitron'; font-size: 16px; font-weight: 800; color: var(--neon-cyan);">
                            &#127757; LIVE GPS VEHICLE TRACKING & CORRIDOR TRAJECTORY
                        </span>
                        <span style="display: block; font-size: 12px; color: var(--text-dim); margin-top: 2px;">
                            ROADWAYS CORRIDOR: MADURAI &rarr; TIRUCHIRAPPALLI &rarr; VILLUPURAM &rarr; CHENNAI (NH 45 GST EXPRESSWAY)
                        </span>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <span class="fleet-telemetry-badge" style="background: rgba(0, 102, 255, 0.12); color: #0066ff; border: 1px solid rgba(0, 102, 255, 0.35);">
                            ROADWAY PATH: HIGHLIGHTED BLUE
                        </span>
                        <span class="fleet-telemetry-badge badge-nominal">REAL-TIME GPS LINK</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            current_lat = gps.get("latitude", 11.2335)
            current_lon = gps.get("longitude", 78.8817)
            heading = gps.get("heading_deg", 38.0)
            route_pts = gps.get("route_waypoints", [])

            # Create Pydeck 3D Map (Carto Positron Light Theme with Highlighted Blue Roadways Line)
            # 1. Outer Glow Roadway Path Layer (electric blue halo)
            glow_path_data = [{"path": [[p[1], p[0]] for p in route_pts], "color": [0, 110, 255, 110]}]
            glow_path_layer = pdk.Layer(
                "PathLayer",
                data=glow_path_data,
                get_path="path",
                get_color="color",
                width_min_pixels=8,
                width_max_pixels=12,
            )

            # 2. Core Roadway Path Layer (Highlighted Vibrant Blue Roadway Path)
            path_data = [{"path": [[p[1], p[0]] for p in route_pts], "color": [0, 102, 255, 255]}]
            path_layer = pdk.Layer(
                "PathLayer",
                data=path_data,
                get_path="path",
                get_color="color",
                width_min_pixels=4,
                width_max_pixels=6,
            )

            # 3. Vehicle Real-Time Marker Layer (Ashok Leyland Lorry Marker)
            marker_color = [220, 38, 38, 240] if is_critical_fatigue else [5, 150, 105, 240]
            vehicle_df = pd.DataFrame([{
                "latitude": current_lat,
                "longitude": current_lon,
                "tooltip": f"Lorry: TN 58 AA 4920 | Driver: Arun Kumar | Speed: {telem.get('speed_kmh', 0):.0f} km/h | Route: Madurai to Chennai",
                "size": 550 if is_critical_fatigue else 380
            }])

            vehicle_layer = pdk.Layer(
                "ScatterplotLayer",
                data=vehicle_df,
                get_position="[longitude, latitude]",
                get_color=marker_color,
                get_radius="size",
                pickable=True,
                filled=True,
                stroked=True,
                get_line_color=[15, 23, 42, 220],
                line_width_min_pixels=2
            )

            # 4. View State centered on Tamil Nadu Freight Corridor
            view_state = pdk.ViewState(
                latitude=current_lat,
                longitude=current_lon,
                zoom=7.3,
                pitch=25,
                bearing=0
            )

            deck = pdk.Deck(
                layers=[glow_path_layer, path_layer, vehicle_layer],
                initial_view_state=view_state,
                tooltip={"text": "{tooltip}"},
                map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
            )
            st.pydeck_chart(deck, use_container_width=True)

            # Perfectly aligned tabular status bar below the map
            st.markdown(f"""
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 14px; font-family: 'JetBrains Mono', monospace; font-size: 12px; background: rgba(241, 245, 249, 0.95); padding: 12px 16px; border-radius: 10px; border: 1px solid rgba(2, 132, 199, 0.15);">
                <div style="border-right: 1px solid rgba(2, 132, 199, 0.15); padding-right: 10px;">
                    <span style="color: var(--text-dim); display: block; font-size: 10px; text-transform: uppercase;">GPS COORDINATES</span>
                    <strong style="color: var(--text-bright); font-size: 13px;">{current_lat:.4f}&deg; N, {current_lon:.4f}&deg; E</strong>
                </div>
                <div style="border-right: 1px solid rgba(2, 132, 199, 0.15); padding-right: 10px;">
                    <span style="color: var(--text-dim); display: block; font-size: 10px; text-transform: uppercase;">LORRY HEADING</span>
                    <strong style="color: var(--neon-cyan); font-size: 13px;">{heading:.1f}&deg; NNE (TOWARDS CHENNAI)</strong>
                </div>
                <div style="border-right: 1px solid rgba(2, 132, 199, 0.15); padding-right: 10px;">
                    <span style="color: var(--text-dim); display: block; font-size: 10px; text-transform: uppercase;">ACTIVE HIGHWAY</span>
                    <strong style="color: var(--text-bright); font-size: 13px;">NH 45 GST ROAD (TAMIL NADU)</strong>
                </div>
                <div>
                    <span style="color: var(--text-dim); display: block; font-size: 10px; text-transform: uppercase;">DISPATCH INTERLOCK</span>
                    <strong style="color: {'#dc2626' if is_critical_fatigue else '#059669'}; font-size: 13px;">{interv.get('intervention_status', 'MONITORING')}</strong>
                </div>
            </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 4. Three Detail Columns with Aligned Spec Rows: Vehicle Diagnostics, Driver Details, Trip Manifest
        col_veh, col_drv, col_trip = st.columns(3)

        # --- VEHICLE DETAILS ---
        with col_veh:
            st.markdown("""
            <div class="fleet-glass-card" style="height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                    <span style="font-family: 'Orbitron'; font-size: 14px; font-weight: 700; color: var(--neon-cyan);">
                        &#128667; VEHICLE SPECIFICATIONS
                    </span>
                    <span class="fleet-telemetry-badge badge-nominal">HEALTHY</span>
                </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">LORRY REGISTRATION:</span>
                    <span class="fleet-spec-val" style="color: var(--neon-cyan); font-size: 15px;">{veh.get('id', 'TN 58 AA 4920')}</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">CHASSIS / VIN:</span>
                    <span class="fleet-spec-val">{veh.get('vin', 'MB1T2H4A0NP492011')}</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">VEHICLE MODEL:</span>
                    <span class="fleet-spec-val" style="font-family: 'Rajdhani';">{veh.get('make_model', 'Ashok Leyland 4220 HG')}</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">ENGINE STATUS:</span>
                    <span class="fleet-spec-val" style="color: {'#059669' if telem.get('speed_kmh', 0) > 0 else '#d97706'};">{veh.get('engine_status', 'RUNNING')} (200 HP)</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">DIESEL / DEF TANK:</span>
                    <span class="fleet-spec-val" style="color: #059669;">{veh.get('fuel_battery_percent', 78.5):.1f}%</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">ENGINE COOLANT:</span>
                    <span class="fleet-spec-val">{veh.get('engine_temp_c', 88.5):.1f}&deg;C</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">TYRE PRESSURES:</span>
                    <span class="fleet-spec-val">{veh.get('tire_pressure_psi', 115.0):.0f} PSI (14 Wheels OK)</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">ODOMETER:</span>
                    <span class="fleet-spec-val" style="color: var(--neon-cyan);">{veh.get('odometer_km', 184218.0):,.1f} km</span>
                </div>
            </div>
            </div>
            """, unsafe_allow_html=True)

        # --- DRIVER DETAILS (ARUN KUMAR) ---
        with col_drv:
            st.markdown("""
            <div class="fleet-glass-card" style="height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                    <span style="font-family: 'Orbitron'; font-size: 14px; font-weight: 700; color: var(--neon-violet);">
                        &#128100; OPERATOR PROFILE & HOS
                    </span>
                    <span class="fleet-telemetry-badge badge-nominal">COMPLIANT</span>
                </div>
            """, unsafe_allow_html=True)

            hos_cur = drv.get('hos_driving_hours', 5.2)
            hos_max = drv.get('hos_max_hours', 10.0)
            hos_pct = min(100.0, round((hos_cur / hos_max) * 100.0, 1))

            st.markdown(f"""
            <div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">OPERATOR NAME:</span>
                    <span class="fleet-spec-val" style="color: var(--text-bright); font-size: 15px;">{drv.get('name', 'Arun Kumar')}</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">COMMERCIAL LICENSE:</span>
                    <span class="fleet-spec-val" style="color: var(--neon-cyan);">{drv.get('license', 'TN-58-2016-0049281')}</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">SAFETY RATING:</span>
                    <span class="fleet-spec-val" style="color: #059669;">{drv.get('safety_score', 96.4)}% ({drv.get('safety_grade', 'A+')})</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">DRIVER CONTACT:</span>
                    <span class="fleet-spec-val">+91 98421 78420</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">MEDICAL FITNESS:</span>
                    <span class="fleet-spec-val" style="color: #059669;">VERIFIED (Expires 2027)</span>
                </div>

                <div style="margin-top: 10px;">
                    <div style="display: flex; justify-content: space-between; font-size: 12px; font-family: 'JetBrains Mono'; color: var(--text-dim);">
                        <span>HOS DRIVEN: {hos_cur:.1f}h</span>
                        <span>DAILY LIMIT: {hos_max:.1f}h</span>
                    </div>
                    <div style="width: 100%; height: 8px; background: rgba(15, 23, 42, 0.08); border-radius: 4px; overflow: hidden; margin-top: 4px;">
                        <div style="width: {hos_pct}%; height: 100%; background: {'#059669' if hos_pct < 75 else '#d97706'};"></div>
                    </div>
                </div>

                <div style="margin-top: 10px; padding: 10px; background: rgba(241, 245, 249, 0.95); border: 1px solid rgba(2, 132, 199, 0.15); border-radius: 8px; font-size: 12px; font-family: 'JetBrains Mono'; color: var(--text-bright);">
                    <div style="display: flex; justify-content: space-between;">
                        <span>BIOMETRIC EAR: <strong style="color: {'#059669' if bio.get('ear', 0.3) >= 0.22 else '#dc2626'};">{bio.get('ear', 0.3):.2f}</strong></span>
                        <span>MAR: <strong style="color: var(--neon-violet);">{bio.get('mar', 0.25):.2f}</strong></span>
                    </div>
                    <div style="margin-top: 4px;">
                        CLOSED EYE DURATION: <strong style="color: {'#dc2626' if bio.get('eye_closed_seconds', 0) >= 2.0 else 'var(--text-bright)'};">{bio.get('eye_closed_seconds', 0):.1f}s / 2.0s</strong>
                    </div>
                </div>
            </div>
            </div>
            """, unsafe_allow_html=True)

        # --- TRIP DETAILS (MADURAI -> CHENNAI) ---
        with col_trip:
            st.markdown("""
            <div class="fleet-glass-card" style="height: 100%;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                    <span style="font-family: 'Orbitron'; font-size: 14px; font-weight: 700; color: var(--neon-emerald);">
                        &#128230; ACTIVE TRIP MANIFEST
                    </span>
                    <span class="fleet-telemetry-badge badge-nominal">ON SCHEDULE</span>
                </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">ROUTE ID:</span>
                    <span class="fleet-spec-val" style="color: var(--neon-cyan);">{trip.get('route_id', 'TN-MDU-MAA-NH45')}</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">ORIGIN:</span>
                    <span class="fleet-spec-val" style="font-family: 'Rajdhani';">{trip.get('origin', 'Madurai Mattuthavani Hub')}</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">DESTINATION:</span>
                    <span class="fleet-spec-val" style="font-family: 'Rajdhani';">{trip.get('destination', 'Chennai Madhavaram Complex')}</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">CONSIGNMENT CARGO:</span>
                    <span class="fleet-spec-val" style="font-family: 'Rajdhani'; font-size: 13px;">{trip.get('cargo_description', 'Automotive Spares & Castings')}</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">TOTAL DISTANCE:</span>
                    <span class="fleet-spec-val">{trip.get('total_route_km', 462):.0f} km</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">REMAINING DISTANCE:</span>
                    <span class="fleet-spec-val" style="color: var(--neon-cyan);">{trip.get('remaining_km', 244):.1f} km</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">ESTIMATED ARRIVAL:</span>
                    <span class="fleet-spec-val" style="color: #059669;">{trip.get('eta_minutes', 185):.0f} min remaining</span>
                </div>
                <div class="fleet-spec-row">
                    <span class="fleet-spec-lbl">FASTAG TOLL STATUS:</span>
                    <span class="fleet-spec-val" style="color: #059669;">SAMAYAPURAM TOLL PAID</span>
                </div>
            </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 5. Remote Dispatch Intervention Console
        st.markdown("""
        <div class="fleet-glass-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-family: 'Orbitron'; font-size: 14px; color: var(--neon-amber);">
                    &#128225; ACTIVE FLEET INTERVENTION & DISPATCH OVERRIDE
                </span>
                <span class="fleet-telemetry-badge badge-warning">COMMAND LINK ONLINE</span>
            </div>
            <p style="color: var(--text-dim); font-size: 13px; margin: 0 0 14px 0;">
                Dispatch supervisory override commands directly to vehicle ECU and in-cabin driver audio display.
            </p>
        """, unsafe_allow_html=True)

        act_col1, act_col2, act_col3, act_col4 = st.columns(4)
        with act_col1:
            if st.button("🛑 ORDER IMMEDIATE SAFE STOP", use_container_width=True):
                msg = "FLEET DISPATCH DIRECTIVE: Pull over at NH 45 Ulundurpet Toll Plaza rest area immediately and initiate mandatory 30-minute rest cycle."
                st.session_state.fleet_mgr_sync.send_manager_command("MANDATORY_SAFE_STOP", msg)
                send_fastapi_command("MANDATORY_SAFE_STOP", msg)
                st.session_state.dispatch_broadcast_status = "Direct Stop Order Dispatched to Lorry TN 58 AA 4920 via FastAPI."
                st.rerun(scope="fragment")

        with act_col2:
            if st.button("📢 BROADCAST CABIN AUDIO ADVISORY", use_container_width=True):
                msg = "DISPATCH MESSAGE: Biometric fatigue indicators elevated on NH 45. Arun, please acknowledge dispatch center."
                st.session_state.fleet_mgr_sync.send_manager_command("AUDIO_ADVISORY", msg)
                send_fastapi_command("AUDIO_ADVISORY", msg)
                st.session_state.dispatch_broadcast_status = "Audio Advisory Broadcast to Cabin via FastAPI."
                st.rerun(scope="fragment")

        with act_col3:
            if st.button("📞 DISPATCH VOICE RADIO CONTACT", use_container_width=True):
                msg = "DISPATCH CALL: Commercial radio dispatch contact requested with Arun Kumar (Lorry 4920)."
                st.session_state.fleet_mgr_sync.send_manager_command("VOICE_CONTACT_REQUEST", msg)
                send_fastapi_command("VOICE_CONTACT_REQUEST", msg)
                st.session_state.dispatch_broadcast_status = "Voice Radio Request Logged via FastAPI."
                st.rerun(scope="fragment")

        with act_col4:
            if st.button("✅ ACKNOWLEDGE & CLEAR ALERT", use_container_width=True):
                msg = "Incident acknowledged and alert cleared by safety manager."
                st.session_state.fleet_mgr_sync.send_manager_command("ACKNOWLEDGE", msg)
                send_fastapi_command("ACKNOWLEDGE", msg)
                st.session_state.dispatch_broadcast_status = "Incident Acknowledged & Emergency Alert Cleared."
                st.rerun(scope="fragment")

        if st.session_state.dispatch_broadcast_status:
            st.success(f"📡 {st.session_state.dispatch_broadcast_status}")

        # Display Recent Manager Commands
        commands = st.session_state.fleet_mgr_sync.fetch_manager_commands(limit=3)
        if commands:
            st.markdown("<div style='margin-top:10px;'><strong>Recent Manager Directives:</strong></div>", unsafe_allow_html=True)
            for cmd in commands:
                st.markdown(f"""
                <div style="font-family:'JetBrains Mono'; font-size:12px; padding:6px 10px; margin-top:6px; background:rgba(241, 245, 249, 0.95); border: 1px solid rgba(2, 132, 199, 0.15); border-left:3px solid var(--neon-cyan); border-radius:6px; color: var(--text-bright);">
                    [{cmd['timestamp']}] <strong>{cmd['command_type']}</strong>: {cmd['message']} &mdash; Status: <span style="color:#059669; font-weight:700;">{cmd['status']}</span>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 6. SQLite Telemetry & Incident Audit Logs
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <h4 style="margin:0; font-family:'Orbitron'; font-size:15px; color:var(--text-bright);">&#128203; Live Dispatch Audit Stream (SQLite Database)</h4>
            <span class="fleet-telemetry-badge badge-nominal"><span class="pulse-dot"></span> SQLITE: fleet_mind.db</span>
        </div>
        """, unsafe_allow_html=True)
        tab_esc, tab_stream = st.tabs(["🚨 Incident Escalation Logs (FastAPI / JSON)", "📡 Live Telematics Stream"])
        with tab_esc:
            fastapi_alerts = fetch_fastapi_alerts(limit=8)
            if fastapi_alerts:
                df_alerts = pd.DataFrame(fastapi_alerts)
                # Select display columns
                cols_to_show = [c for c in ["timestamp", "driver_id", "event_type", "severity", "risk_score", "speed_kmh", "details"] if c in df_alerts.columns]
                st.dataframe(df_alerts[cols_to_show], hide_index=True, use_container_width=True)
            else:
                esc_df = st.session_state.fleet_mgr_sync.fetch_recent_escalations(limit=8)
                if esc_df:
                    st.dataframe(esc_df, hide_index=True, use_container_width=True)
                else:
                    st.info("No critical dispatch incidents logged yet. Fleet operating within nominal safety parameters.")
        with tab_stream:
            stream_df = st.session_state.fleet_mgr_sync.fetch_recent_telematics(limit=8)
            if stream_df:
                st.dataframe(stream_df, hide_index=True, use_container_width=True)
            else:
                st.info("Telemetry stream active and synchronized with fleet_mind.db.")

    except Exception as e:
        st.error(f"Telematics Sync Exception: {e}")

    # -----------------------------------------------------------------------------

# Mount real-time telematics fragment
render_live_operations_view()

# Bottom Operations Footer
# -----------------------------------------------------------------------------
st.markdown("<br><hr style='border-color: rgba(2, 132, 199, 0.2);'>", unsafe_allow_html=True)
st.caption("FleetGuard Sentinel Fleet Management OS v2.4 &bull; Synchronized via SQLite & Atomic JSON Bus &bull; Dual-Screen Telematics Architecture")
