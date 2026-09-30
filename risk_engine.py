"""
Dynamic Telematics Risk Engine & Active Intervention State Machine
Features:
1. Dynamic Sensor Fusion (EAR, MAR, Speed, Deceleration) -> Risk Score (0-100%).
2. In-Cabin Intervention Alert Trigger (Critical Threshold >= 70%).
3. Speedometer Verification Loop -> Verifies Safe Stop only when speed == 0 km/h.
4. Auto-Escalation Engine -> Escalates to Fleet Command if driver ignores alert (speed > 0 km/h).
"""

import time


class RiskLevel:
    NOMINAL = "NOMINAL"
    ELEVATED = "ELEVATED"
    CRITICAL = "CRITICAL"


class InterventionStatus:
    MONITORING = "MONITORING"
    CRITICAL_ALERT = "CRITICAL_ALERT_ACTIVE"
    AWAITING_SAFE_STOP = "AWAITING_SAFE_STOP"
    SAFE_STOP_VERIFIED = "SAFE_STOP_VERIFIED"
    ESCALATED = "ESCALATED_TO_FLEET"


class DynamicRiskEngine:
    """
    Fuses edge vision biometric cues and vehicle telematics into a real-time risk score,
    managing cockpit interventions and fleet escalation verification.
    """

    CRITICAL_THRESHOLD = 70.0
    ESCALATION_TIMEOUT_SEC = 10.0  # Seconds before auto-escalating if speed > 0

    def __init__(self):
        self.risk_score = 0.0
        self.risk_level = RiskLevel.NOMINAL
        self.intervention_status = InterventionStatus.MONITORING

        # Timing and state
        self.alert_triggered_time = None
        self.safe_stop_verified_time = None
        self.escalation_time = None
        self.is_escalated = False
        self.driver_action_summary = "Normal operation"

    def compute_risk(self, vision_data: dict, telematics_data: dict) -> dict:
        """
        Fuses biometric and telematics features into a dynamic risk score [0 - 100].
        """
        ear = vision_data.get("ear", 0.30)
        eye_closed_dur = vision_data.get("eye_closed_duration", 0.0)
        microsleep = vision_data.get("microsleep_detected", False)
        is_yawning = vision_data.get("is_yawning", False)
        recent_yawns = vision_data.get("recent_yawns_count", 0)

        speed = telematics_data.get("speed_kmh", 0.0)
        accel = telematics_data.get("acceleration_kmh_s", 0.0)
        is_overspeeding = telematics_data.get("is_overspeeding", False)
        is_hard_braking = telematics_data.get("is_hard_braking", False)

        # 1. Eye Closure / Microsleep Score (Max 65)
        eye_score = 0.0
        if microsleep:
            eye_score = 65.0
        elif eye_closed_dur > 0.0:
            eye_score = min(55.0, (eye_closed_dur / 2.0) * 55.0)
        elif ear < 0.22:
            eye_score = 25.0

        # 2. Yawn / Fatigue Score (Max 30)
        yawn_score = 0.0
        if is_yawning:
            yawn_score += 15.0
        yawn_score += min(15.0, recent_yawns * 5.0)

        # 3. Speed Risk Factor (Max 20)
        speed_score = 0.0
        if is_overspeeding:
            speed_score = 18.0 + min(2.0, (speed - 80.0) * 0.2)
        elif speed > 60.0:
            speed_score = ((speed - 60.0) / 20.0) * 10.0

        # High-Speed Multiplier when fatigued (> 50 km/h)
        if (microsleep or eye_closed_dur > 1.0) and speed > 50.0:
            eye_score = min(75.0, eye_score * 1.20)

        # 4. Deceleration / Instability Factor (Max 15)
        brake_score = 0.0
        if is_hard_braking:
            brake_score = 15.0
        elif accel < -8.0:
            brake_score = 8.0

        total_score = min(100.0, round(eye_score + yawn_score + speed_score + brake_score, 1))
        self.risk_score = total_score

        # Categorize Risk Level
        if total_score >= self.CRITICAL_THRESHOLD:
            self.risk_level = RiskLevel.CRITICAL
        elif total_score >= 40.0:
            self.risk_level = RiskLevel.ELEVATED
        else:
            self.risk_level = RiskLevel.NOMINAL

        # Update Active Intervention & Verification Loop
        intervention_output = self._update_intervention_loop(
            total_score, speed, microsleep, is_overspeeding, is_hard_braking
        )

        return {
            "risk_score": float(total_score),
            "risk_level": self.risk_level,
            "intervention_status": self.intervention_status,
            "is_critical": (self.risk_level == RiskLevel.CRITICAL or self.alert_triggered_time is not None),
            "is_escalated": self.is_escalated,
            "driver_action": self.driver_action_summary,
            "seconds_in_alert": intervention_output.get("seconds_in_alert", 0.0),
            "breakdown": {
                "eye_fatigue_score": round(eye_score, 1),
                "yawn_fatigue_score": round(yawn_score, 1),
                "speed_risk_score": round(speed_score, 1),
                "braking_risk_score": round(brake_score, 1),
            }
        }

    def _update_intervention_loop(
        self,
        risk_score: float,
        speed: float,
        microsleep: bool,
        is_overspeeding: bool,
        is_hard_braking: bool
    ) -> dict:
        """
        State machine governing in-cabin alert triggers, safe-stop verification,
        and fleet auto-escalation.
        """
        now = time.time()
        seconds_in_alert = 0.0

        # Trigger intervention if risk reaches critical threshold
        if self.risk_level == RiskLevel.CRITICAL and self.alert_triggered_time is None:
            self.alert_triggered_time = now
            self.intervention_status = InterventionStatus.CRITICAL_ALERT
            self.driver_action_summary = "CRITICAL ALERT: Driver instructed to pull over immediately"

        # If an alert is active or awaiting safe stop
        if self.alert_triggered_time is not None:
            seconds_in_alert = now - self.alert_triggered_time

            # Auto-recovery: If biometric telemetry returns to nominal and alert has passed
            if self.risk_level == RiskLevel.NOMINAL and not microsleep and not is_hard_braking:
                self.intervention_status = InterventionStatus.MONITORING
                self.alert_triggered_time = None
                self.safe_stop_verified_time = None
                self.is_escalated = False
                self.driver_action_summary = "Driver attention restored. Nominal monitoring active."
            # Verification condition: Safe Stop ONLY if speed drops to EXACTLY 0.0 km/h
            elif speed == 0.0:
                self.intervention_status = InterventionStatus.SAFE_STOP_VERIFIED
                self.safe_stop_verified_time = now
                self.alert_triggered_time = None
                self.is_escalated = False
                self.driver_action_summary = "SAFE STOP VERIFIED: Vehicle stopped at 0 km/h. Driver safe."
            else:
                # Vehicle still moving (speed > 0 km/h)
                if seconds_in_alert >= self.ESCALATION_TIMEOUT_SEC:
                    self.intervention_status = InterventionStatus.ESCALATED
                    self.is_escalated = True
                    self.escalation_time = now
                    self.driver_action_summary = (
                        f"ALERT IGNORED: Speed is {speed:.1f} km/h after {seconds_in_alert:.0f}s. "
                        "FLEET DISPATCH AUTO-ESCALATED!"
                    )
                else:
                    self.intervention_status = InterventionStatus.AWAITING_SAFE_STOP
                    remaining = max(0.0, self.ESCALATION_TIMEOUT_SEC - seconds_in_alert)
                    self.driver_action_summary = (
                        f"AWAITING SAFE STOP: Vehicle speed {speed:.1f} km/h. "
                        f"Escalation in {remaining:.1f}s unless speed = 0 km/h."
                    )
        elif self.intervention_status == InterventionStatus.SAFE_STOP_VERIFIED:
            if speed > 0.0:
                # Vehicle resumed transit after verified stop
                self.intervention_status = InterventionStatus.MONITORING
                self.driver_action_summary = "Vehicle resumed transit safely"
        else:
            self.intervention_status = InterventionStatus.MONITORING
            self.driver_action_summary = "Nominal telemetry monitoring"

        return {"seconds_in_alert": seconds_in_alert}

    def reset_intervention(self):
        """Manually resets the active intervention state."""
        self.alert_triggered_time = None
        self.safe_stop_verified_time = None
        self.escalation_time = None
        self.is_escalated = False
        self.intervention_status = InterventionStatus.MONITORING
        self.driver_action_summary = "Manual cockpit reset"
