"""
Fleet Command Center Dashboard Module
Displays dispatcher / headquarters overview:
- Synchronized fleet metrics
- Escalation incident table from SQLite
- Live JSON packet inspection
- Fleet wide alert status
"""

import json
import streamlit as st


def render_command_center_view(fleet_sync_mgr):
    """Renders the Fleet Command Center dispatch view in Streamlit."""
    st.markdown("""
    <div style="border-bottom: 2px solid rgba(2, 132, 199, 0.25); padding-bottom: 12px; margin-bottom: 20px;">
        <h2 style="margin: 0; color: var(--neon-cyan); letter-spacing: 2px;">
            &#128752; FLEET COMMAND CENTER // DISPATCH ESCALATION CONSOLE
        </h2>
        <p style="color: var(--text-dim); margin-top: 4px; font-size: 14px;">
            Real-time synchronization across vehicle telemetry, driver biometric feeds, and intervention logs.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Top KPI Cards
    col1, col2, col3, col4 = st.columns(4)

    recent_escalations = fleet_sync_mgr.fetch_recent_escalations(limit=10)
    recent_telematics = fleet_sync_mgr.fetch_recent_telematics(limit=20)

    total_escalations = len(recent_escalations)
    latest_speed = recent_telematics[0]["speed_kmh"] if recent_telematics else 0.0
    latest_risk = recent_telematics[0]["risk_score"] if recent_telematics else 0.0
    latest_status = recent_telematics[0]["intervention_status"] if recent_telematics else "ONLINE"

    with col1:
        st.markdown(f"""
        <div class="fleet-metric-tile">
            <div class="fleet-metric-val">{latest_speed:.0f} <span style="font-size: 16px;">km/h</span></div>
            <div class="fleet-metric-lbl">ACTIVE VEHICLE SPEED</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        risk_color = "#059669" if latest_risk < 40 else ("#d97706" if latest_risk < 70 else "#dc2626")
        st.markdown(f"""
        <div class="fleet-metric-tile">
            <div class="fleet-metric-val" style="color: {risk_color};">{latest_risk:.1f}%</div>
            <div class="fleet-metric-lbl">TELEMATICS RISK INDEX</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        status_color = "#dc2626" if "ESCALATED" in latest_status else ("#d97706" if "ALERT" in latest_status else "var(--neon-cyan)")
        st.markdown(f"""
        <div class="fleet-metric-tile">
            <div class="fleet-metric-val" style="font-size: 16px; color: {status_color}; font-weight: 700;">{latest_status}</div>
            <div class="fleet-metric-lbl">INTERVENTION STATE</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        esc_color = "#dc2626" if total_escalations > 0 else "#059669"
        st.markdown(f"""
        <div class="fleet-metric-tile">
            <div class="fleet-metric-val" style="color: {esc_color}; font-weight: 700;">{total_escalations}</div>
            <div class="fleet-metric-lbl">DISPATCH INCIDENTS LOGGED</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    left_col, right_col = st.columns([1.3, 1])

    with left_col:
        st.markdown("### &#128680; Live Escalation Log (SQLite Database)")
        if recent_escalations:
            st.dataframe(
                recent_escalations,
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No active escalation events recorded yet. Fleet operating within nominal safety margins.")

        st.markdown("### &#128202; Telematics Rolling Stream")
        if recent_telematics:
            st.dataframe(
                recent_telematics,
                hide_index=True,
                use_container_width=True
            )

    with right_col:
        st.markdown("### &#128225; Real-Time JSON Telemetry Packet")
        st.caption(f"Synchronized with `{fleet_sync_mgr.JSON_PATH}`")
        try:
            with open(fleet_sync_mgr.JSON_PATH, "r", encoding="utf-8") as f:
                live_payload = json.load(f)
            st.json(live_payload)
        except Exception:
            st.warning("Awaiting initial JSON payload sync...")
