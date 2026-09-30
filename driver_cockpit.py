"""
================================================================================
ANTI-GRAVITY // FLEET MANAGEMENT & DRIVER COCKPIT DASHBOARD
================================================================================
Executive-level commercial fleet safety system featuring:
- Modern Anti-Gravity UI Theme (deep slate #0d1117 background, floating glass-morphic containers, glowing neon cyan #00f2fe highlights, amber/red #ff0055 emergency accents)
- Header: Floating status pills displaying system status (ONLINE) and SQLite database connection status (fleet_mind.db)
- Left Panel (Driver Safety Node): Live webcam feed, Eye Aspect Ratio (EAR) and Mouth Aspect Ratio (MAR) metrics
- Right Panel (Fleet Telematics): Simulated vehicle GPS on st.map() and large digital speedometer reading from local fleet_mind.db
- Active Escalation Logic: Game-style auto-aim lock; speed poll: green SAFE STOP banner if speed == 0 km/h, massive pulsing red DISPATCHER ESCALATION ACTIVE modal overlay if speed > 0 km/h
"""

import time
import os
import sqlite3
import socket
import cv2
import numpy as np
import pandas as pd
import requests
import streamlit as st

# Import Existing Backend Modules (Preserving all original signatures and structures)
from modules.styles import get_audio_alert_html, get_spoken_voice_alert_html
from modules.audio_alerts import speak_aloud, render_browser_voice_component
from modules.vision import FaceAnalysisModule
from modules.telematics import TelematicsModule
from modules.risk_engine import DynamicRiskEngine, RiskLevel, InterventionStatus
from modules.fleet_sync import FleetSyncManager
from modules.safety_core import SentinelSafetyCore


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


# Dynamic Backend URL from session_state or default
if "fastapi_url" not in st.session_state:
    st.session_state.fastapi_url = "http://localhost:8000"

FASTAPI_URL = st.session_state.fastapi_url


def check_fastapi_connection() -> bool:
    """Verifies whether the FastAPI backend is online."""
    try:
        r = requests.get(f"{st.session_state.fastapi_url}/health", timeout=0.25)
        return r.status_code == 200
    except Exception:
        return False


def poll_dispatcher_commands():
    """Polls FastAPI for incoming directives dispatched from Fleet Manager Laptop."""
    try:
        url = f"{st.session_state.fastapi_url}/commands?vehicle_id=TN 58 AA 4920&limit=1"
        r = requests.get(url, timeout=0.25)
        if r.status_code == 200:
            cmds = r.json()
            if cmds:
                latest = cmds[0]
                last_seen_id = st.session_state.get("_last_seen_cmd_id", None)
                cmd_id = latest.get("id") or latest.get("timestamp")
                if cmd_id != last_seen_id:
                    st.session_state._last_seen_cmd_id = cmd_id
                    cmd_type = latest.get("command_type", "DIRECTIVE")
                    msg = latest.get("message", "")
                    spoken_text = f"Fleet Manager Directive: {msg}"
                    speak_aloud(spoken_text, category="dispatcher_cmd", priority=True)
                    st.session_state.latest_safety_directive = {
                        "text": msg,
                        "source": f"Fleet Manager ({cmd_type})",
                        "timestamp": time.strftime("%H:%M:%S")
                    }
                    st.session_state.incident_logs.append(f"[{time.strftime('%H:%M:%S')}] DISPATCH DIRECTIVE: {msg}")
                    if cmd_type == "MANDATORY_SAFE_STOP":
                        st.session_state.target_lock_engaged = True
    except Exception:
        pass


def send_telemetry_to_fastapi(telematics_data: dict, vision_data: dict, risk_data: dict):
    """Sends continuous driver telemetry & risk score to FastAPI backend."""
    payload = {
        "driver_id": "D001",
        "driver_name": "Arun Kumar (Operator #104)",
        "vehicle_id": "TN 58 AA 4920",
        "speed_kmh": float(telematics_data.get("speed_kmh", 0.0)),
        "acceleration_kmh_s": float(telematics_data.get("acceleration_kmh_s", 0.0)),
        "latitude": float(telematics_data.get("latitude", 11.2335)),
        "longitude": float(telematics_data.get("longitude", 78.8817)),
        "heading_deg": float(telematics_data.get("heading_deg", 38.0)),
        "ear": float(vision_data.get("ear", 0.30)),
        "mar": float(vision_data.get("mar", 0.25)),
        "eye_closed_seconds": float(vision_data.get("eye_closed_duration", 0.0)),
        "is_yawning": bool(vision_data.get("is_yawning", False)),
        "microsleep_detected": bool(vision_data.get("microsleep_detected", False)),
        "risk_score": float(risk_data.get("risk_score", 0.0)),
        "risk_level": str(risk_data.get("risk_level", "NOMINAL")),
        "driver_action": str(risk_data.get("driver_action", "Nominal operation"))
    }
    try:
        requests.post(f"{st.session_state.fastapi_url}/risk", json=payload, timeout=0.25)
    except Exception:
        pass


def send_event_to_fastapi(event_type: str, severity: str, risk_score: float, speed_kmh: float, details: str):
    """Sends explicit sensor/risk events to FastAPI backend."""
    payload = {
        "driver_id": "D001",
        "vehicle_id": "TN 58 AA 4920",
        "event_type": event_type,
        "severity": severity,
        "risk_score": float(risk_score),
        "speed_kmh": float(speed_kmh),
        "details": details
    }
    try:
        requests.post(f"{st.session_state.fastapi_url}/events", json=payload, timeout=0.4)
    except Exception:
        pass

# -----------------------------------------------------------------------------
# System Application Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ANTI-GRAVITY // Fleet Command HUD",
    page_icon="🛸",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -----------------------------------------------------------------------------
# Anti-Gravity UI Theme: Custom CSS (Deep Slate #0d1117, Glass, Neon Cyan, Red)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;800;900&family=Rajdhani:wght@500;600;700&family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

:root {
    --bg-deep: #0d1117;
    --bg-card: rgba(22, 27, 34, 0.78);
    --border-card: rgba(48, 54, 61, 0.75);
    --neon-cyan: #00f2fe;
    --neon-cyan-glow: rgba(0, 242, 254, 0.45);
    --neon-emerald: #00ff88;
    --neon-amber: #ffaa00;
    --neon-red: #ff0055;
    --neon-red-glow: rgba(255, 0, 85, 0.55);
    --text-primary: #f0f6fc;
    --text-secondary: #8b949e;
    --text-muted: #6e7681;
}

html, body, [data-testid="stAppViewContainer"], .main {
    background-color: var(--bg-deep) !important;
    background-image: 
        radial-gradient(circle at 15% 15%, rgba(0, 242, 254, 0.05) 0%, transparent 45%),
        radial-gradient(circle at 85% 85%, rgba(255, 0, 85, 0.04) 0%, transparent 45%),
        linear-gradient(180deg, #0d1117 0%, #090d13 100%) !important;
    background-attachment: fixed !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
}

[data-testid="stHeader"] {
    background: transparent !important;
}

.ag-card {
    background: var(--bg-card);
    backdrop-filter: blur(16px);
    border: 1px solid var(--border-card);
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 20px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    transition: all 0.3s ease;
}

.ag-card:hover {
    border-color: rgba(0, 242, 254, 0.4);
    box-shadow: 0 12px 35px rgba(0, 242, 254, 0.12);
}

.ag-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(48, 54, 61, 0.6);
    padding-bottom: 12px;
    margin-bottom: 16px;
}

.ag-card-title {
    font-family: 'Orbitron', monospace;
    font-size: 15px;
    font-weight: 700;
    color: var(--neon-cyan);
    letter-spacing: 1.5px;
    display: flex;
    align-items: center;
    gap: 8px;
    text-shadow: 0 0 12px var(--neon-cyan-glow);
}

.ag-header-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(22, 27, 34, 0.85);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(0, 242, 254, 0.25);
    border-radius: 12px;
    padding: 14px 22px;
    margin-bottom: 20px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
}

.ag-brand-title {
    font-family: 'Orbitron', monospace;
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 2px;
    color: #ffffff;
}

.ag-brand-title span {
    color: var(--neon-cyan);
    text-shadow: 0 0 15px var(--neon-cyan-glow);
}

.ag-status-pills {
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
}

.ag-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    padding: 6px 14px;
    border-radius: 9999px;
    text-transform: uppercase;
}

.ag-pill-online {
    background: rgba(0, 255, 136, 0.1);
    color: var(--neon-emerald);
    border: 1px solid rgba(0, 255, 136, 0.35);
    box-shadow: 0 0 10px rgba(0, 255, 136, 0.2);
}

.ag-pill-db {
    background: rgba(0, 242, 254, 0.1);
    color: var(--neon-cyan);
    border: 1px solid rgba(0, 242, 254, 0.35);
    box-shadow: 0 0 10px rgba(0, 242, 254, 0.2);
}

.ag-pill-vehicle {
    background: rgba(240, 246, 252, 0.06);
    color: var(--text-primary);
    border: 1px solid rgba(240, 246, 252, 0.18);
}

.pulse-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--neon-emerald);
    box-shadow: 0 0 8px var(--neon-emerald);
    animation: pulseGlow 1.5s infinite alternate;
}

.pulse-dot-cyan {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--neon-cyan);
    box-shadow: 0 0 8px var(--neon-cyan);
    animation: pulseGlow 1.5s infinite alternate;
}

.pulse-dot-red {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--neon-red);
    box-shadow: 0 0 10px var(--neon-red);
    animation: pulseCrit 0.8s infinite alternate;
}

@keyframes pulseGlow {
    0% { transform: scale(0.9); opacity: 0.6; }
    100% { transform: scale(1.2); opacity: 1; }
}

@keyframes pulseCrit {
    0% { transform: scale(0.85); box-shadow: 0 0 6px var(--neon-red); }
    100% { transform: scale(1.3); box-shadow: 0 0 18px var(--neon-red); }
}

.ag-metric-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-top: 14px;
}

.ag-metric-tile {
    background: rgba(13, 17, 23, 0.7);
    border: 1px solid rgba(48, 54, 61, 0.8);
    border-radius: 10px;
    padding: 12px 14px;
    text-align: center;
    transition: border-color 0.2s;
}

.ag-metric-tile:hover {
    border-color: rgba(0, 242, 254, 0.35);
}

.ag-metric-val {
    font-family: 'Orbitron', monospace;
    font-size: 24px;
    font-weight: 800;
    color: var(--neon-cyan);
    letter-spacing: 0.5px;
}

.ag-metric-lbl {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 4px;
}

.ag-speedometer-box {
    background: radial-gradient(circle at center, rgba(0, 242, 254, 0.08) 0%, rgba(13, 17, 23, 0.95) 75%);
    border: 1px solid rgba(0, 242, 254, 0.3);
    border-radius: 14px;
    padding: 24px 16px;
    text-align: center;
    margin-top: 16px;
    box-shadow: inset 0 0 25px rgba(0, 242, 254, 0.06);
}

.ag-speed-number {
    font-family: 'Orbitron', monospace;
    font-size: 78px;
    font-weight: 900;
    line-height: 1;
    background: linear-gradient(180deg, #ffffff 10%, #00f2fe 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: drop-shadow(0 0 16px rgba(0, 242, 254, 0.4));
    letter-spacing: -2px;
}

.ag-speed-unit {
    font-family: 'Orbitron', monospace;
    font-size: 13px;
    color: var(--neon-cyan);
    letter-spacing: 3px;
    margin-top: 2px;
    font-weight: 700;
}

.ag-speed-source {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 6px;
}

.ag-target-lock {
    background: rgba(255, 0, 85, 0.12);
    border: 1px solid var(--neon-red);
    border-radius: 10px;
    padding: 12px 18px;
    margin-bottom: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    animation: reticlePulse 1.2s infinite alternate;
}

@keyframes reticlePulse {
    0% { border-color: rgba(255, 0, 85, 0.4); box-shadow: 0 0 10px rgba(255, 0, 85, 0.2); }
    100% { border-color: rgba(255, 0, 85, 1); box-shadow: 0 0 24px rgba(255, 0, 85, 0.6); }
}

.ag-target-lock-title {
    font-family: 'Orbitron', monospace;
    font-size: 13px;
    font-weight: 800;
    color: #ff3377;
    letter-spacing: 1.5px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.ag-safe-stop-banner {
    background: rgba(0, 255, 136, 0.12);
    border: 2px solid var(--neon-emerald);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 18px;
    box-shadow: 0 0 25px rgba(0, 255, 136, 0.35);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.ag-safe-stop-title {
    font-family: 'Orbitron', monospace;
    font-size: 16px;
    font-weight: 800;
    color: var(--neon-emerald);
    letter-spacing: 1.5px;
}

.ag-modal-overlay {
    background: rgba(13, 17, 23, 0.94);
    border: 2px solid var(--neon-red);
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 22px;
    box-shadow: 0 0 45px rgba(255, 0, 85, 0.55), inset 0 0 25px rgba(255, 0, 85, 0.2);
    animation: modalPulse 1.2s infinite alternate;
}

@keyframes modalPulse {
    0% { transform: scale(0.995); border-color: #ff0055; box-shadow: 0 0 30px rgba(255, 0, 85, 0.4); }
    100% { transform: scale(1.002); border-color: #ff3377; box-shadow: 0 0 60px rgba(255, 0, 85, 0.85); }
}

.ag-modal-badge {
    display: inline-block;
    background: var(--neon-red);
    color: #ffffff;
    font-family: 'Orbitron', monospace;
    font-size: 12px;
    font-weight: 900;
    letter-spacing: 1.5px;
    padding: 4px 12px;
    border-radius: 4px;
    margin-bottom: 8px;
    box-shadow: 0 0 12px var(--neon-red);
}

.ag-modal-title {
    font-family: 'Orbitron', monospace;
    font-size: 24px;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: 2px;
    text-shadow: 0 0 16px var(--neon-red);
    margin: 4px 0 10px 0;
}

.ag-modal-body {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: #ffb3c6;
    line-height: 1.6;
}

.stButton > button {
    background: rgba(22, 27, 34, 0.9) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-card) !important;
    border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    transition: all 0.2s ease !important;
}

.stButton > button:hover {
    border-color: var(--neon-cyan) !important;
    color: var(--neon-cyan) !important;
    box-shadow: 0 0 14px rgba(0, 242, 254, 0.3) !important;
}

[data-testid="stSelectbox"] label, [data-testid="stSlider"] label {
    color: var(--text-secondary) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
    text-transform: uppercase !important;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Database Telematics Reader (Live SQLite connection to fleet_mind.db)
# -----------------------------------------------------------------------------
def get_latest_telematics_from_db() -> dict:
    """Queries the local fleet_mind.db SQLite database for the latest speed & GPS record and live stats."""
    db_file = "fleet_mind.db"
    default_record = {
        "speed_kmh": 68.0,
        "acceleration_kmh_s": 0.2,
        "latitude": 11.2335,
        "longitude": 78.8817,
        "heading_deg": 38.0,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "db_connected": False,
        "total_records": 0,
        "stream_records": 0,
        "db_size_kb": 0.0
    }

    if not os.path.exists(db_file):
        return default_record

    try:
        size_kb = round(os.path.getsize(db_file) / 1024.0, 1)
        with sqlite3.connect(db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM telematics")
            total_records = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM telematics_stream")
            stream_records = cursor.fetchone()[0]
            cursor.execute("""
            SELECT speed_kmh, acceleration_kmh_s, latitude, longitude, heading_deg, timestamp
            FROM telematics
            ORDER BY id DESC
            LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return {
                    "speed_kmh": float(row[0]),
                    "acceleration_kmh_s": float(row[1]) if row[1] is not None else 0.0,
                    "latitude": float(row[2]) if row[2] is not None else 11.2335,
                    "longitude": float(row[3]) if row[3] is not None else 78.8817,
                    "heading_deg": float(row[4]) if row[4] is not None else 38.0,
                    "timestamp": str(row[5]),
                    "db_connected": True,
                    "total_records": total_records,
                    "stream_records": stream_records,
                    "db_size_kb": size_kb
                }
    except Exception:
        pass

    default_record["db_connected"] = os.path.exists(db_file)
    return default_record


# -----------------------------------------------------------------------------
# State Initialization (Preserving existing backend signatures & variable names)
# -----------------------------------------------------------------------------
if "incident_logs" not in st.session_state:
    st.session_state.incident_logs = []

if "latest_safety_directive" not in st.session_state:
    st.session_state.latest_safety_directive = {
        "text": "Sentinel Safety Core active. Biometrics and telematics online.",
        "source": "Sentinel Onboard Safety Engine",
        "timestamp": time.strftime("%H:%M:%S")
    }

if "safety_core" not in st.session_state:
    st.session_state.safety_core = SentinelSafetyCore()

if "vision_module" not in st.session_state:
    st.session_state.vision_module = FaceAnalysisModule(
        ear_threshold=0.22,
        microsleep_duration_sec=2.0,
        mar_threshold=0.60,
        yawn_min_duration_sec=1.0
    )

if "telematics_module" not in st.session_state:
    st.session_state.telematics_module = TelematicsModule(initial_speed=68.0)

if "risk_engine" not in st.session_state:
    st.session_state.risk_engine = DynamicRiskEngine()

if "fleet_sync_mgr" not in st.session_state:
    st.session_state.fleet_sync_mgr = FleetSyncManager(
        vehicle_id="TN 58 AA 4920",
        driver_name="Arun Kumar (Operator #104)"
    )

if "stream_active" not in st.session_state:
    st.session_state.stream_active = False

if "video_source_mode" not in st.session_state:
    st.session_state.video_source_mode = "Webcam (Live OpenCV)"

if "synthetic_driver_state" not in st.session_state:
    st.session_state.synthetic_driver_state = "nominal"

if "target_lock_engaged" not in st.session_state:
    st.session_state.target_lock_engaged = False


# -----------------------------------------------------------------------------
# Distributed 2-Laptop Setup & In-Cabin Speaker Controls (Sidebar)
# -----------------------------------------------------------------------------
local_ip = get_local_ip()

with st.sidebar:
    st.markdown("""
    <div style="font-family: 'Orbitron'; font-size: 16px; font-weight: 700; color: #00f2fe; margin-bottom: 8px;">
        🛸 IN-CABIN COCKPIT & SENSOR
    </div>
    <div style="font-family: 'JetBrains Mono'; font-size: 11px; color: #8b949e; margin-bottom: 16px;">
        LAPTOP 1: SENSOR + IN-CABIN HUD + LOUD ALOUD SPEAKER
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background: rgba(22, 27, 34, 0.85); border: 1px solid rgba(48, 54, 61, 0.8); border-radius: 8px; padding: 12px; margin-bottom: 14px;">
        <div style="font-size: 10px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px;">THIS LAPTOP WI-FI IP:</div>
        <div style="font-family: 'JetBrains Mono'; font-size: 16px; color: #00ff88; font-weight: 700; margin-top: 2px;">{local_ip}</div>
        <div style="font-size: 11px; color: #8b949e; margin-top: 6px;">
            Port <strong>8501</strong>: In-Cabin Driver Cockpit<br>
            Port <strong>8000</strong>: FastAPI Telematics Backend
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background: rgba(0, 242, 254, 0.08); border: 1px solid rgba(0, 242, 254, 0.3); border-radius: 8px; padding: 12px; margin-bottom: 16px;">
        <div style="font-size: 10px; color: #00f2fe; text-transform: uppercase; font-weight: 700;">FOR LAPTOP 2 (FLEET MANAGER):</div>
        <div style="font-size: 11px; color: #f0f6fc; margin-top: 4px;">
            Open in browser on Laptop 2:<br>
            <code style="color: #00f2fe; background: rgba(0,0,0,0.4); padding: 2px 6px; border-radius: 4px;">http://{local_ip}:8502</code>
        </div>
    </div>
    """, unsafe_allow_html=True)

    backend_input = st.text_input("FastAPI Backend URL", value=st.session_state.fastapi_url)
    if backend_input != st.session_state.fastapi_url:
        st.session_state.fastapi_url = backend_input.rstrip("/")
        st.rerun()

    st.markdown("<hr style='border-color: rgba(48, 54, 61, 0.6); margin: 16px 0;'>", unsafe_allow_html=True)

    st.markdown("""
    <div style="font-family: 'Orbitron'; font-size: 13px; font-weight: 700; color: #ffaa00; margin-bottom: 6px;">
        🔊 IN-CABIN AUDIO SYSTEM
    </div>
    <div style="font-size: 11px; color: #8b949e; margin-bottom: 10px;">
        Outputs loud voice directives and siren through physical laptop speakers.
    </div>
    """, unsafe_allow_html=True)

    if st.button("🔊 TEST IN-CABIN VOICE SPEAKER", use_container_width=True, key="btn_test_speaker"):
        speak_aloud("Fleet Sentinel In-Cabin Safety System online. Physical laptop speaker test verified.", category="test", priority=True)
        render_browser_voice_component("Fleet Sentinel In-Cabin Safety System online. Physical laptop speaker test verified.", tone=True)
        st.toast("🔊 Voice alert dispatched to physical laptop speakers!", icon="📢")

    st.markdown("<br>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Top Header: Floating Status Pills
# -----------------------------------------------------------------------------
db_status = get_latest_telematics_from_db()
db_connected = db_status.get("db_connected", False)
total_recs = db_status.get("total_records", 0)
rec_label = f": {total_recs:,} records" if total_recs > 0 else ""
fastapi_online = check_fastapi_connection()

st.markdown(f"""
<div class="ag-header-bar">
    <div class="ag-brand-title">
        <span>&#128752; ANTI-GRAVITY</span> // FLEET SENTINEL COMMAND HUD
    </div>
    <div class="ag-status-pills">
        <div class="ag-pill ag-pill-online">
            <span class="pulse-dot"></span> SYSTEM ONLINE
        </div>
        <div class="ag-pill ag-pill-db" style="border-color: {'rgba(0, 242, 254, 0.4)' if fastapi_online else 'rgba(255, 170, 0, 0.4)'};">
            <span class="{'pulse-dot-cyan' if fastapi_online else 'pulse-dot'}"></span> FASTAPI: {'ONLINE (Port 8000)' if fastapi_online else 'OFFLINE (Local Standby)'}
        </div>
        <div class="ag-pill ag-pill-db">
            <span class="pulse-dot-cyan"></span> DATABASE: {'JSON + SQLITE SYNC' if db_connected else 'JSON REPO ACTIVE'}
        </div>
        <div class="ag-pill ag-pill-vehicle">
            UNIT: <strong style="color: var(--neon-cyan); margin-left: 4px;">TN 58 AA 4920</strong> &bull; ARUN KUMAR
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Quick Verification Scenario Bar (1-Click Test Harness)
# -----------------------------------------------------------------------------
with st.expander("🕹️ SIMULATOR VERIFICATION CONTROLS // SCENARIOS & CALIBRATION", expanded=False):
    s_col1, s_col2, s_col3, s_col4, s_col5, s_col6, s_col7 = st.columns(7)
    
    with s_col1:
        if st.button("🟢 Scenario 1: Nominal Driving", use_container_width=True, key="sc_norm"):
            st.session_state.risk_engine.reset_intervention()
            st.session_state.vision_module.reset()
            st.session_state.telematics_module.reset(68.0)
            st.session_state.target_lock_engaged = False
            t_data = st.session_state.telematics_module.step(dt=0.2)
            v_data = st.session_state.vision_module.generate_synthetic_frame(driver_mode="nominal")
            r_data = st.session_state.risk_engine.compute_risk(v_data, t_data)
            st.session_state.fleet_sync_mgr.sync_telematics_frame(t_data, v_data, r_data)
            send_telemetry_to_fastapi(t_data, v_data, r_data)
            speak_aloud("Nominal driving restored. Systems nominal.", category="nominal", priority=True)
            st.session_state.incident_logs.append(f"[{time.strftime('%H:%M:%S')}] NOMINAL: Systems nominal. Risk: {r_data['risk_score']}%.")
            st.rerun()

    with s_col2:
        if st.button("🔴 Scenario 2: Microsleep (> 2s)", use_container_width=True, key="sc_micro"):
            st.session_state.risk_engine.reset_intervention()
            st.session_state.vision_module.reset()
            st.session_state.telematics_module.current_speed = 76.0
            st.session_state.telematics_module.set_target_speed(88.0)
            st.session_state.target_lock_engaged = True
            t_data = st.session_state.telematics_module.step(dt=0.2)
            v_data = st.session_state.vision_module.generate_synthetic_frame(driver_mode="microsleep")
            v_data["ear"] = 0.11
            v_data["eye_closed_duration"] = 2.5
            v_data["microsleep_detected"] = True
            r_data = st.session_state.risk_engine.compute_risk(v_data, t_data)
            st.session_state.fleet_sync_mgr.sync_telematics_frame(t_data, v_data, r_data)
            send_telemetry_to_fastapi(t_data, v_data, r_data)
            send_event_to_fastapi("microsleep", "CRITICAL", r_data["risk_score"], t_data["speed_kmh"], "Microsleep episode detected (> 2.0s eyes closed)")
            speak_aloud("Emergency warning! Driver eyes closed detected! Wake up and pull over safely!", category="microsleep", priority=True)
            st.session_state.incident_logs.append(f"[{time.strftime('%H:%M:%S')}] CRITICAL: Microsleep detected. Target Lock engaged.")
            st.rerun()

    with s_col3:
        if st.button("🔴 Scenario 3: Repeated Yawning", use_container_width=True, key="sc_yawn"):
            st.session_state.risk_engine.reset_intervention()
            st.session_state.vision_module.reset()
            st.session_state.telematics_module.current_speed = 72.0
            st.session_state.target_lock_engaged = True
            t_data = st.session_state.telematics_module.step(dt=0.2)
            v_data = st.session_state.vision_module.generate_synthetic_frame(driver_mode="yawn")
            v_data["mar"] = 0.74
            v_data["is_yawning"] = True
            v_data["recent_yawns_count"] = 3
            v_data["total_yawns"] = 4
            r_data = st.session_state.risk_engine.compute_risk(v_data, t_data)
            st.session_state.fleet_sync_mgr.sync_telematics_frame(t_data, v_data, r_data)
            send_telemetry_to_fastapi(t_data, v_data, r_data)
            send_event_to_fastapi("yawn", "WARNING", r_data["risk_score"], t_data["speed_kmh"], "Repeated yawning cluster detected")
            speak_aloud("Warning. Repeated yawning detected. High driver fatigue advisory.", category="yawn", priority=True)
            st.session_state.incident_logs.append(f"[{time.strftime('%H:%M:%S')}] WARNING: Yawn frequency elevated. Target Lock engaged.")
            st.rerun()

    with s_col4:
        if st.button("⚠️ Scenario 4: Hard Braking", use_container_width=True, key="sc_brake"):
            st.session_state.telematics_module.trigger_preset_scenario("hard_brake")
            t_data = st.session_state.telematics_module.step(dt=0.2)
            v_data = st.session_state.vision_module.generate_synthetic_frame(driver_mode="drowsy")
            r_data = st.session_state.risk_engine.compute_risk(v_data, t_data)
            st.session_state.fleet_sync_mgr.sync_telematics_frame(t_data, v_data, r_data)
            send_telemetry_to_fastapi(t_data, v_data, r_data)
            send_event_to_fastapi("hard_brake", "WARNING", r_data["risk_score"], t_data["speed_kmh"], "Hard braking instability event")
            speak_aloud("Caution: Sudden hard braking detected.", category="hard_brake", priority=True)
            st.rerun()

    with s_col5:
        if st.button("🛡️ Scenario 5: Safe Stop (0 km/h)", use_container_width=True, key="sc_stop"):
            st.session_state.telematics_module.set_target_speed(0.0)
            st.session_state.telematics_module.current_speed = 0.0
            t_data = st.session_state.telematics_module.step(dt=0.2)
            v_data = st.session_state.vision_module.generate_synthetic_frame(driver_mode="nominal")
            r_data = st.session_state.risk_engine.compute_risk(v_data, t_data)
            st.session_state.fleet_sync_mgr.sync_telematics_frame(t_data, v_data, r_data)
            send_telemetry_to_fastapi(t_data, v_data, r_data)
            send_event_to_fastapi("safe_stop", "INFO", r_data["risk_score"], 0.0, "Safe Stop confirmed at rest area")
            speak_aloud("Safe stop confirmed. Vehicle secured at rest area.", category="safe_stop", priority=True)
            st.session_state.incident_logs.append(f"[{time.strftime('%H:%M:%S')}] SAFE STOP: Vehicle brought to 0.0 km/h halt.")
            st.rerun()

    with s_col6:
        if st.button("💾 Scenario 6: SQLite Stream", use_container_width=True, key="sc_dbstream"):
            st.session_state.telematics_module.enable_db_playback(True)
            t_data = st.session_state.telematics_module.step(dt=0.2)
            v_data = st.session_state.vision_module.generate_synthetic_frame(driver_mode="nominal")
            r_data = st.session_state.risk_engine.compute_risk(v_data, t_data)
            st.session_state.fleet_sync_mgr.sync_telematics_frame(t_data, v_data, r_data)
            send_telemetry_to_fastapi(t_data, v_data, r_data)
            st.session_state.incident_logs.append(f"[{time.strftime('%H:%M:%S')}] SQLITE PLAYBACK: Activated high-frequency dataset stream from fleet_mind.db.")
            st.rerun()

    with s_col7:
        if st.button("🔄 Reset System & State", use_container_width=True, key="sc_reset"):
            st.session_state.risk_engine.reset_intervention()
            st.session_state.vision_module.reset()
            st.session_state.telematics_module.reset(68.0)
            st.session_state.target_lock_engaged = False
            t_data = st.session_state.telematics_module.step(dt=0.2)
            v_data = st.session_state.vision_module.generate_synthetic_frame(driver_mode="nominal")
            r_data = st.session_state.risk_engine.compute_risk(v_data, t_data)
            st.session_state.fleet_sync_mgr.sync_telematics_frame(t_data, v_data, r_data)
            send_telemetry_to_fastapi(t_data, v_data, r_data)
            speak_aloud("Fleet Sentinel safety systems reset to nominal.", category="reset", priority=True)
            st.success("System reset to nominal.")
            st.rerun()


# -----------------------------------------------------------------------------
# Active Escalation Logic (Game Auto-Aim Target Lock & Safe Stop / Escalation Modal)
# -----------------------------------------------------------------------------
current_risk_score = st.session_state.risk_engine.risk_score
current_risk_level = st.session_state.risk_engine.risk_level
is_fatigue_alert = (current_risk_level == RiskLevel.CRITICAL or current_risk_score >= 70.0 or st.session_state.target_lock_engaged)

# Fetch latest speed continuously from local fleet_mind.db
db_telemetry = get_latest_telematics_from_db()
latest_db_speed = db_telemetry.get("speed_kmh", 0.0)

# 1. AUTO-AIM LOCK ENGAGEMENT
if is_fatigue_alert:
    st.markdown(f"""
    <div class="ag-target-lock">
        <div class="ag-target-lock-title">
            <span>🎯</span> AUTO-AIM TARGET LOCK ENGAGED // LOCKED ON SPEED TELEMETRY
        </div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #ffb3c6;">
            POLLING: <strong style="color: var(--neon-cyan);">fleet_mind.db</strong> &bull; SPEED: <strong>{latest_db_speed:.1f} km/h</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. ESCALATION FORK: Speed == 0 vs Speed > 0
    if latest_db_speed == 0.0:
        # Green SAFE STOP Banner
        st.markdown("""
        <div class="ag-safe-stop-banner">
            <div>
                <div class="ag-safe-stop-title">&#10004; SAFE STOP CONFIRMED &mdash; VEHICLE SECURED</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #00ff88; margin-top: 4px;">
                    SPEED: 0.0 KM/H &bull; Parking brake engaged at NH 45 safe rest area. Operator rest verified.
                </div>
            </div>
            <div>
                <span class="ag-pill ag-pill-online" style="font-size: 12px;">SAFE STOP OK</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        speak_aloud("Safe stop confirmed. Vehicle secured.", category="safe_stop_banner", cooldown_sec=10.0)
    else:
        # Speed > 0 km/h: System does NOT lose focus & triggers massive pulsing red modal overlay
        speak_aloud("Critical alert: High driver fatigue while vehicle is at speed! Decelerate now!", category="high_speed_fatigue", cooldown_sec=4.0)
        st.markdown(f"""
        <div class="ag-modal-overlay">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div class="ag-modal-badge">&#128680; HIGH-FATIGUE AUTO-AIM LOCK ACTIVE</div>
                    <div class="ag-modal-title">DISPATCHER ESCALATION ACTIVE</div>
                </div>
                <div>
                    <span class="ag-pill" style="background: rgba(255, 0, 85, 0.2); color: #ff0055; border: 1px solid #ff0055;">
                        <span class="pulse-dot-red"></span> CRITICAL HAZARD
                    </span>
                </div>
            </div>
            <div class="ag-modal-body">
                <strong>CRITICAL INTERVENTION DIRECTIVE:</strong> High driver fatigue detected while vehicle maintains active highway speed!
                <div style="margin-top: 8px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; font-size: 12px;">
                    <div>VEHICLE: <strong style="color:#ffffff;">TN 58 AA 4920</strong></div>
                    <div>OPERATOR: <strong style="color:#ffffff;">ARUN KUMAR</strong></div>
                    <div>CURRENT SPEED: <strong style="color:#ff3377; font-size:14px;">{latest_db_speed:.1f} KM/H</strong></div>
                    <div>RISK INDEX: <strong style="color:#ff3377; font-size:14px;">{current_risk_score:.1f}%</strong></div>
                </div>
                <div style="margin-top: 10px; color: #ffffff;">
                    &bull; System is actively tracking vehicle deceleration. Pull vehicle over immediately.<br>
                    &bull; Emergency alert tone broadcasted to driver cabin. Dispatcher supervisory channel locked.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(get_audio_alert_html(active=True), unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Main Dashboard Layout: Two Balanced Panels
# Left: Driver Safety Node (Webcam, EAR, MAR)
# Right: Fleet Telematics (st.map(), Speedometer from fleet_mind.db)
# -----------------------------------------------------------------------------
col_left, col_right = st.columns([1, 1], gap="medium")

# =============================================================================
# LEFT PANEL: Driver Safety Node
# =============================================================================
with col_left:
    st.markdown("""
    <div class="ag-card">
        <div class="ag-card-header">
            <div class="ag-card-title">&#128737; DRIVER SAFETY NODE // BIOMETRIC MESH</div>
            <div class="ag-pill ag-pill-online"><span class="pulse-dot"></span> SENSOR ACTIVE</div>
        </div>
    """, unsafe_allow_html=True)

    # Dynamic camera & sensor placeholders
    video_ph = st.empty()
    alert_banner_ph = st.empty()

    # Controls Bar inside card
    c_btn1, c_btn2, c_mode = st.columns([1.2, 1.2, 2.0])
    with c_btn1:
        if not st.session_state.stream_active:
            if st.button("▶ ENGAGE SENSORS", use_container_width=True, key="btn_engage_cam"):
                st.session_state.stream_active = True
                st.rerun()
        else:
            if st.button("⏸ DISENGAGE", use_container_width=True, key="btn_disengage_cam"):
                st.session_state.stream_active = False
                st.rerun()

    with c_btn2:
        if st.button("RESET BIOMETRICS", use_container_width=True, key="btn_reset_bio"):
            st.session_state.vision_module.reset()
            st.session_state.risk_engine.reset_intervention()
            st.rerun()

    with c_mode:
        selected_source = st.selectbox(
            "Camera Channel",
            ["Webcam (Live OpenCV)", "Synthetic Sensor Simulator"],
            index=0 if st.session_state.video_source_mode == "Webcam (Live OpenCV)" else 1,
            key="sel_source_mode",
            label_visibility="collapsed"
        )
        st.session_state.video_source_mode = selected_source

    if selected_source == "Synthetic Sensor Simulator":
        st.caption("Operator Biometric Simulation Mode:")
        sim_choice = st.selectbox(
            "Biometric Scenario State",
            ["Nominal (Alert)", "Microsleep (> 2.0s closed)", "Repeated Yawning", "Drowsy (Drooping eyes)"],
            index=0,
            key="sel_sim_state"
        )
        map_sim = {
            "Nominal (Alert)": "nominal",
            "Microsleep (> 2.0s closed)": "microsleep",
            "Repeated Yawning": "yawn",
            "Drowsy (Drooping eyes)": "drowsy"
        }
        st.session_state.synthetic_driver_state = map_sim[sim_choice]

    # Live Biometric Metrics Below Camera (EAR and MAR)
    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    ear_ph = b_col1.empty()
    mar_ph = b_col2.empty()
    eyes_closed_ph = b_col3.empty()
    yawns_ph = b_col4.empty()

    st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# RIGHT PANEL: Fleet Telematics & GPS Tracking
# =============================================================================
with col_right:
    st.markdown("""
    <div class="ag-card">
        <div class="ag-card-header">
            <div class="ag-card-title">&#128752; FLEET TELEMATICS & GPS TRACKING</div>
            <div class="ag-pill ag-pill-db"><span class="pulse-dot-cyan"></span> SQLITE STREAM</div>
        </div>
    """, unsafe_allow_html=True)

    # 1. Vehicle GPS Location on st.map()
    current_lat = db_telemetry.get("latitude", 11.2335)
    current_lon = db_telemetry.get("longitude", 78.8817)

    gps_df = pd.DataFrame([{
        "lat": current_lat,
        "lon": current_lon
    }])
    st.map(gps_df, zoom=10, use_container_width=True)

    # 2. Large Digital Speedometer Reading from Local fleet_mind.db
    spd_val = db_telemetry.get("speed_kmh", 0.0)
    accel_val = db_telemetry.get("acceleration_kmh_s", 0.0)
    heading_val = db_telemetry.get("heading_deg", 38.0)

    st.markdown(f"""
    <div class="ag-speedometer-box">
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 2px;">
            VEHICLE SPEED // DIGITAL TELEMETRY
        </div>
        <div class="ag-speed-number">{spd_val:.0f}</div>
        <div class="ag-speed-unit">KM / H</div>
        <div class="ag-speed-source">
            SOURCE: <strong style="color: var(--neon-cyan);">fleet_mind.db</strong> &bull; ACCEL: <strong style="color: {'#ff0055' if accel_val < -5 else '#00ff88'};">{accel_val:+.1f} km/h/s</strong> &bull; HEADING: <strong>{heading_val:.0f}&deg; NNE</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Telematics Quick Channels
    t_col1, t_col2, t_col3 = st.columns(3)
    with t_col1:
        st.markdown(f"""
        <div class="ag-metric-tile" style="margin-top: 12px;">
            <div class="ag-metric-val" style="font-size: 18px;">{current_lat:.4f}&deg; N</div>
            <div class="ag-metric-lbl">GPS LATITUDE</div>
        </div>
        """, unsafe_allow_html=True)
    with t_col2:
        st.markdown(f"""
        <div class="ag-metric-tile" style="margin-top: 12px;">
            <div class="ag-metric-val" style="font-size: 18px;">{current_lon:.4f}&deg; E</div>
            <div class="ag-metric-lbl">GPS LONGITUDE</div>
        </div>
        """, unsafe_allow_html=True)
    with t_col3:
        st.markdown(f"""
        <div class="ag-metric-tile" style="margin-top: 12px;">
            <div class="ag-metric-val" style="font-size: 18px; color: #00ff88;">NH 45</div>
            <div class="ag-metric-lbl">ACTIVE CORRIDOR</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Video Streaming & Continuous Processing Execution Loop
# -----------------------------------------------------------------------------
cap = None
if st.session_state.stream_active and st.session_state.video_source_mode == "Webcam (Live OpenCV)":
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        st.warning("⚠️ Hardware camera busy or inaccessible. Automatically engaging Synthetic Sensor Simulator.")
        st.session_state.video_source_mode = "Synthetic Sensor Simulator"
        cap = None

try:
    if st.session_state.stream_active:
        while st.session_state.stream_active:
            # 1. Step Telematics
            t_data = st.session_state.telematics_module.step()

            # 2. Process Vision (Webcam or Synthetic)
            if cap and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    frame = np.zeros((480, 640, 3), dtype=np.uint8)
                v_data = st.session_state.vision_module.process_frame(frame)
            else:
                v_data = st.session_state.vision_module.generate_synthetic_frame(
                    driver_mode=st.session_state.synthetic_driver_state,
                    width=640,
                    height=480
                )

            # 3. Dynamic Risk Engine Fusion
            r_data = st.session_state.risk_engine.compute_risk(v_data, t_data)

            # 4. Sync to SQLite (fleet_mind.db & fleet_telematics.db) and fleet_live_state.json
            st.session_state.fleet_sync_mgr.sync_telematics_frame(t_data, v_data, r_data)

            # 4b. Sync to FastAPI Backend Layer (JSON Database via REST API)
            send_telemetry_to_fastapi(t_data, v_data, r_data)

            # 5. Render Video Frame
            annotated_bgr = v_data["annotated_frame"]
            annotated_rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
            video_ph.image(annotated_rgb, channels="RGB", use_container_width=True)

            # 6. Render EAR & MAR Metrics
            ear_val = v_data["ear"]
            ear_color = "var(--neon-emerald)" if ear_val >= 0.22 else "var(--neon-red)"
            ear_ph.markdown(f"""
            <div class="ag-metric-tile">
                <div class="ag-metric-val" style="color: {ear_color};">{ear_val:.2f}</div>
                <div class="ag-metric-lbl">EYE ASPECT (EAR)</div>
            </div>
            """, unsafe_allow_html=True)

            mar_val = v_data["mar"]
            mar_color = "var(--neon-red)" if mar_val >= 0.60 else "var(--neon-cyan)"
            mar_ph.markdown(f"""
            <div class="ag-metric-tile">
                <div class="ag-metric-val" style="color: {mar_color};">{mar_val:.2f}</div>
                <div class="ag-metric-lbl">MOUTH ASPECT (MAR)</div>
            </div>
            """, unsafe_allow_html=True)

            eye_closed_s = v_data["eye_closed_duration"]
            dur_color = "var(--neon-red)" if eye_closed_s >= 2.0 else ("var(--neon-amber)" if eye_closed_s > 0.5 else "var(--neon-cyan)")
            eyes_closed_ph.markdown(f"""
            <div class="ag-metric-tile">
                <div class="ag-metric-val" style="color: {dur_color};">{eye_closed_s:.1f}s</div>
                <div class="ag-metric-lbl">EYES CLOSED</div>
            </div>
            """, unsafe_allow_html=True)

            total_yawns = v_data["total_yawns"]
            yawns_ph.markdown(f"""
            <div class="ag-metric-tile">
                <div class="ag-metric-val" style="color: var(--neon-cyan);">{total_yawns}</div>
                <div class="ag-metric-lbl">TOTAL YAWNS</div>
            </div>
            """, unsafe_allow_html=True)

            # 6b. Poll for Dispatcher Directives from Fleet Manager (Laptop 2)
            if not hasattr(st.session_state, "_last_cmd_poll_time"):
                st.session_state._last_cmd_poll_time = 0.0
            now_time = time.time()
            if (now_time - st.session_state._last_cmd_poll_time) > 1.5:
                st.session_state._last_cmd_poll_time = now_time
                poll_dispatcher_commands()

            # 6c. Active In-Cabin Spoken Voice Warnings via Laptop Speakers
            if v_data.get("microsleep_detected") or v_data.get("eye_closed_duration", 0.0) >= 2.0:
                speak_aloud("Emergency alert! Driver eyes closed! Wake up and pull over safely!", category="microsleep", cooldown_sec=3.0, priority=True)
            elif v_data.get("is_yawning") or v_data.get("recent_yawns_count", 0) >= 3:
                speak_aloud("Warning. Driver fatigue and repeated yawning detected. Please take a rest break.", category="yawn", cooldown_sec=6.0)
            elif r_data.get("is_critical") and t_data.get("speed_kmh", 0.0) > 0.0:
                speak_aloud("Warning: Critical driver fatigue hazard while vehicle in motion! Decelerate now!", category="critical_motion", cooldown_sec=4.0)

            # 7. Check for Target Lock Trigger
            if r_data["is_critical"]:
                st.session_state.target_lock_engaged = True
                if not st.session_state.get("_last_escalation_state", False):
                    st.session_state._last_escalation_state = True
                    st.rerun()
            else:
                if st.session_state.get("_last_escalation_state", False):
                    st.session_state._last_escalation_state = False
                    st.session_state.target_lock_engaged = False
                    st.rerun()

            time.sleep(0.06)

    else:
        # Static Idle Display when streaming is off
        dummy_frame = st.session_state.vision_module.generate_synthetic_frame(driver_mode="nominal")
        annotated_bgr = dummy_frame["annotated_frame"]
        annotated_rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
        video_ph.image(annotated_rgb, channels="RGB", use_container_width=True)

        ear_ph.markdown(f"""
        <div class="ag-metric-tile">
            <div class="ag-metric-val" style="color: var(--neon-emerald);">{dummy_frame['ear']:.2f}</div>
            <div class="ag-metric-lbl">EYE ASPECT (EAR)</div>
        </div>
        """, unsafe_allow_html=True)

        mar_ph.markdown(f"""
        <div class="ag-metric-tile">
            <div class="ag-metric-val" style="color: var(--neon-cyan);">{dummy_frame['mar']:.2f}</div>
            <div class="ag-metric-lbl">MOUTH ASPECT (MAR)</div>
        </div>
        """, unsafe_allow_html=True)

        eyes_closed_ph.markdown("""
        <div class="ag-metric-tile">
            <div class="ag-metric-val" style="color: var(--neon-cyan);">0.0s</div>
            <div class="ag-metric-lbl">EYES CLOSED</div>
        </div>
        """, unsafe_allow_html=True)

        yawns_ph.markdown("""
        <div class="ag-metric-tile">
            <div class="ag-metric-val" style="color: var(--neon-cyan);">0</div>
            <div class="ag-metric-lbl">TOTAL YAWNS</div>
        </div>
        """, unsafe_allow_html=True)

finally:
    if cap:
        cap.release()


# -----------------------------------------------------------------------------
# Bottom Audit Log
# -----------------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div class="ag-card" style="padding: 16px 20px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
        <span style="font-family: 'Orbitron'; font-size: 13px; color: var(--neon-cyan);">
            &#128203; REAL-TIME INCIDENT & SAFETY DECISION LOG
        </span>
        <span class="ag-pill ag-pill-db" style="font-size: 10px;">SQLITE AUDIT STREAM</span>
    </div>
""", unsafe_allow_html=True)

if st.session_state.incident_logs:
    for entry in reversed(st.session_state.incident_logs[-6:]):
        entry_color = "#ff0055" if "CRITICAL" in entry or "ESCALATION" in entry else ("#ffaa00" if "WARNING" in entry else "#00ff88")
        st.markdown(f"""
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 12px; padding: 6px 12px; margin-bottom: 6px; background: rgba(13, 17, 23, 0.7); border: 1px solid rgba(48, 54, 61, 0.7); border-left: 3px solid {entry_color}; border-radius: 6px; color: var(--text-primary);">
            {entry}
        </div>
        """, unsafe_allow_html=True)
else:
    st.caption("No critical safety interventions logged yet. Telematics and biometrics within nominal thresholds.")

st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# SQLite Database Live Inspector (fleet_mind.db)
# -----------------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("💾 SQLITE TELEMATICS LIVE DATABASE INSPECTOR // fleet_mind.db", expanded=True):
    stats = db_status
    i_col1, i_col2, i_col3, i_col4 = st.columns(4)
    with i_col1:
        st.markdown(f"""
        <div class="ag-metric-tile">
            <div class="ag-metric-val" style="color: var(--neon-cyan);">{stats.get('total_records', 0):,}</div>
            <div class="ag-metric-lbl">TOTAL TELEMETRY ROWS</div>
        </div>
        """, unsafe_allow_html=True)
    with i_col2:
        st.markdown(f"""
        <div class="ag-metric-tile">
            <div class="ag-metric-val" style="color: #00ff88;">{stats.get('stream_records', 0):,}</div>
            <div class="ag-metric-lbl">STREAM LOG ROWS</div>
        </div>
        """, unsafe_allow_html=True)
    with i_col3:
        st.markdown(f"""
        <div class="ag-metric-tile">
            <div class="ag-metric-val" style="color: #00f2fe;">{stats.get('db_size_kb', 0):.1f} KB</div>
            <div class="ag-metric-lbl">DATABASE FILE SIZE</div>
        </div>
        """, unsafe_allow_html=True)
    with i_col4:
        st.markdown(f"""
        <div class="ag-metric-tile">
            <div class="ag-metric-val" style="color: {'#00ff88' if db_connected else '#ff0055'};">
                {'SYNCHRONIZED' if db_connected else 'OFFLINE'}
            </div>
            <div class="ag-metric-lbl">SQLITE ENGINE STATE</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:12px; margin-bottom:6px; font-family: JetBrains Mono, monospace; font-size:12px; color: var(--text-secondary);'>ACTIVE REAL-TIME SQL QUERY: <code style='color:var(--neon-cyan); background:rgba(0,242,254,0.1); padding:2px 8px; border-radius:4px;'>SELECT id, timestamp, vehicle_id, speed_kmh, acceleration_kmh_s, latitude, longitude, ear, mar, fatigue_score, status FROM telematics ORDER BY id DESC LIMIT 6</code></div>", unsafe_allow_html=True)
    try:
        if os.path.exists("fleet_mind.db"):
            with sqlite3.connect("fleet_mind.db") as conn_insp:
                query_df = pd.read_sql_query("""
                SELECT id, timestamp, vehicle_id, speed_kmh, acceleration_kmh_s, latitude, longitude, ear, mar, fatigue_score, status
                FROM telematics ORDER BY id DESC LIMIT 6
                """, conn_insp)
                st.dataframe(query_df, hide_index=True, use_container_width=True)
    except Exception as e_insp:
        st.caption(f"Inspection query standby: {e_insp}")
