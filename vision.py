"""
Face Analysis Module (Edge Vision)
Tracks 468 facial landmarks via MediaPipe Face Mesh & OpenCV.
Computes:
1. Eye Aspect Ratio (EAR) -> Detects microsleeps (eyes closed > 2.0s).
2. Mouth Aspect Ratio (MAR) -> Detects sustained and repeated yawning.
3. Fleet HUD Annotations -> Neon overlays, biometric telemetry.
4. High-fidelity Synthetic Vision Simulator -> For automated testing and camera-free validation.
"""

import time
import math
import numpy as np
import cv2

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = hasattr(mp, "solutions") and hasattr(mp.solutions, "face_mesh")
except ImportError:
    MEDIAPIPE_AVAILABLE = False


class FaceAnalysisModule:
    """
    Edge Vision Face Analysis Module using MediaPipe Face Mesh (468 landmarks).
    """

    # 468 Face Mesh Canonical Indices
    # Right Eye Landmarks [P1, P2, P3, P4, P5, P6]
    RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
    # Left Eye Landmarks [P1, P2, P3, P4, P5, P6]
    LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
    # Mouth Landmarks: Corner Left (61), Corner Right (291), Upper/Lower Lips
    MOUTH_OUTER_INDICES = [61, 291, 13, 14, 82, 87, 312, 317]

    def __init__(
        self,
        ear_threshold: float = 0.22,
        microsleep_duration_sec: float = 2.0,
        mar_threshold: float = 0.60,
        yawn_min_duration_sec: float = 1.0
    ):
        self.ear_threshold = ear_threshold
        self.microsleep_duration_sec = microsleep_duration_sec
        self.mar_threshold = mar_threshold
        self.yawn_min_duration_sec = yawn_min_duration_sec

        # State tracking
        self.eye_closed_start_time = None
        self.eye_closed_duration = 0.0
        self.microsleep_flag = False

        self.yawn_start_time = None
        self.is_currently_yawning = False
        self.total_yawns_count = 0
        self.recent_yawn_timestamps = []

        # MediaPipe initialization
        self.face_mesh = None
        if MEDIAPIPE_AVAILABLE:
            try:
                self.mp_face_mesh = mp.solutions.face_mesh
                self.face_mesh = self.mp_face_mesh.FaceMesh(
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
            except Exception:
                self.face_mesh = None

    def reset(self):
        """Resets all transient biometric anomaly flags and counters for a fresh trial."""
        self.eye_closed_start_time = None
        self.eye_closed_duration = 0.0
        self.microsleep_flag = False
        self.yawn_start_time = None
        self.is_currently_yawning = False
        self.total_yawns_count = 0
        self.recent_yawn_timestamps = []

    @staticmethod
    def _euclidean_dist(p1, p2) -> float:
        """Calculates 2D Euclidean distance between two points."""
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def calculate_ear(self, landmarks, eye_indices, img_w: int, img_h: int) -> float:
        """
        Eye Aspect Ratio:
        EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)
        """
        pts = [(landmarks[idx].x * img_w, landmarks[idx].y * img_h) for idx in eye_indices]
        v1 = self._euclidean_dist(pts[1], pts[5])
        v2 = self._euclidean_dist(pts[2], pts[4])
        h = self._euclidean_dist(pts[0], pts[3])
        if h == 0:
            return 0.0
        return (v1 + v2) / (2.0 * h)

    def calculate_mar(self, landmarks, img_w: int, img_h: int) -> float:
        """
        Mouth Aspect Ratio:
        MAR = (||p13 - p14|| + ||p82 - p87|| + ||p312 - p317||) / (3 * ||p61 - p291||)
        """
        def pt(idx):
            return (landmarks[idx].x * img_w, landmarks[idx].y * img_h)

        h_dist = self._euclidean_dist(pt(61), pt(291))
        if h_dist == 0:
            return 0.0

        v1 = self._euclidean_dist(pt(13), pt(14))
        v2 = self._euclidean_dist(pt(82), pt(87))
        v3 = self._euclidean_dist(pt(312), pt(317))

        return (v1 + v2 + v3) / (3.0 * h_dist)

    def process_frame(self, frame: np.ndarray) -> dict:
        """
        Processes an image frame (BGR), runs face mesh, updates metrics,
        and paints the HUD directly on the frame.
        """
        h, w, _ = frame.shape
        now = time.time()
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        ear = 0.32
        mar = 0.25
        face_detected = False

        if self.face_mesh:
            results = self.face_mesh.process(rgb_frame)
            if results.multi_face_landmarks:
                face_detected = True
                mesh = results.multi_face_landmarks[0].landmark

                right_ear = self.calculate_ear(mesh, self.RIGHT_EYE_INDICES, w, h)
                left_ear = self.calculate_ear(mesh, self.LEFT_EYE_INDICES, w, h)
                ear = (right_ear + left_ear) / 2.0
                mar = self.calculate_mar(mesh, w, h)

                self._draw_neon_hud_overlays(frame, mesh, w, h, ear, mar)

        # Microsleep detection logic (eyes closed > 2.0s)
        if ear < self.ear_threshold:
            if self.eye_closed_start_time is None:
                self.eye_closed_start_time = now
            self.eye_closed_duration = now - self.eye_closed_start_time
            if self.eye_closed_duration >= self.microsleep_duration_sec:
                self.microsleep_flag = True
        else:
            self.eye_closed_start_time = None
            self.eye_closed_duration = 0.0
            self.microsleep_flag = False

        # Yawn detection logic (repeated yawning tracking)
        if mar > self.mar_threshold:
            if self.yawn_start_time is None:
                self.yawn_start_time = now
            yawn_dur = now - self.yawn_start_time
            if yawn_dur >= self.yawn_min_duration_sec and not self.is_currently_yawning:
                self.is_currently_yawning = True
                self.total_yawns_count += 1
                self.recent_yawn_timestamps.append(now)
        else:
            self.yawn_start_time = None
            self.is_currently_yawning = False

        self.recent_yawn_timestamps = [t for t in self.recent_yawn_timestamps if now - t < 300]
        recent_yawns_count = len(self.recent_yawn_timestamps)

        annotated_frame = self._render_cockpit_hud(
            frame, ear, mar, self.eye_closed_duration,
            self.microsleep_flag, self.is_currently_yawning,
            recent_yawns_count, face_detected
        )

        return {
            "annotated_frame": annotated_frame,
            "ear": float(ear),
            "mar": float(mar),
            "eye_closed_duration": float(self.eye_closed_duration),
            "microsleep_detected": bool(self.microsleep_flag),
            "is_yawning": bool(self.is_currently_yawning),
            "recent_yawns_count": int(recent_yawns_count),
            "total_yawns": int(self.total_yawns_count),
            "face_detected": bool(face_detected)
        }

    def _draw_neon_hud_overlays(self, frame, mesh, w, h, ear, mar):
        """Draws cyber mesh points around eyes and lips."""
        eye_color = (255, 240, 0) if ear >= self.ear_threshold else (85, 0, 255)
        mouth_color = (255, 0, 189) if mar < self.mar_threshold else (85, 0, 255)

        for idx in self.LEFT_EYE_INDICES + self.RIGHT_EYE_INDICES:
            pt = (int(mesh[idx].x * w), int(mesh[idx].y * h))
            cv2.circle(frame, pt, 2, eye_color, -1)

        for idx in self.MOUTH_OUTER_INDICES:
            pt = (int(mesh[idx].x * w), int(mesh[idx].y * h))
            cv2.circle(frame, pt, 2, mouth_color, -1)

    def _render_cockpit_hud(
        self, frame, ear, mar, eye_dur, microsleep, yawning, recent_yawns, face_detected
    ) -> np.ndarray:
        """Renders cockpit diagnostics directly onto the video frame."""
        h, w, _ = frame.shape
        overlay = frame.copy()

        # Top diagnostic bar
        cv2.rectangle(overlay, (15, 15), (w - 15, 80), (12, 18, 32), -1)
        cv2.rectangle(overlay, (15, 15), (w - 15, 80), (255, 240, 0), 1)

        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        font = cv2.FONT_HERSHEY_SIMPLEX
        status_color = (85, 0, 255) if microsleep else ((0, 255, 136) if face_detected else (0, 183, 255))
        state_str = "MICROSLEEP DETECTED!" if microsleep else ("FACE LOCKED" if face_detected else "SEARCHING FOR DRIVER")
        
        cv2.putText(frame, "SENTINEL DMS v2.4", (28, 42), font, 0.55, (255, 240, 0), 1, cv2.LINE_AA)
        cv2.putText(frame, f"STATUS: {state_str}", (28, 68), font, 0.6, status_color, 2, cv2.LINE_AA)

        # Telemetry metrics on right of top bar
        ear_text = f"EAR: {ear:.2f}"
        mar_text = f"MAR: {mar:.2f}"
        cv2.putText(frame, ear_text, (w - 260, 42), font, 0.55, (255, 240, 0), 1, cv2.LINE_AA)
        cv2.putText(frame, mar_text, (w - 260, 68), font, 0.55, (255, 0, 189), 1, cv2.LINE_AA)

        if eye_dur > 0.3:
            warn_color = (85, 0, 255) if eye_dur >= 2.0 else (0, 183, 255)
            alert_bar_text = f"EYES CLOSED: {eye_dur:.1f}s / 2.0s"
            cv2.putText(frame, alert_bar_text, (w - 140, 42), font, 0.5, warn_color, 2, cv2.LINE_AA)

        if yawning:
            cv2.putText(frame, "YAWN DETECTED", (w - 140, 68), font, 0.5, (85, 0, 255), 2, cv2.LINE_AA)

        if microsleep:
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), (85, 0, 255), 8)
            cv2.putText(
                frame, "!! CRITICAL FATIGUE ALERT !!",
                (w // 2 - 180, h // 2), font, 0.8, (85, 0, 255), 2, cv2.LINE_AA
            )

        return frame

    def generate_synthetic_frame(
        self,
        driver_mode: str = "nominal",
        width: int = 640,
        height: int = 480
    ) -> dict:
        """
        Generates a synthetic camera frame for automated test harnesses or systems without webcams.
        """
        # Clean diagnostic sensor backdrop (light slate theme)
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        for y in range(height):
            ratio = y / height
            b = int(242 - ratio * 12)
            g = int(236 - ratio * 16)
            r = int(230 - ratio * 20)
            frame[y, :] = (b, g, r)

        # Crisp grid lines for high-tech HUD feel
        for gx in range(0, width, 60):
            cv2.line(frame, (gx, 0), (gx, height), (210, 218, 226), 1)
        for gy in range(0, height, 60):
            cv2.line(frame, (0, gy), (width, gy), (210, 218, 226), 1)

        cx, cy = width // 2, height // 2 + 20
        # Driver avatar silhouette (executive slate blue)
        cv2.ellipse(frame, (cx, cy + 180), (140, 100), 0, 0, 180, (148, 163, 184), -1)
        cv2.ellipse(frame, (cx, cy), (75, 100), 0, 0, 360, (100, 116, 139), -1)

        now = time.time()
        if driver_mode == "microsleep":
            ear = 0.12
            mar = 0.22
            cv2.line(frame, (cx - 40, cy - 15), (cx - 15, cy - 15), (38, 38, 220), 3)
            cv2.line(frame, (cx + 15, cy - 15), (cx + 40, cy - 15), (38, 38, 220), 3)
            cv2.line(frame, (cx - 25, cy + 45), (cx + 25, cy + 45), (189, 0, 255), 2)
        elif driver_mode == "yawn":
            ear = 0.26
            mar = 0.72
            cv2.circle(frame, (cx - 28, cy - 15), 9, (199, 132, 2), 2)
            cv2.circle(frame, (cx + 28, cy - 15), 9, (199, 132, 2), 2)
            cv2.ellipse(frame, (cx, cy + 50), (22, 35), 0, 0, 360, (38, 38, 220), -1)
        elif driver_mode == "drowsy":
            ear = 0.19
            mar = 0.40
            cv2.ellipse(frame, (cx - 28, cy - 15), (12, 4), 0, 0, 360, (6, 119, 217), -1)
            cv2.ellipse(frame, (cx + 28, cy - 15), (12, 4), 0, 0, 360, (6, 119, 217), -1)
            cv2.line(frame, (cx - 20, cy + 45), (cx + 20, cy + 45), (189, 0, 255), 2)
        else:
            ear = 0.32
            mar = 0.22
            cv2.circle(frame, (cx - 28, cy - 15), 8, (105, 150, 5), 2)
            cv2.circle(frame, (cx + 28, cy - 15), 8, (105, 150, 5), 2)
            cv2.circle(frame, (cx - 28, cy - 15), 3, (199, 132, 2), -1)
            cv2.circle(frame, (cx + 28, cy - 15), 3, (199, 132, 2), -1)
            cv2.ellipse(frame, (cx, cy + 45), (20, 10), 0, 0, 180, (105, 150, 5), 2)

        if ear < self.ear_threshold:
            if self.eye_closed_start_time is None:
                self.eye_closed_start_time = now
            self.eye_closed_duration = now - self.eye_closed_start_time
            if self.eye_closed_duration >= self.microsleep_duration_sec:
                self.microsleep_flag = True
        else:
            self.eye_closed_start_time = None
            self.eye_closed_duration = 0.0
            self.microsleep_flag = False

        if mar > self.mar_threshold:
            if self.yawn_start_time is None:
                self.yawn_start_time = now
            if (now - self.yawn_start_time >= self.yawn_min_duration_sec) and not self.is_currently_yawning:
                self.is_currently_yawning = True
                self.total_yawns_count += 1
                self.recent_yawn_timestamps.append(now)
        else:
            self.yawn_start_time = None
            self.is_currently_yawning = False

        self.recent_yawn_timestamps = [t for t in self.recent_yawn_timestamps if now - t < 300]
        recent_yawns_count = len(self.recent_yawn_timestamps)

        annotated_frame = self._render_cockpit_hud(
            frame, ear, mar, self.eye_closed_duration,
            self.microsleep_flag, self.is_currently_yawning,
            recent_yawns_count, True
        )

        return {
            "annotated_frame": annotated_frame,
            "ear": float(ear),
            "mar": float(mar),
            "eye_closed_duration": float(self.eye_closed_duration),
            "microsleep_detected": bool(self.microsleep_flag),
            "is_yawning": bool(self.is_currently_yawning),
            "recent_yawns_count": int(recent_yawns_count),
            "total_yawns": int(self.total_yawns_count),
            "face_detected": True
        }
