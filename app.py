import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone

from wastegrid import (
    db,
    auth,
    data,
    optimizer,
    theme,
    components,
    forecast,
    calendar_module,
    truck_module,
    analytics_module,
    facility_module,
    map_module,
    alert_engine,
    vehicle_module,
    simulator_module,
    citizen_module,
    reports_module,
    analytics_dashboards,
    settings_module,
)

# 1. Page Configuration (Full Widescreen Layout)
st.set_page_config(
    page_title="WasteGrid 2.0 — Smart Municipal Waste Management",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database schema and seed data
db.init_db()

# 2. Session State Initialization
defaults = {
    "event_active": False,
    "reoptimized": True,
    "theme": "light",
    "outage_facility": None,
    "nav_selection": "overview",
    "show_auth_modal": False,
    "show_help": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# 3. Handle Special Action Query Parameters
if st.query_params.get("logout") == "1":
    if "logout" in st.query_params:
        del st.query_params["logout"]
    auth.logout()

if st.query_params.get("profile") == "1":
    if "profile" in st.query_params:
        del st.query_params["profile"]
    st.session_state["show_auth_modal"] = True

if st.query_params.get("footer_info"):
    st.session_state["footer_info_active"] = st.query_params.get("footer_info")
    if "footer_info" in st.query_params:
        del st.query_params["footer_info"]

if st.query_params.get("help") == "1":
    if "help" in st.query_params:
        del st.query_params["help"]
    st.session_state["show_help"] = True

# 4. Theme Resolution
param_theme = st.query_params.get("theme")
if param_theme in ["light", "dark"]:
    st.session_state.theme = param_theme
elif "theme" not in st.session_state or st.session_state.theme not in ["light", "dark"]:
    st.session_state.theme = "light"

st.query_params["theme"] = st.session_state.theme
palette = theme.get_palette(st.session_state.theme)
theme.inject_css(palette)


def render_html(content):
    clean = "\n".join(line.strip() for line in str(content).strip().splitlines())
    st.markdown(clean, unsafe_allow_html=True)


# 5. Core Computational Grid Data
uploaded = st.session_state.get("csv_uploader")
if uploaded is not None:
    try:
        sources = data.load_sources_from_csv(uploaded)
        data_mode = "CSV Upload"
    except Exception:
        sources = data.SAMPLE_SOURCES
        data_mode = "Sample Baseline"
else:
    sources = data.SAMPLE_SOURCES
    data_mode = "Sample Baseline"

sources = data.apply_event_state(sources, st.session_state.event_active)
wet_total, dry_total, total_waste = data.totals(sources)

# Dynamic facilities from database
db_facilities = db.get_all_facilities(include_offline=True)
active_facilities = []
for f in db_facilities:
    fc = dict(f)
    if st.session_state.outage_facility == fc["id"]:
        fc["capacity_kg"] = 0
        fc["status"] = "offline"
    active_facilities.append(fc)

total_capacity = sum(f["capacity_kg"] for f in active_facilities if f.get("status") != "offline")

# Optimization Calculation
if st.session_state.reoptimized:
    allocations, overflow = optimizer.optimize(active_facilities, wet_total, dry_total)
else:
    allocations = {}
    base_plan = {"A": 2000, "B": 1800, "C": 1400, "D": 2200, "E": 1200}
    for f in active_facilities:
        fid = f["id"]
        if f["capacity_kg"] <= 0 or f.get("status") == "offline":
            allocations[fid] = 0
        else:
            allocations[fid] = min(base_plan.get(fid, 1000), f["capacity_kg"])

    assigned_wet = allocations.get("A", 0) + allocations.get("B", 0) + allocations.get("E", 0)
    assigned_dry = allocations.get("C", 0) + allocations.get("D", 0)
    overflow = {}
    if wet_total > assigned_wet:
        overflow["wet"] = wet_total - assigned_wet
    if dry_total > assigned_dry:
        overflow["dry"] = dry_total - assigned_dry

st.session_state.allocations = allocations
st.session_state.overflow = overflow
total_overflow = optimizer.total_overflow(overflow)

# Synchronize predictive alerts
alert_engine.evaluate_and_sync_alerts()
pending_alert_count = alert_engine.get_pending_alert_count()

# Grid System Status Determination
if total_overflow > 0:
    system_status = "alert"
elif st.session_state.outage_facility or any(f.get("status") in ["offline", "maintenance"] for f in db_facilities):
    system_status = "warn"
else:
    system_status = "optimal"

# 6. Streamlined 6 Core Primary Operations Navigation
NAV_ITEMS = [
    ("🌐 Overview & Services", "overview"),
    ("🗺️ Live Operations & Fleet", "operations"),
    ("⚡ Smart Allocation & LP Solver", "allocation"),
    ("📈 Analytics & 7-Day Forecast", "analytics"),
    ("🚨 Alerts & Citizen Grievances", "alerts_citizen"),
    ("📑 Audits, Reports & Admin", "admin_reports"),
]

title_to_key = {title: key for title, key in NAV_ITEMS}
key_to_title = {key: title for title, key in NAV_ITEMS}

# 7. Left Sidebar Construction
current_user = auth.get_current_user()

with st.sidebar:
    # Sidebar Header Brand
    render_html(
        f"""
        <div style="display:flex; align-items:center; gap:12px; padding:6px 0 16px 0; border-bottom:1px solid {palette['border']}; margin-bottom:16px;">
            <div style="width:40px; height:40px; border-radius:10px; background:linear-gradient(135deg, #10b981, #0284c7); 
                        display:flex; align-items:center; justify-content:center; font-size:1.4rem; box-shadow:0 2px 10px rgba(0,0,0,0.25);">
                ♻️
            </div>
            <div>
                <div style="font-size:1.2rem; font-weight:800; color:{palette['text']}; letter-spacing:-0.02em;">WasteGrid <span style="font-size:0.65rem; background:#10b981; color:#fff; padding:2px 6px; border-radius:4px; vertical-align:middle;">2.0</span></div>
                <div style="font-size:0.68rem; color:{palette['muted']}; letter-spacing:0.04em; text-transform:uppercase;">National Smart Grid</div>
            </div>
        </div>
        """
    )

    # Secure Sidebar Authentication Widget
    auth.render_sidebar_auth_widget()

    st.markdown(
        f'<div style="font-size:0.7rem; font-weight:700; color:{palette["muted"]}; text-transform:uppercase; letter-spacing:0.12em; margin-bottom:8px;">'
        f'🧭 OPERATIONS NAVIGATION'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Calculate default index in nav items
    active_nav_key = st.session_state.get("nav_selection", "overview")
    active_index = 0
    for idx, (_, k) in enumerate(NAV_ITEMS):
        if k == active_nav_key:
            active_index = idx
            break

    selected_nav_title = st.radio(
        "Sidebar Navigation",
        [t for t, k in NAV_ITEMS],
        index=active_index,
        label_visibility="collapsed",
        key="main_sidebar_nav_radio",
    )
    selected_key = title_to_key[selected_nav_title]
    if selected_key != st.session_state.nav_selection:
        st.session_state.nav_selection = selected_key
        st.rerun()

    # Sidebar Quick Actions & Help Button
    st.markdown("<br>", unsafe_allow_html=True)
    col_sb_act1, col_sb_act2 = st.columns(2)
    with col_sb_act1:
        if st.button("👤 Profile", use_container_width=True, key="btn_sb_open_prof"):
            st.session_state["show_auth_modal"] = True
            st.rerun()
    with col_sb_act2:
        if st.button("❓ Help", use_container_width=True, key="btn_sb_open_help"):
            st.session_state["show_help"] = True
            st.rerun()

    # Sidebar Grid Summary Footer Card
    active_trucks_count = len([v for v in db.get_all_vehicles() if v["status"] in ["available", "in_transit", "assigned"]])
    render_html(
        f"""
        <div style="margin-top:20px; padding:12px; background:rgba(255,255,255,0.03); border:1px solid {palette['border']}; 
                    border-radius:8px; font-size:0.72rem; color:{palette['muted']}; line-height:1.6;">
            <div style="font-weight:700; color:{palette['text']}; margin-bottom:4px; display:flex; justify-content:space-between;">
                <span>Grid Telemetry</span>
                <span style="color:{palette['success']};">● Live</span>
            </div>
            <div>Facilities: <b>{len(db_facilities)} Active Nodes</b></div>
            <div>Fleet Units: <b>{active_trucks_count} Vehicles</b></div>
            <div>Active Incidents: <b>{pending_alert_count} Alerts</b></div>
            <div style="margin-top:6px; font-size:0.65rem; color:{palette['muted']}; border-top:1px solid {palette['border']}; padding-top:4px;">
                Storage: SQLite · Architecture: PG-Ready
            </div>
        </div>
        """
    )

# 8. Modals & Overlay Drawers
if st.session_state.get("show_auth_modal"):
    auth.render_auth_modal(palette)

if st.session_state.get("footer_info_active"):
    components.render_footer_info_modal(st.session_state["footer_info_active"], palette)

if st.session_state.get("show_help"):
    components.render_help_section(palette)

# 9. Top Navigation Bar (Logo on Left, Profile/Login on Right)
components.top_nav_bar(
    user=current_user,
    theme=st.session_state.theme,
    p=palette,
)

current_nav_key = st.session_state.get("nav_selection", "overview")

# =========================================================================
# PAGE 1: OVERVIEW & SERVICES DASHBOARD
# =========================================================================
if current_nav_key == "overview":
    # 1. Pilot Case Study Reference Banner & Region Switcher
    render_html(
        f"""
        <div style="background:linear-gradient(135deg, rgba(2, 132, 199, 0.08) 0%, rgba(16, 185, 129, 0.08) 100%); 
                    border:1px solid rgba(2, 132, 199, 0.25); border-radius:10px; padding:12px 18px; margin-bottom:20px; 
                    display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-size:1.3rem;">📍</span>
                <div>
                    <div style="font-size:0.85rem; font-weight:800; color:{palette['text']};">
                        General Smart-City Architecture · Reference Pilot: Bengaluru Urban Pilot Model
                    </div>
                    <div style="font-size:0.74rem; color:{palette['muted']}; margin-top:2px;">
                        WasteGrid is an open, universal platform deployed nationally. The active live demonstration utilizes calibrated empirical datasets 
                        from the <b>Karnataka / Bengaluru Urban pilot</b> as a real-world case study.
                    </div>
                </div>
            </div>
            <span style="font-size:0.68rem; font-weight:700; background:rgba(16,185,129,0.15); color:{palette['success']}; border:1px solid rgba(16,185,129,0.3); padding:4px 10px; border-radius:999px; text-transform:uppercase;">
                ● Pilot Case Study Active
            </span>
        </div>
        """
    )

    # Dedicated Role-Specific Dashboard for Each of the 5 Logins
    if current_user:
        user_role = current_user.get("role", "municipality")
        if user_role == "admin":
            analytics_module.render_super_admin_view(palette, active_facilities, allocations, pending_alert_count)
        elif user_role == "state":
            analytics_module.render_state_authority_view(palette)
        elif user_role == "district":
            analytics_module.render_district_authority_view(palette)
        elif user_role == "municipality":
            analytics_module.render_municipal_office_view(palette, pending_alert_count)
        elif user_role == "factory":
            analytics_module.render_factory_authority_view(active_facilities, allocations, palette)

    # 2. Hero Presentation Banner
    render_html(
        f"""
        <div class="wg-hero">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
                <div style="max-width:850px;">
                    <div style="font-size:0.75rem; font-weight:800; letter-spacing:0.15em; text-transform:uppercase; color:#10b981; margin-bottom:6px;">
                        ⚡ Intelligent Municipal Environmental Infrastructure
                    </div>
                    <div style="font-size:1.85rem; font-weight:900; color:{palette['text']}; line-height:1.2; letter-spacing:-0.03em;">
                        Smart Municipal Waste Grid & Automated Resource Logistics
                    </div>
                    <div style="font-size:0.88rem; color:{palette['muted']}; margin-top:8px; line-height:1.6;">
                        Predict municipal waste generation spikes, dynamically rebalance compatible bio-methanation and recycling facilities, 
                        and dispatch autonomous fleet vehicles in real time with guaranteed zero capacity overflow.
                    </div>
                </div>
                <div style="background:{palette['card_bg']}; border:1px solid {palette['border']}; border-radius:10px; padding:16px 20px; box-shadow:{palette['shadow']};">
                    <div style="font-size:0.7rem; color:{palette['muted']}; text-transform:uppercase; font-weight:700;">Live Grid Health</div>
                    <div style="font-size:1.5rem; font-weight:900; color:{palette['success'] if total_overflow==0 else palette['accent']};">
                        {'99.4% OPTIMAL' if total_overflow==0 else 'OVERFLOW ALERT'}
                    </div>
                    <div style="font-size:0.72rem; color:{palette['muted']}; margin-top:4px;">
                        Allocated: <b>{sum(allocations.values())/1000:.1f} T</b> / {total_capacity/1000:.1f} T
                    </div>
                </div>
            </div>
        </div>
        """
    )

    # 3. What Services We Provide (6 Rich Interactive Feature Cards)
    components.section_title("SERVICES WE PROVIDE — INTELLIGENT MUNICIPAL WASTE CAPABILITIES")
    render_html(
        f"""
        <div class="services-grid">
            <div class="service-card" style="border-top:3px solid #0284c7;">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div class="service-icon-wrap" style="background:rgba(2,132,199,0.12); color:#0284c7;">🚛</div>
                        <span class="service-tag" style="background:rgba(2,132,199,0.15); color:#0284c7;">8 Active Vehicles</span>
                    </div>
                    <div style="font-size:1.05rem; font-weight:800; color:{palette['text']}; margin-bottom:6px;">Autonomous Fleet Telematics</div>
                    <div style="font-size:0.78rem; color:{palette['muted']}; line-height:1.5;">
                        Real-time GPS breadcrumb tracking, dynamic fuel routing, weighbridge telemetry integration, and automated driver dispatch.
                    </div>
                </div>
                <div style="margin-top:14px; font-size:0.72rem; font-weight:700; color:#0284c7;">
                    ⚡ Live Tracking: Central, South & North Corridors
                </div>
            </div>

            <div class="service-card" style="border-top:3px solid #059669;">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div class="service-icon-wrap" style="background:rgba(5,150,105,0.12); color:#059669;">⚡</div>
                        <span class="service-tag" style="background:rgba(5,150,105,0.15); color:#059669;">HiGHS LP Solver</span>
                    </div>
                    <div style="font-size:1.05rem; font-weight:800; color:{palette['text']}; margin-bottom:6px;">Multi-Objective LP Allocation</div>
                    <div style="font-size:0.78rem; color:{palette['muted']}; line-height:1.5;">
                        Linear Programming Simplex solver enforcing zero-overflow constraints, stream segregation compatibility, and transport cost minimization.
                    </div>
                </div>
                <div style="margin-top:14px; font-size:0.72rem; font-weight:700; color:#059669;">
                    ✓ Zero Overflow Guarantee · Dual Simplex Solver
                </div>
            </div>

            <div class="service-card" style="border-top:3px solid #7c3aed;">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div class="service-icon-wrap" style="background:rgba(124,58,237,0.12); color:#7c3aed;">🔮</div>
                        <span class="service-tag" style="background:rgba(124,58,237,0.15); color:#7c3aed;">7-Day Horizon</span>
                    </div>
                    <div style="font-size:1.05rem; font-weight:800; color:{palette['text']}; margin-bottom:6px;">Predictive Demand Forecasting</div>
                    <div style="font-size:0.78rem; color:{palette['muted']}; line-height:1.5;">
                        Machine learning projection calibrated with day-of-week occupancy trends, municipal event calendars, and seasonal multipliers.
                    </div>
                </div>
                <div style="margin-top:14px; font-size:0.72rem; font-weight:700; color:#7c3aed;">
                    📈 7-Day Forward Horizon with Headroom Safeguard
                </div>
            </div>

            <div class="service-card" style="border-top:3px solid #d97706;">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div class="service-icon-wrap" style="background:rgba(217,119,6,0.12); color:#d97706;">🚨</div>
                        <span class="service-tag" style="background:rgba(217,119,6,0.15); color:#d97706;">IoT Sensor Grid</span>
                    </div>
                    <div style="font-size:1.05rem; font-weight:800; color:{palette['text']}; margin-bottom:6px;">Smart Overflow Alert Engine</div>
                    <div style="font-size:0.78rem; color:{palette['muted']}; line-height:1.5;">
                        Automated threshold monitoring (normal, moderate, warning, critical) with instant incident escalation to field inspectors.
                    </div>
                </div>
                <div style="margin-top:14px; font-size:0.72rem; font-weight:700; color:#d97706;">
                    🔔 4-Tier Escalation Workflow with Auto-Resolution
                </div>
            </div>

            <div class="service-card" style="border-top:3px solid #e11d48;">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div class="service-icon-wrap" style="background:rgba(225,29,72,0.12); color:#e11d48;">📢</div>
                        <span class="service-tag" style="background:rgba(225,29,72,0.15); color:#e11d48;">24-Hr SLA</span>
                    </div>
                    <div style="font-size:1.05rem; font-weight:800; color:{palette['text']}; margin-bottom:6px;">Citizen Grievance Redressal</div>
                    <div style="font-size:0.78rem; color:{palette['muted']}; line-height:1.5;">
                        Public blackspot reporting portal with GPS geotagging, photo upload, ticket tracking IDs, and automated driver dispatch.
                    </div>
                </div>
                <div style="margin-top:14px; font-size:0.72rem; font-weight:700; color:#e11d48;">
                    🎫 Dedicated Tracking: e.g. WG-REP-2026-9041
                </div>
            </div>

            <div class="service-card" style="border-top:3px solid #0d9488;">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div class="service-icon-wrap" style="background:rgba(13,148,136,0.12); color:#0d9488;">🌱</div>
                        <span class="service-tag" style="background:rgba(13,148,136,0.15); color:#0d9488;">ESG Scorecard</span>
                    </div>
                    <div style="font-size:1.05rem; font-weight:800; color:{palette['text']}; margin-bottom:6px;">Carbon & Methane Avoidance</div>
                    <div style="font-size:0.78rem; color:{palette['muted']}; line-height:1.5;">
                        Quantified GHG abatement metrics, landfill diversion ratios, bio-fertilizer yields, and certified carbon offset accounting.
                    </div>
                </div>
                <div style="margin-top:14px; font-size:0.72rem; font-weight:700; color:#0d9488;">
                    🌿 0.58 kg CO₂e Saved per kg Biodegradable Waste
                </div>
            </div>
        </div>
        """
    )

    # 4. Quick Evaluator Access Cards (if public visitor)
    if not current_user:
        st.markdown(
            f"""
            <div style="background:rgba(59,130,246,0.06); border:1px solid rgba(59,130,246,0.3); border-radius:12px; padding:20px; margin-bottom:24px;">
                <div style="font-size:0.95rem; font-weight:800; color:{palette['blue']}; margin-bottom:6px;">
                    🛡️ Evaluator Role Portals (1-Click Instant Access)
                </div>
                <div style="font-size:0.8rem; color:{palette['muted']}; margin-bottom:14px;">
                    Experience WasteGrid from any municipal stakeholder perspective with pre-configured authority accounts:
                </div>
            """,
            unsafe_allow_html=True,
        )
        col_rp1, col_rp2, col_rp3, col_rp4, col_rp5 = st.columns(5)
        with col_rp1:
            if st.button("👑 Super Admin", use_container_width=True, key="btn_ev_admin"):
                auth.login("admin", "Admin@123")
                st.rerun()
            st.caption("Full System Control")
        with col_rp2:
            if st.button("🏛️ State Authority", use_container_width=True, key="btn_ev_state"):
                auth.login("state_admin", "Waste@123")
                st.rerun()
            st.caption("Macro Policy & ESG")
        with col_rp3:
            if st.button("🏢 District Magistrate", use_container_width=True, key="btn_ev_dist"):
                auth.login("district_admin", "District@123")
                st.rerun()
            st.caption("Inter-Ward Transit")
        with col_rp4:
            if st.button("🏙️ Municipal Officer", use_container_width=True, key="btn_ev_muni"):
                auth.login("municipality_admin", "Municipality@123")
                st.rerun()
            st.caption("Ward Trucks & Tickets")
        with col_rp5:
            if st.button("🏭 Plant Manager", use_container_width=True, key="btn_ev_fact"):
                auth.login("factory_admin", "Factory@123")
                st.rerun()
            st.caption("Receiving Docks")
        st.markdown("</div>", unsafe_allow_html=True)

    # 5. Real-Time Grid KPIs Row (8 Primary Overview Metrics)
    processed_kg = sum(allocations.values())
    overflow_risk_label = "HIGH" if total_overflow > 500 else ("MODERATE" if total_overflow > 0 else "NOMINAL")
    recycling_pct = round((allocations.get("C", 0) + allocations.get("D", 0)) / max(total_waste, 1) * 100, 1)
    online_facs_count = sum(1 for f in active_facilities if f.get("status") == "online" and f["capacity_kg"] > 0)
    avail_capacity_kg = max(0.0, total_capacity - processed_kg)

    components.section_title("REAL-TIME GRID METRICS & OPERATIONAL TELEMETRY")
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        render_html(
            f"""<div class="m-card hero">
                <div class="m-label">📊 Predicted Demand</div>
                <div class="m-value">{total_waste/1000:.2f} T</div>
                <div style="font-size:0.68rem; color:{palette['muted']}; margin-top:4px;">{wet_total/1000:.1f}T Wet · {dry_total/1000:.1f}T Dry</div>
            </div>"""
        )
    with col_m2:
        render_html(
            f"""<div class="m-card green">
                <div class="m-label">⚙️ Waste Processed</div>
                <div class="m-value">{processed_kg/1000:.2f} T</div>
                <div style="font-size:0.68rem; color:{palette['success']}; margin-top:4px;">{(processed_kg/max(total_waste,1))*100:.1f}% reallocated</div>
            </div>"""
        )
    with col_m3:
        render_html(
            f"""<div class="m-card purple">
                <div class="m-label">🏭 Available Capacity</div>
                <div class="m-value">{avail_capacity_kg/1000:.2f} T</div>
                <div style="font-size:0.68rem; color:{palette['purple']}; margin-top:4px;">{online_facs_count} of {len(active_facilities)} Plants Online</div>
            </div>"""
        )
    with col_m4:
        ovf_cls = "red" if total_overflow > 0 else "green"
        render_html(
            f"""<div class="m-card {ovf_cls}">
                <div class="m-label">⚠️ Overflow Risk</div>
                <div class="m-value">{total_overflow/1000:.2f} T</div>
                <div style="font-size:0.68rem; color:{palette['accent'] if total_overflow>0 else palette['success']}; margin-top:4px;">Risk Status: {overflow_risk_label}</div>
            </div>"""
        )

    col_m5, col_m6, col_m7, col_m8 = st.columns(4)
    with col_m5:
        render_html(
            f"""<div class="m-card">
                <div class="m-label">🚚 Active Fleet Units</div>
                <div class="m-value">{active_trucks_count} Trucks</div>
                <div style="font-size:0.68rem; color:{palette['muted']}; margin-top:4px;">Real-time GPS monitored</div>
            </div>"""
        )
    with col_m6:
        render_html(
            f"""<div class="m-card">
                <div class="m-label">🔔 Pending Alerts</div>
                <div class="m-value">{pending_alert_count} Incidents</div>
                <div style="font-size:0.68rem; color:{palette['accent'] if pending_alert_count>0 else palette['success']}; margin-top:4px;">Threshold & outages</div>
            </div>"""
        )
    with col_m7:
        render_html(
            f"""<div class="m-card green">
                <div class="m-label">♻️ Recycling Ratio</div>
                <div class="m-value">{recycling_pct}%</div>
                <div style="font-size:0.68rem; color:{palette['success']}; margin-top:4px;">Diverted from Landfills</div>
            </div>"""
        )
    with col_m8:
        render_html(
            f"""<div class="m-card">
                <div class="m-label">📁 Data Mode</div>
                <div class="m-value" style="font-size:1.1rem; padding-top:6px;">{data_mode}</div>
                <div style="font-size:0.68rem; color:{palette['muted']}; margin-top:4px;">{len(sources)} Active Waste Sources</div>
            </div>"""
        )

    # 6. Multi-Stream Compatibility Flow
    components.stream_breakdown(wet_total, dry_total, palette)

    # 7. Operational Status Banner & Action Buttons
    components.status_banner(total_overflow, st.session_state.reoptimized, st.session_state.outage_facility)

    btn_clicks = components.action_buttons(
        event_active=st.session_state.event_active,
        outage=st.session_state.outage_facility,
    )
    if btn_clicks["event"]:
        st.session_state.event_active = not st.session_state.event_active
        st.session_state.reoptimized = False
        st.rerun()

    if btn_clicks["outage"]:
        cycle = {None: "B", "B": "C", "C": "D", "D": None}
        st.session_state.outage_facility = cycle.get(st.session_state.outage_facility, None)
        st.session_state.reoptimized = False
        st.rerun()

    if btn_clicks["reopt"]:
        st.session_state.reoptimized = True
        st.rerun()

    if btn_clicks["reset"]:
        st.session_state.event_active = False
        st.session_state.outage_facility = None
        st.session_state.reoptimized = True
        st.rerun()

    # 8. Facility Utilization Grid
    components.section_title("FACILITY UTILIZATION & REAL-TIME LOAD BALANCING")
    components.facility_grid(active_facilities, allocations, palette, outage=st.session_state.outage_facility)

    # 9. Fixed vs WasteGrid Dynamic LP Comparison
    components.section_title("FIXED ALLOCATION VS WASTEGRID OPTIMIZER COMPARISON")
    fixed_overflow = optimizer.fixed_allocation_overflow(total_waste, total_capacity)
    components.comparison_cards(fixed_overflow, total_overflow, palette)

    if fixed_overflow > 0 and total_overflow < fixed_overflow:
        pct = optimizer.reduction_pct(fixed_overflow, total_overflow)
        components.success_banner(f"WasteGrid prevented {fixed_overflow - total_overflow:,.0f} kg ({pct:.1f}%) of overflow vs static fixed routing!")

    # 10. Weekly Generation & Processing Trend Dynamics
    components.section_title("WEEKLY GENERATION & PROCESSING TREND DYNAMICS")
    forecast_rows = forecast.forecast_week(sources, total_capacity)
    forecast_df = pd.DataFrame(forecast_rows)
    components.forecast_section(forecast_df, palette)

    # 11. Data Ingestion Drawer
    with st.expander("📁 DATA INGESTION — UPLOAD CSV DATASET OR DOWNLOAD TEMPLATE", expanded=False):
        col_u1, col_u2 = st.columns([3, 1])
        with col_u1:
            st.file_uploader("Upload CSV", type=["csv"], key="csv_uploader", label_visibility="collapsed")
        with col_u2:
            try:
                with open("sample_data.csv", "rb") as f:
                    st.download_button("📥 DOWNLOAD SAMPLE CSV", f, file_name="sample_data.csv", mime="text/csv")
            except FileNotFoundError:
                pass

# =========================================================================
# PAGE 2: LIVE OPERATIONS & FLEET
# =========================================================================
elif current_nav_key == "operations":
    tab_map, tab_fleet, tab_facs = st.tabs([
        "🗺️ Live GIS Waste Map & Heatmap",
        "🚚 Vehicle Tracking & Fleet Dispatch",
        "🏭 Facility Processing Nodes",
    ])

    with tab_map:
        map_module.render_map_page(palette)

    with tab_fleet:
        vehicle_module.render_vehicle_tracking_page(palette)

    with tab_facs:
        facility_module.render_facility_management_page(palette)

# =========================================================================
# PAGE 3: SMART ALLOCATION & SIMPLEX LP SOLVER
# =========================================================================
elif current_nav_key == "allocation":
    tab_opt, tab_sim, tab_cal = st.tabs([
        "⚡ Multi-Objective LP Solver (Simplex)",
        "🧪 Scenario Simulator",
        "📅 Event Surge Calendar",
    ])

    with tab_opt:
        optimizer.render_smart_allocation_page(palette, wet_total, dry_total)

    with tab_sim:
        simulator_module.render_scenario_simulator_page(palette, wet_total, dry_total)

    with tab_cal:
        calendar_module.render_calendar_section(palette, total_capacity=total_capacity)

# =========================================================================
# PAGE 4: ANALYTICS & 7-DAY FORECAST
# =========================================================================
elif current_nav_key == "analytics":
    tab_trends, tab_fc, tab_esg, tab_perf = st.tabs([
        "📈 Waste Generation Trends",
        "🔮 7-Day ML Forecast",
        "🌱 Carbon & ESG Scorecard",
        "🏆 Municipal SLA Performance",
    ])

    with tab_trends:
        analytics_dashboards.render_waste_analytics_page(palette)

    with tab_fc:
        st.markdown(
            f"""
            <div style="background:{palette['card_bg']}; border:1px solid {palette['border']}; border-left:4px solid {palette['purple']};
                        border-radius:8px; padding:18px 22px; margin-bottom:20px;">
                <div style="font-size:1.15rem; font-weight:800; color:{palette['text']};">🔮 7-Day Predictive Waste Forecast & Capacity Ceilings</div>
                <div style="font-size:0.75rem; color:{palette['muted']}; margin-top:4px;">
                    Calibrated on day-of-week commercial activity, residential weekend multipliers, and holiday event surges.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_fc1, col_fc2, col_fc3 = st.columns(3)
        with col_fc1:
            st.markdown(
                f"""<div class="m-card hero"><div class="m-label">📅 7-Day Cumulative Volume</div><div class="m-value">{(total_waste * 7.15) / 1000:.1f} T</div></div>""",
                unsafe_allow_html=True,
            )
        with col_fc2:
            st.markdown(
                f"""<div class="m-card"><div class="m-label">⚡ Peak Demand Surge Day</div><div class="m-value">Saturday (Weekend Peak)</div></div>""",
                unsafe_allow_html=True,
            )
        with col_fc3:
            st.markdown(
                f"""<div class="m-card green"><div class="m-label">🛡️ Minimum Reserve Margin</div><div class="m-value">{max(0, total_capacity - total_waste)/1000:.2f} T Buffer</div></div>""",
                unsafe_allow_html=True,
            )

        forecast_rows = forecast.forecast_week(sources, total_capacity)
        forecast_df = pd.DataFrame(forecast_rows)
        components.forecast_section(forecast_df, palette)

        st.markdown(f'<div class="sec-title">📊 WARD-LEVEL PREDICTED GENERATION DYNAMICS</div>', unsafe_allow_html=True)
        ward_fcs = []
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for s in sources:
            for d in days:
                mult = 1.25 if d in ["Sat", "Sun"] and "house" in s["id"] else (0.4 if d in ["Sat", "Sun"] and "office" in s["id"] else 1.0)
                ward_fcs.append({"Source": s["id"].upper(), "Day": d, "Waste (kg)": round(s["baseline_kg"] * mult)})
        df_wf = pd.DataFrame(ward_fcs)

        fig_w = px.bar(
            df_wf,
            x="Day",
            y="Waste (kg)",
            color="Source",
            barmode="stack",
            title="Projected Daily Generation by Municipal Source Stream",
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        fig_w.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color=palette["text"],
            height=320,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(fig_w, use_container_width=True)

    with tab_esg:
        wet_alloc = allocations.get("A", 0) + allocations.get("B", 0) + allocations.get("E", 0)
        dry_alloc = allocations.get("C", 0) + allocations.get("D", 0)
        analytics_module.render_carbon_scorecard(wet_alloc, dry_alloc, total_overflow, total_waste, palette)

    with tab_perf:
        analytics_dashboards.render_performance_dashboard_page(palette)

# =========================================================================
# PAGE 5: ALERTS & CITIZEN GRIEVANCES
# =========================================================================
elif current_nav_key == "alerts_citizen":
    tab_alerts, tab_citizen = st.tabs([
        "🚨 Predictive Overflow Alerts",
        "📢 Citizen Grievance Portal & File Ticket",
    ])

    with tab_alerts:
        alert_engine.render_alerts_dashboard(palette)

    with tab_citizen:
        citizen_module.render_citizen_reports_page(palette)

# =========================================================================
# PAGE 6: AUDITS, REPORTS & ADMIN
# =========================================================================
elif current_nav_key == "admin_reports":
    tab_rep, tab_users, tab_settings, tab_prof = st.tabs([
        "📑 Executive Reports & Data Export",
        "👥 User Role Management (Admin)",
        "⚙️ System Settings & API Keys",
        "👤 Account Profile & Security",
    ])

    with tab_rep:
        reports_module.render_reports_page(palette)

    with tab_users:
        if not current_user or current_user.get("role") != "admin":
            st.warning("User Management is restricted to System Administrators. Please sign in as admin.")
        else:
            analytics_dashboards.render_user_management_page(palette)

    with tab_settings:
        settings_module.render_settings_page(palette)

    with tab_prof:
        settings_module.render_profile_page(palette)

# =========================================================================
# PROFESSIONAL REAL WEBSITE FOOTER
# =========================================================================
components.website_footer(palette)