"""
FleetGuard Sentinel: Commercial Telematics & Driver Monitoring System
Cockpit Styling & Audio Alarm Module (Light Executive Theme)
Features:
- Crisp arctic platinum / frosted glassmorphism palette
- High-contrast typography (#0f172a) with vivid telemetry accents
- Cobalt Azure (#0284c7), Deep Violet (#7c3aed), Emerald (#059669), Crimson (#dc2626)
- In-dash light sidebar and clean touch tabs
- In-browser synthesized audio safety buzzer
"""

def get_cockpit_css() -> str:
    """Returns custom CSS for the FleetGuard Sentinel executive light theme."""
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800;900&family=Rajdhani:wght@500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

    :root {
        --bg-void: #f4f6fa;
        --bg-deep: #e8ecf4;
        --bg-panel: rgba(255, 255, 255, 0.88);
        --bg-panel-hover: rgba(255, 255, 255, 0.98);
        --neon-cyan: #0284c7;      /* Vivid Azure */
        --neon-violet: #7c3aed;    /* Deep Violet */
        --neon-emerald: #059669;   /* Crisp Emerald */
        --neon-amber: #d97706;     /* Alert Amber */
        --neon-crimson: #dc2626;   /* Alert Crimson */
        --text-bright: #0f172a;    /* Deep Slate Navy */
        --text-dim: #64748b;       /* Muted Slate */
        --glass-border: rgba(2, 132, 199, 0.22);
        --glass-border-alert: rgba(220, 38, 38, 0.65);
        --glass-shadow: 0 12px 35px rgba(15, 23, 42, 0.08);
    }

    /* Remove Streamlit web platform artifacts */
    #MainMenu {visibility: hidden !important; display: none !important;}
    footer {visibility: hidden !important; display: none !important;}
    header[data-testid="stHeader"] {background: transparent !important; height: 1.5rem !important;}
    .stDeployButton {display: none !important;}
    div[data-testid="stDecoration"] {display: none !important;}
    div[data-testid="stToolbar"] {visibility: hidden !important;}

    /* Core Vehicle Display Background - Light Executive Theme */
    .stApp {
        background-color: var(--bg-void);
        background-image: 
            radial-gradient(circle at 10% 10%, rgba(2, 132, 199, 0.06) 0%, transparent 40%),
            radial-gradient(circle at 90% 15%, rgba(124, 58, 237, 0.05) 0%, transparent 45%),
            radial-gradient(circle at 50% 90%, rgba(5, 150, 105, 0.04) 0%, transparent 50%),
            linear-gradient(180deg, #f8fafc 0%, #edf2f7 100%);
        background-attachment: fixed;
        color: var(--text-bright);
        font-family: 'Rajdhani', sans-serif;
    }

    /* Typography */
    h1, h2, h3, h4 {
        font-family: 'Orbitron', monospace !important;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        color: var(--text-bright) !important;
    }

    p, span, div, label {
        color: var(--text-bright);
    }

    /* =========================================================================
       IN-DASH SIDEBAR: Styled as a Clean Vehicle ECU Panel
       ========================================================================= */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%) !important;
        border-right: 1px solid rgba(2, 132, 199, 0.20) !important;
        box-shadow: 8px 0 30px rgba(15, 23, 42, 0.06) !important;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
    }

    button[data-testid="stSidebarCollapseButton"],
    button[data-testid="baseButton-headerNoPadding"] {
        color: var(--neon-cyan) !important;
        background: rgba(255, 255, 255, 0.9) !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 10px rgba(2, 132, 199, 0.15) !important;
    }

    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {
        color: var(--neon-cyan) !important;
        font-size: 14px !important;
        margin-bottom: 6px !important;
    }

    /* Sidebar Radio / Navigation Pill buttons */
    section[data-testid="stSidebar"] div[role="radiogroup"] {
        background: rgba(241, 245, 249, 0.8) !important;
        border: 1px solid rgba(2, 132, 199, 0.2) !important;
        border-radius: 12px !important;
        padding: 6px !important;
        gap: 6px !important;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        background: rgba(255, 255, 255, 0.7) !important;
        border: 1px solid transparent !important;
        border-radius: 8px !important;
        padding: 8px 12px !important;
        color: var(--text-dim) !important;
        font-family: 'Rajdhani', sans-serif !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        letter-spacing: 0.8px !important;
        transition: all 0.2s ease !important;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: rgba(2, 132, 199, 0.1) !important;
        color: var(--neon-cyan) !important;
        border-color: rgba(2, 132, 199, 0.3) !important;
    }

    /* Sidebar Selectbox & Inputs */
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 10px !important;
        color: var(--text-bright) !important;
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 14px !important;
    }

    section[data-testid="stSidebar"] input {
        background-color: #ffffff !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 10px !important;
        color: var(--text-bright) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
    }

    /* Slider track & thumb */
    div[data-testid="stSlider"] > div > div > div {
        background-color: var(--neon-cyan) !important;
    }

    /* =========================================================================
       TOP NAVIGATION TABS: Light Cockpit Touch Navigation
       ========================================================================= */
    div[data-testid="stTabs"] {
        margin-top: -10px;
        margin-bottom: 20px;
    }

    div[data-testid="stTabs"] button[role="tab"] {
        font-family: 'Orbitron', monospace !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        letter-spacing: 1.2px !important;
        color: var(--text-dim) !important;
        background: rgba(255, 255, 255, 0.6) !important;
        border: 1px solid rgba(2, 132, 199, 0.15) !important;
        border-radius: 10px 10px 0 0 !important;
        padding: 12px 24px !important;
        margin-right: 6px !important;
        transition: all 0.25s ease !important;
    }

    div[data-testid="stTabs"] button[role="tab"]:hover {
        color: var(--neon-cyan) !important;
        border-color: rgba(2, 132, 199, 0.4) !important;
        background: rgba(255, 255, 255, 0.9) !important;
    }

    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color: var(--neon-cyan) !important;
        background: #ffffff !important;
        border-color: var(--neon-cyan) !important;
        border-bottom-color: transparent !important;
        box-shadow: 0 -4px 18px rgba(2, 132, 199, 0.15) !important;
    }

    /* =========================================================================
       FROSTED GLASS LIGHT COCKPIT CARDS
       ========================================================================= */
    .fleet-glass-card {
        background: var(--bg-panel);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--glass-border);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 18px;
        box-shadow: var(--glass-shadow), inset 0 0 15px rgba(255, 255, 255, 0.8);
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        position: relative;
        overflow: hidden;
    }

    .fleet-glass-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, transparent, var(--neon-cyan), transparent);
    }

    .fleet-glass-card:hover {
        border-color: rgba(2, 132, 199, 0.5);
        box-shadow: 0 16px 45px rgba(2, 132, 199, 0.12), inset 0 0 20px rgba(255, 255, 255, 0.9);
        transform: translateY(-2px);
    }

    /* Top Telematics Bar */
    .fleet-navbar {
        background: rgba(255, 255, 255, 0.92);
        backdrop-filter: blur(20px);
        border-bottom: 2px solid var(--glass-border);
        border-radius: 14px;
        padding: 14px 24px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 8px 30px rgba(15, 23, 42, 0.08);
    }

    .fleet-nav-brand {
        display: flex;
        align-items: center;
        gap: 14px;
    }

    .fleet-nav-logo {
        font-family: 'Orbitron', monospace;
        font-size: 20px;
        font-weight: 900;
        background: linear-gradient(135deg, #0284c7 0%, #7c3aed 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 2px;
    }

    .fleet-telemetry-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-family: 'JetBrains Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }

    .badge-nominal {
        background: rgba(5, 150, 105, 0.12);
        color: var(--neon-emerald);
        border: 1px solid rgba(5, 150, 105, 0.4);
        box-shadow: 0 2px 8px rgba(5, 150, 105, 0.15);
    }

    .badge-warning {
        background: rgba(217, 119, 6, 0.12);
        color: var(--neon-amber);
        border: 1px solid rgba(217, 119, 6, 0.4);
        box-shadow: 0 2px 8px rgba(217, 119, 6, 0.15);
    }

    .badge-critical {
        background: rgba(220, 38, 38, 0.15);
        color: var(--neon-crimson);
        border: 1px solid rgba(220, 38, 38, 0.6);
        box-shadow: 0 4px 16px rgba(220, 38, 38, 0.25);
        animation: criticalPulse 1.2s infinite alternate;
    }

    @keyframes criticalPulse {
        0% {
            background-color: rgba(220, 38, 38, 0.22);
            border-color: rgba(220, 38, 38, 0.9);
            box-shadow: 0 0 25px rgba(220, 38, 38, 0.4);
        }
        100% {
            background-color: rgba(220, 38, 38, 0.08);
            border-color: rgba(220, 38, 38, 0.35);
            box-shadow: 0 0 10px rgba(220, 38, 38, 0.15);
        }
    }

    .fleet-alert-banner {
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 22px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        animation: criticalPulse 0.9s infinite alternate;
        border: 2px solid var(--neon-crimson);
        background: rgba(254, 242, 242, 0.95);
    }

    .fleet-alert-title {
        font-family: 'Orbitron', monospace;
        font-size: 20px;
        font-weight: 800;
        color: #991b1b;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .fleet-alert-subtitle {
        color: #7f1d1d;
        font-size: 15px;
        font-weight: 600;
        margin-top: 5px;
    }

    .fleet-metric-tile {
        background: #ffffff;
        border: 1px solid rgba(2, 132, 199, 0.18);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(15, 23, 42, 0.04);
        transition: border-color 0.2s;
    }

    .fleet-metric-tile:hover {
        border-color: var(--neon-cyan);
    }

    /* Tabular aligned spec rows */
    .fleet-spec-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid rgba(2, 132, 199, 0.08);
        font-family: 'Rajdhani', sans-serif;
        font-size: 15px;
    }

    .fleet-spec-row:last-child {
        border-bottom: none;
    }

    .fleet-spec-lbl {
        color: var(--text-dim);
        font-weight: 600;
        font-size: 13px;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }

    .fleet-spec-val {
        color: var(--text-bright);
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        font-size: 14px;
        text-align: right;
    }

    .fleet-metric-val {
        font-family: 'Orbitron', monospace;
        font-size: 28px;
        font-weight: 700;
        color: var(--neon-cyan);
    }

    .fleet-metric-lbl {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: var(--text-dim);
        margin-top: 4px;
        font-weight: 600;
    }

    .fleet-speed-display {
        font-family: 'Orbitron', monospace;
        font-size: 54px;
        font-weight: 900;
        line-height: 1;
        background: linear-gradient(180deg, #0f172a 0%, var(--neon-cyan) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .stButton>button {
        background: linear-gradient(135deg, rgba(2, 132, 199, 0.12) 0%, rgba(124, 58, 237, 0.15) 100%) !important;
        color: var(--neon-cyan) !important;
        border: 1px solid var(--neon-cyan) !important;
        border-radius: 10px !important;
        font-family: 'Orbitron', monospace !important;
        font-weight: 700 !important;
        letter-spacing: 1.2px !important;
        padding: 10px 22px !important;
        box-shadow: 0 4px 15px rgba(2, 132, 199, 0.10) !important;
        transition: all 0.3s ease !important;
    }

    .stButton>button:hover {
        background: linear-gradient(135deg, var(--neon-cyan) 0%, var(--neon-violet) 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 6px 25px rgba(2, 132, 199, 0.30) !important;
        transform: translateY(-2px);
    }

    .pulse-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        display: inline-block;
        background-color: var(--neon-emerald);
        box-shadow: 0 0 10px var(--neon-emerald);
        animation: pulseAnimation 1.5s infinite;
    }

    @keyframes pulseAnimation {
        0% { transform: scale(0.9); opacity: 0.8; }
        50% { transform: scale(1.3); opacity: 1; }
        100% { transform: scale(0.9); opacity: 0.8; }
    }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-void); }
    ::-webkit-scrollbar-thumb { background: rgba(2, 132, 199, 0.3); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--neon-cyan); }
    </style>
    """


def get_audio_alert_html(active: bool = False) -> str:
    """Renders in-browser audio warning buzzer using Web Audio API synthesis."""
    if not active:
        return ""
    
    return """
    <script>
    (function playEmergencyTone() {
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            const ctx = new AudioContext();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            
            osc.type = 'sawtooth';
            const now = ctx.currentTime;
            
            osc.frequency.setValueAtTime(880, now);
            osc.frequency.exponentialRampToValueAtTime(587, now + 0.15);
            osc.frequency.exponentialRampToValueAtTime(880, now + 0.30);
            osc.frequency.exponentialRampToValueAtTime(587, now + 0.45);
            
            gain.gain.setValueAtTime(0.25, now);
            gain.gain.exponentialRampToValueAtTime(0.01, now + 0.55);
            
            osc.connect(gain);
            gain.connect(ctx.destination);
            
            osc.start(now);
            osc.stop(now + 0.55);
        } catch (e) {
            console.warn("Audio Alert notice:", e);
        }
    })();
    </script>
    """


def get_spoken_voice_alert_html(message: str, tone: bool = True, cancel_previous: bool = True) -> str:
    """
    Renders HTML/JavaScript that speaks instructions aloud through laptop speakers
    using browser SpeechSynthesis API, preceded by an emergency tone.
    """
    escaped_msg = message.replace('"', '\\"').replace("'", "\\'")
    tone_code = """
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                const ctx = new AudioContext();
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

    cancel_code = "window.speechSynthesis.cancel();" if cancel_previous else ""

    return f"""
    <div style="display:none;">
        <script>
        (function() {{
            {tone_code}
            if ('speechSynthesis' in window) {{
                {cancel_code}
                const msg = new SpeechSynthesisUtterance("{escaped_msg}");
                msg.rate = 1.05;
                msg.pitch = 1.1;
                msg.volume = 1.0;
                window.speechSynthesis.speak(msg);
            }}
        }})();
        </script>
    </div>
    """


def render_cockpit_header(vehicle_id: str = "TN 58 AA 4920", driver_name: str = "Arun Kumar", sync_status: str = "ONLINE"):
    """HTML template for the cockpit top bar in light mode."""
    return f"""
    <div class="fleet-navbar">
        <div class="fleet-nav-brand">
            <span class="fleet-nav-logo">&#10038; FLEETGUARD // SENTINEL DMS</span>
            <span class="fleet-telemetry-badge badge-nominal"><span class="pulse-dot"></span> SENSORS ARMED</span>
        </div>
        <div style="display: flex; gap: 24px; align-items: center; font-family: 'JetBrains Mono', monospace; font-size: 13px;">
            <div><span style="color: var(--text-dim);">LORRY:</span> <strong style="color: var(--neon-cyan);">{vehicle_id}</strong></div>
            <div><span style="color: var(--text-dim);">DRIVER:</span> <strong style="color: var(--text-bright);">{driver_name}</strong></div>
            <div><span class="fleet-telemetry-badge badge-nominal">DISPATCH: {sync_status}</span></div>
        </div>
    </div>
    """
