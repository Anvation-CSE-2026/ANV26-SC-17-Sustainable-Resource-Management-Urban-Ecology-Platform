import streamlit as st


def metric_card(col, label, value, accent):
    col.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color:{accent};">{value}</div>
        </div>
    """, unsafe_allow_html=True)


def status_banner(total_overflow, reoptimized):
    if total_overflow == 0:
        st.markdown('<div class="status-ok">🟢 No predicted overflow — all waste can be processed</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="status-alert">🔴 Potential overflow: {total_overflow/1000:.2f} T</div>', unsafe_allow_html=True)
        if not reoptimized:
            st.markdown('<div class="status-warn">⚠️ Allocation plan has NOT been recalculated. Click <b>Re-optimize</b> below.</div>', unsafe_allow_html=True)


def facility_card(col, facility, allocated_kg, text_muted):
    util = allocated_kg / facility["capacity_kg"] * 100
    color = "#16a34a" if util < 70 else "#f59e0b" if util < 95 else "#dc2626"
    col.markdown(f"""
        <div class="facility-card">
            <div class="facility-name">Facility {facility['id']}</div>
            <div class="facility-type">Accepts: {facility['accepts']} · {facility['distance_km']} km</div>
            <div style="margin-top:10px; font-size:0.9rem; color:{text_muted};">
                {round(allocated_kg)} / {facility['capacity_kg']} kg
            </div>
            <div class="util-bar">
                <div class="util-fill" style="width:{min(util,100)}%; background:{color};"></div>
            </div>
            <div style="margin-top:6px; font-size:0.8rem; color:{color}; font-weight:600;">
                {util:.0f}% utilized
            </div>
        </div>
    """, unsafe_allow_html=True)


def success_banner(text):
    st.markdown(f'<div class="status-success">{text}</div>', unsafe_allow_html=True)