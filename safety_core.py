"""
FleetGuard Sentinel: Safety Advisory & Supervisory System
Integrates:
- Neural Heuristic Safety Engine for instant in-cabin driver directives.
- Optional Cloud Telematics link for fleet dispatch synchronization.
- Context-aware intervention directives fusing biometrics (EAR, MAR) and telematics (Speed, Accel).
Zero AI marketing jargon - engineered as a commercial vehicle safety supervisor.
"""

import os
import time

try:
    from anthropic import Anthropic
    CLOUD_LINK_AVAILABLE = True
except ImportError:
    CLOUD_LINK_AVAILABLE = False


class SentinelSafetyCore:
    """
    Sentinel Autonomous Safety Supervisor for commercial fleet vehicles.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.client = None
        if CLOUD_LINK_AVAILABLE and self.api_key.startswith("sk-"):
            try:
                self.client = Anthropic(api_key=self.api_key)
            except Exception:
                self.client = None

    def update_api_key(self, api_key: str):
        """Updates Cloud API key at runtime."""
        self.api_key = api_key
        if CLOUD_LINK_AVAILABLE and self.api_key.startswith("sk-"):
            try:
                self.client = Anthropic(api_key=self.api_key)
            except Exception:
                self.client = None
        else:
            self.client = None

    def get_safety_directive(
        self,
        risk_score: float,
        issue: str,
        speed: float = 65.0,
        ear: float = 0.20,
        mar: float = 0.30
    ) -> dict:
        """
        Synthesizes an immediate in-cabin safety directive based on biometric and telematics data.
        """
        # 1. Cloud Dispatch Link (if enabled)
        if self.client:
            prompt = (
                f"You are the FleetGuard Sentinel Onboard Safety System for commercial vehicle unit FLEET-UNIT-9042. "
                f"Telematics and edge vision have detected a driver fatigue hazard:\n"
                f"- Risk Index: {risk_score:.1f}%\n"
                f"- Primary Anomaly: {issue}\n"
                f"- Vehicle Speed: {speed:.1f} km/h\n"
                f"- Biometrics: EAR={ear:.2f}, MAR={mar:.2f}\n"
                f"Provide a concise, authoritative, critical 1-sentence in-cabin directive instructing the driver on immediate actions."
            )
            try:
                message = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=90,
                    temperature=0.2,
                    messages=[{"role": "user", "content": prompt}]
                )
                text = message.content[0].text if isinstance(message.content, list) else str(message.content)
                return {
                    "text": text.strip(),
                    "source": "Sentinel Cloud Dispatch Link",
                    "timestamp": time.strftime("%H:%M:%S")
                }
            except Exception:
                pass

        # 2. Sentinel Onboard Heuristic Safety Engine
        if "Eye" in issue or "Microsleep" in issue:
            if speed > 80.0:
                text = (
                    f"CRITICAL SAFETY OVERRIDE: Eye closure detected at {speed:.0f} km/h! "
                    "Decelerate immediately and pull onto the shoulder to prevent collision."
                )
            else:
                text = (
                    "SAFETY INTERVENTION: Microsleep duration exceeded safe operational thresholds. "
                    "Activate hazard lights and bring the vehicle to an immediate safe stop."
                )
        elif "Yawn" in issue:
            text = (
                f"DRIVER ADVISORY: High-frequency yawning detected ({mar:.2f} MAR). "
                "Cognitive alertness impaired—exit at next designated commercial rest area."
            )
        elif "Braking" in issue or "Decel" in issue:
            text = (
                "TELEMATICS ALERT: Severe deceleration spike detected. "
                "Stabilize steering vector and verify distance to preceding vehicles."
            )
        elif risk_score >= 70.0:
            text = (
                f"FLEET INTERVENTION: Telematics Risk Critical ({risk_score:.0f}%). "
                "Initiate controlled pull-over protocol immediately before automated dispatch lock."
            )
        else:
            text = (
                f"SYSTEM STATUS: Biometrics nominal (EAR: {ear:.2f}, MAR: {mar:.2f}). "
                "Vehicle operating within safe commercial fleet parameters."
            )

        return {
            "text": text,
            "source": "Sentinel Onboard Safety Engine",
            "timestamp": time.strftime("%H:%M:%S")
        }
