"""
================================================================================
ANTI-GRAVITY // IN-CABIN AUDIO ALERT ENGINE (Physical Speakers + Web Audio)
================================================================================
Provides loud, clear aloud spoken voice alerts and emergency siren tones through:
1. Native Physical Laptop Speakers (pyttsx3 / Windows SAPI in background thread)
2. Browser Web Speech Synthesis & Web Audio API Oscillator (Streamlit component)

Includes intelligent cooldown deduplication so alerts sound authoritative
without stuttering or lagging during 30 FPS video processing.
================================================================================
"""

import time
import threading
import queue
import logging
import streamlit.components.v1 as components

logger = logging.getLogger("fleet_audio")

# Optional pyttsx3 native engine
try:
    import pyttsx3
    HAS_PYTTSX3 = True
except Exception:
    HAS_PYTTSX3 = False


class CabinSpeakerService:
    """Singleton background speech synthesis service for laptop physical speakers."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_service()
            return cls._instance

    def _init_service(self):
        self.speech_queue = queue.Queue(maxsize=10)
        self.last_alert_time = {}
        self.worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.worker_thread.start()

    def _speech_worker(self):
        """Dedicated background thread for speech synthesis to prevent blocking UI/Camera."""
        engine = None
        if HAS_PYTTSX3:
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', 165)  # Clear, urgent speech rate
                engine.setProperty('volume', 1.0) # Maximum volume
            except Exception as e:
                logger.warning(f"pyttsx3 init fallback: {e}")
                engine = None

        while True:
            try:
                text = self.speech_queue.get()
                if text is None:
                    break

                if engine:
                    try:
                        engine.say(text)
                        engine.runAndWait()
                    except Exception:
                        # Re-initialize engine if COM state corrupted
                        try:
                            engine = pyttsx3.init()
                            engine.say(text)
                            engine.runAndWait()
                        except Exception:
                            pass
                else:
                    # Windows PowerShell SAPI fallback
                    import subprocess
                    clean_text = text.replace("'", "").replace('"', "")
                    cmd = f"(New-Object -ComObject SAPI.SpVoice).Speak('{clean_text}')"
                    subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True)

                self.speech_queue.task_done()
            except Exception as e:
                logger.error(f"Speech worker error: {e}")
                time.sleep(0.1)

    def speak(self, text: str, alert_category: str = "generic", cooldown_sec: float = 3.5, priority: bool = False):
        """
        Speaks text aloud through laptop speakers with rate-limiting cooldown.
        If priority=True, clears queue and speaks immediately.
        """
        now = time.time()
        last_time = self.last_alert_time.get(alert_category, 0.0)

        if not priority and (now - last_time) < cooldown_sec:
            return False  # Cooldown active, don't spam

        self.last_alert_time[alert_category] = now

        if priority:
            # Clear pending items
            while not self.speech_queue.empty():
                try:
                    self.speech_queue.get_nowait()
                    self.speech_queue.task_done()
                except Exception:
                    break

        try:
            self.speech_queue.put_nowait(text)
            return True
        except queue.Full:
            return False

    def clear(self):
        """Clears all pending speech and resets timers."""
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except Exception:
                break
        self.last_alert_time.clear()


# Global Singleton Speaker instance
speaker = CabinSpeakerService()


def speak_aloud(text: str, category: str = "generic", cooldown_sec: float = 3.5, priority: bool = False) -> bool:
    """Convenience helper to speak aloud through the laptop's physical speakers."""
    return speaker.speak(text, alert_category=category, cooldown_sec=cooldown_sec, priority=priority)


def render_browser_voice_component(message: str, tone: bool = True, cancel_previous: bool = True):
    """
    Renders an active Streamlit component that speaks aloud via browser SpeechSynthesis
    and plays a siren oscillation via Web Audio API.
    """
    escaped_msg = message.replace('"', '\\"').replace("'", "\\'").replace("\n", " ")
    tone_js = """
        try {
            const AudioCtx = window.AudioContext || window.webkitAudioContext || (window.parent && (window.parent.AudioContext || window.parent.webkitAudioContext));
            if (AudioCtx) {
                const ctx = new AudioCtx();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sawtooth';
                const now = ctx.currentTime;
                osc.frequency.setValueAtTime(880, now);
                osc.frequency.exponentialRampToValueAtTime(587, now + 0.15);
                osc.frequency.exponentialRampToValueAtTime(880, now + 0.30);
                gain.gain.setValueAtTime(0.35, now);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.40);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start(now);
                osc.stop(now + 0.40);
            }
        } catch (e) {}
    """ if tone else ""

    cancel_js = """
        try {
            if (window.speechSynthesis) window.speechSynthesis.cancel();
            if (window.parent && window.parent.speechSynthesis) window.parent.speechSynthesis.cancel();
        } catch(e) {}
    """ if cancel_previous else ""

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin:0; padding:0; background:transparent;">
        <script>
        (function() {{
            {tone_js}
            const synth = window.speechSynthesis || (window.parent && window.parent.speechSynthesis);
            if (synth) {{
                {cancel_js}
                const Utterance = window.SpeechSynthesisUtterance || (window.parent && window.parent.SpeechSynthesisUtterance);
                if (Utterance) {{
                    const utterance = new Utterance("{escaped_msg}");
                    utterance.rate = 1.05;
                    utterance.pitch = 1.05;
                    utterance.volume = 1.0;
                    synth.speak(utterance);
                }}
            }}
        }})();
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=0, width=0)
