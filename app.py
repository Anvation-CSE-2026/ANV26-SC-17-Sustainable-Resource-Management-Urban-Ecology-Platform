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
    "nav_selection": "home",
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

# Handle navigation via query params (e.g. ?nav=maps, ?nav=services, ?nav=settings)
req_nav = st.query_params.get("nav")
if req_nav:
    if "nav" in st.query_params:
        del st.query_params["nav"]
    nav_map_aliases = {
        "maps": "map",
        "gis": "map",
        "live_maps": "map",
        "overview": "home",
        "dashboard": "home",
        "fleet": "fleet_ops",
        "citizen": "citizen_ops",
    }
    st.session_state["nav_selection"] = nav_map_aliases.get(req_nav, req_nav)

if st.query_params.get("alert_nav") == "1":
    st.session_state["nav_selection"] = "alerts"
    if "alert_nav" in st.query_params:
        del st.query_params["alert_nav"]

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


# =========================================================================
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
active_trucks_count = len([v for v in db.get_all_vehicles() if v.get("status") in ["available", "in_transit", "assigned"]])

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

# 6. Current User and 5-Tenant Respective Sidebar Navigation
current_user = auth.get_current_user()
user_role = current_user.get("role") if current_user else None

# Core Base Navigation matching the hand-drawn wireframe
BASE_NAV = [
    ("🏠 Home", "home"),
    ("🛠️ Services", "services"),
    ("📅 Events", "events"),
    ("🗺️ Live Maps", "map"),
    ("🚨 Alerts", "alerts"),
]

# Build Respective Sidebar for Each of the 5 Tenants (Settings included in sidebar before logout)
if user_role in ["state", "state_authority"]:
    TENANT_NAV = BASE_NAV + [
        ("🏛️ State Policy", "state_policy"),
        ("📊 Statewide Reports", "reports"),
        ("⚙️ Settings", "settings"),
    ]
elif user_role == "commissioner":
    TENANT_NAV = BASE_NAV + [
        ("⚖️ Reallocation LP", "allocation_exec"),
        ("📈 Executive KPIs", "kpis_exec"),
        ("⚙️ Settings", "settings"),
    ]
elif user_role in ["waste_officer", "municipality"]:
    TENANT_NAV = BASE_NAV + [
        ("🚛 Fleet Telematics", "fleet_ops"),
        ("🗳️ Citizen Grievances", "citizen_ops"),
        ("⚙️ Settings", "settings"),
    ]
elif user_role in ["zonal_officer", "district"]:
    TENANT_NAV = BASE_NAV + [
        ("📍 Ward Blackspots", "ward_spots"),
        ("👥 Citizen Reports", "citizen_zonal"),
        ("⚙️ Settings", "settings"),
    ]
elif user_role in ["processing_facility", "recycling_facility", "factory"]:
    TENANT_NAV = BASE_NAV + [
        ("🏭 Plant Inflow", "plant_inflow"),
        ("♻️ Material Recovery", "recycling_ops"),
        ("⚙️ Settings", "settings"),
    ]
elif user_role == "admin":
    TENANT_NAV = BASE_NAV + [
        ("🛡️ User Governance", "users"),
        ("🧪 Simulator Sandbox", "simulator"),
        ("📑 Reports", "reports"),
        ("⚙️ Settings", "settings"),
    ]
else:
    # Public / Guest Visitor Navigation
    TENANT_NAV = BASE_NAV + [
        ("⚙️ Settings", "settings"),
    ]

# Map legacy nav keys if present
legacy_map = {
    "overview": "home",
    "operations": "map",
    "allocation": "services",
    "analytics": "reports",
    "alerts_citizen": "alerts",
    "admin_reports": "reports",
}
if st.session_state.nav_selection in legacy_map:
    st.session_state.nav_selection = legacy_map[st.session_state.nav_selection]

# 7. Left Sidebar Construction matching user hand-drawn wireframe
with st.sidebar:
    # Sidebar Header Brand
    logo_uri = theme.get_logo_data_uri()
    render_html(
        f"""
        <div style="display:flex; align-items:center; gap:12px; padding:6px 0 16px 0; border-bottom:1px solid {palette['border']}; margin-bottom:16px;">
            <img src="{logo_uri}" alt="WasteGrid Logo" style="width:42px; height:42px; object-fit:contain; filter:drop-shadow(0 2px 6px rgba(0,0,0,0.18));" />
            <div>
                <div style="font-size:1.24rem; font-weight:900; color:{palette['text']}; letter-spacing:-0.02em;">WasteGrid</div>
                <div style="font-size:0.65rem; color:{palette['muted']}; letter-spacing:0.12em; text-transform:uppercase; font-weight:700;">Predict. Detect. Allocate.</div>
            </div>
        </div>
        """
    )

    # Active Tenant Badge if logged in
    if current_user:
        u_fname = current_user.get("full_name") or current_user.get("username") or "Officer"
        u_role_title = current_user.get("authority_title") or str(current_user.get("role", "Authority")).title()
        render_html(
            f"""
            <div style="background:{palette['bg_soft']}; border:1px solid {palette['border']}; border-radius:8px; padding:10px 12px; margin-bottom:14px; font-size:0.75rem;">
                <div style="font-weight:700; color:{palette['text']}; display:flex; align-items:center; gap:6px;">
                    <span>👤</span> <span>{u_fname}</span>
                </div>
                <div style="font-size:0.68rem; color:{palette['blue']}; font-weight:700; text-transform:uppercase; margin-top:3px;">
                    {u_role_title}
                </div>
            </div>
            """
        )

    # Clean Sidebar Navigation Buttons: Icon on Left, Name on Right, NO RADIO DOTS!
    for label, nav_key in TENANT_NAV:
        is_active = (st.session_state.nav_selection == nav_key)
        if st.button(
            label,
            key=f"sb_nav_btn_{nav_key}",
            type="primary" if is_active else "secondary",
            use_container_width=True,
        ):
            st.session_state.nav_selection = nav_key
            st.rerun()

    # Bottom of Sidebar: Logout Icon with Logout under it, and NOTHING ELSE AFTER IT!
    st.markdown(
        f"<div style='margin-top:42px; padding-top:16px; border-top:1px solid {palette['border']}; text-align:center;'></div>",
        unsafe_allow_html=True,
    )
    if current_user:
        if st.button("🚪\n\nLogout", key="btn_sb_logout_bottom", use_container_width=True, help="Sign out of WasteGrid"):
            auth.logout()
    else:
        if st.button("🔑\n\nSign In", key="btn_sb_signin_bottom", use_container_width=True, help="Open Authority Sign In / Sign Up"):
            st.session_state["show_auth_modal"] = True
            st.rerun()

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
    alert_count=pending_alert_count,
)

current_nav_key = st.session_state.get("nav_selection", "home")

# =========================================================================
# PAGE 1: HOME AUTHORITY DASHBOARD (INSPIRED BY WIREFRAME LAYOUT)
# =========================================================================
if current_nav_key in ["home", "overview"]:
    # 1. Executive Status / Welcome Banner
    if current_user:
        u_name = current_user.get("full_name") or current_user.get("username") or "Authorized Officer"
        u_role_text = current_user.get("authority_title") or "Municipal Authority"
        u_juris = current_user.get("jurisdiction") or "City Operations"
        render_html(
            f"""
            <div style="background:linear-gradient(135deg, rgba(2, 132, 199, 0.08) 0%, rgba(16, 185, 129, 0.08) 100%); 
                        border:1px solid rgba(2, 132, 199, 0.25); border-radius:10px; padding:12px 18px; margin-bottom:20px; 
                        display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:1.3rem;">📍</span>
                    <div>
                        <div style="font-size:0.85rem; font-weight:800; color:{palette['text']};">
                            WasteGrid Municipal Authority Operations Command Center
                        </div>
                        <div style="font-size:0.74rem; color:{palette['muted']}; margin-top:2px;">
                            Logged in as <b>{u_name}</b> ({u_role_text}) · Scope: <b>{u_juris}</b>
                        </div>
                    </div>
                </div>
                <span style="font-size:0.68rem; font-weight:700; background:rgba(16,185,129,0.15); color:{palette['success']}; border:1px solid rgba(16,185,129,0.3); padding:4px 10px; border-radius:999px; text-transform:uppercase;">
                    ● Live Grid Authenticated
                </span>
            </div>
            """
        )
    else:
        render_html(
            f"""
            <div style="background:linear-gradient(135deg, rgba(2, 132, 199, 0.08) 0%, rgba(16, 185, 129, 0.08) 100%); 
                        border:1px solid rgba(2, 132, 199, 0.25); border-radius:10px; padding:12px 18px; margin-bottom:20px; 
                        display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div style="display:flex; align-items:center; gap:10px;">
                    <span style="font-size:1.3rem;">🏛️</span>
                    <div>
                        <div style="font-size:0.85rem; font-weight:800; color:{palette['text']};">
                            WasteGrid — Smart Municipal Solid-Waste Management Platform
                        </div>
                        <div style="font-size:0.74rem; color:{palette['muted']}; margin-top:2px;">
                            Predict. Detect. Allocate. · Official 5-Tenant Authority System
                        </div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:0.72rem; color:{palette['muted']};">Click the Profile icon <b>(P)</b> at the top-right to sign into your authority tenant dashboard.</span>
                </div>
            </div>
            """
        )

    # Dedicated Role-Specific Dashboard for Each of the 6 Official Authority Logins
    if current_user:
        user_role = current_user.get("role", "municipality")
        if user_role == "admin":
            analytics_module.render_super_admin_view(palette, active_facilities, allocations, pending_alert_count)
        elif user_role in ["state", "state_authority"]:
            analytics_module.render_state_authority_view(palette)
        elif user_role == "commissioner":
            analytics_module.render_commissioner_view(palette, pending_alert_count)
        elif user_role in ["waste_officer", "municipality"]:
            analytics_module.render_waste_officer_view(palette, pending_alert_count)
        elif user_role in ["zonal_officer", "district"]:
            analytics_module.render_zonal_officer_view(palette)
        elif user_role in ["processing_facility", "factory"]:
            analytics_module.render_processing_facility_view(active_facilities, allocations, palette)
        elif user_role == "recycling_facility":
            analytics_module.render_recycling_facility_view(active_facilities, allocations, palette)
        else:
            analytics_module.render_municipal_office_view(palette, pending_alert_count)

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

    # 11. Live Maps & Predictive Alerts Split Grid (Inspired by Hand-Drawn Layout)
    st.markdown("<br>", unsafe_allow_html=True)
    components.section_title("OPERATIONAL DISPATCH: GIS MAP NODES & PREDICTIVE ALERTS")
    col_hm_map, col_hm_alert = st.columns(2)
    with col_hm_map:
        st.markdown(
            f"""
            <div style="background:{palette['card_bg']}; border:1px solid {palette['border']}; border-radius:12px; padding:18px; box-shadow:{palette['shadow']};">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div style="font-size:1.05rem; font-weight:800; color:{palette['text']};">🗺️ Live GIS Facilities & Fleet</div>
                    <span style="font-size:0.7rem; color:{palette['success']}; font-weight:700;">● {active_trucks_count} Fleet Online</span>
                </div>
                <div style="font-size:0.8rem; color:{palette['muted']}; margin-bottom:12px;">
                    Real-time GPS telemetry from 5 processing nodes (A-E) and municipal compactor units with automated weighbridge logging.
                </div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:16px;">
                    <div style="background:{palette['bg_soft']}; padding:8px 12px; border-radius:6px; font-size:0.75rem;">
                        <b>Biocompost A:</b> {allocations.get('A', 0):,.0f} kg
                    </div>
                    <div style="background:{palette['bg_soft']}; padding:8px 12px; border-radius:6px; font-size:0.75rem;">
                        <b>Digester B:</b> {allocations.get('B', 0):,.0f} kg
                    </div>
                    <div style="background:{palette['bg_soft']}; padding:8px 12px; border-radius:6px; font-size:0.75rem;">
                        <b>MRF C:</b> {allocations.get('C', 0):,.0f} kg
                    </div>
                    <div style="background:{palette['bg_soft']}; padding:8px 12px; border-radius:6px; font-size:0.75rem;">
                        <b>Energy Plant D:</b> {allocations.get('D', 0):,.0f} kg
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🗺️ Open Interactive Live Map ➔", key="btn_home_goto_map", use_container_width=True):
            st.session_state["nav_selection"] = "map"
            st.rerun()

    with col_hm_alert:
        st.markdown(
            f"""
            <div style="background:{palette['card_bg']}; border:1px solid {palette['border']}; border-radius:12px; padding:18px; box-shadow:{palette['shadow']};">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div style="font-size:1.05rem; font-weight:800; color:{palette['text']};">🚨 Predictive Alerts & Incidents</div>
                    <span style="font-size:0.7rem; color:{palette['accent'] if pending_alert_count>0 else palette['success']}; font-weight:700;">
                        {pending_alert_count} Pending
                    </span>
                </div>
                <div style="font-size:0.8rem; color:{palette['muted']}; margin-bottom:12px;">
                    Active automated early-warning telemetry tracking capacity limits, offline plant contingencies, and citizen tickets.
                </div>
                <div style="background:{'rgba(239,68,68,0.08)' if pending_alert_count>0 else 'rgba(16,185,129,0.08)'}; border:1px solid {'rgba(239,68,68,0.25)' if pending_alert_count>0 else 'rgba(16,185,129,0.25)'}; border-radius:8px; padding:10px 14px; margin-bottom:16px; font-size:0.78rem;">
                    <b>Status:</b> {'⚠️ Action Required: Pending load rebalance' if pending_alert_count>0 else '✅ Optimal Operations: Zero active emergency bottlenecks'}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🚨 Open Incident & Grievance Alerts ➔", key="btn_home_goto_alerts", use_container_width=True):
            st.session_state["nav_selection"] = "alerts"
            st.rerun()

    # 12. Data Ingestion Drawer
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
# PAGE 2: SERVICES & SMART LP ALLOCATION
# =========================================================================
elif current_nav_key in ["services", "allocation"]:
    tab_opt, tab_esg, tab_sim, tab_facs = st.tabs([
        "⚡ Multi-Objective LP Solver (Simplex)",
        "🌱 Carbon & ESG Scorecard",
        "🧪 Scenario Simulator Sandbox",
        "🏭 Facility Processing Nodes",
    ])

    with tab_opt:
        optimizer.render_smart_allocation_page(palette, wet_total, dry_total)

    with tab_esg:
        wet_alloc = allocations.get("A", 0) + allocations.get("B", 0) + allocations.get("E", 0)
        dry_alloc = allocations.get("C", 0) + allocations.get("D", 0)
        analytics_module.render_carbon_scorecard(wet_alloc, dry_alloc, total_overflow, total_waste, palette)

    with tab_sim:
        simulator_module.render_scenario_simulator_page(palette, wet_total, dry_total)

    with tab_facs:
        facility_module.render_facility_management_page(palette)

# =========================================================================
# PAGE 3: EVENTS & HOLIDAY SURGE CALENDAR
# =========================================================================
elif current_nav_key == "events":
    tab_cal, tab_fc, tab_trends = st.tabs([
        "📅 Municipal Event Calendar & Surge Register",
        "🔮 7-Day ML Forecast & Trend Dynamics",
        "📊 Ward-Level Generation Patterns",
    ])

    with tab_cal:
        calendar_module.render_calendar_section(palette, total_capacity=total_capacity)

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

    with tab_trends:
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

# =========================================================================
# PAGE 4: LIVE MAP & FLEET TELEMATICS
# =========================================================================
elif current_nav_key in ["map", "operations"]:
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
elif current_nav_key in ["alerts", "alerts_citizen"]:
    tab_alerts, tab_citizen = st.tabs([
        "🚨 Predictive Overflow Alerts",
        "📢 Citizen Grievance Portal & File Ticket",
    ])

    with tab_alerts:
        alert_engine.render_alerts_dashboard(palette)

    with tab_citizen:
        citizen_module.render_citizen_reports_page(palette)

# =========================================================================
# PAGE 6: AUDITS, REPORTS & PERFORMANCE
# =========================================================================
elif current_nav_key in ["reports", "admin_reports"]:
    tab_rep, tab_trends, tab_perf = st.tabs([
        "📑 Executive Reports & Excel Export",
        "📈 Waste Generation Trends & Analytics",
        "🏆 Municipal SLA Performance",
    ])

    with tab_rep:
        reports_module.render_reports_page(palette)

    with tab_trends:
        analytics_dashboards.render_waste_analytics_page(palette)

    with tab_perf:
        analytics_dashboards.render_performance_dashboard_page(palette)

# =========================================================================
# PAGE 7: SETTINGS & GOVERNANCE
# =========================================================================
elif current_nav_key == "settings":
    tabs_list = [
        "⚙️ System Settings & Telemetry API",
        "👤 Account Profile & Security",
    ]
    if current_user and current_user.get("role") == "admin":
        tabs_list.append("👥 User Role Management (Admin)")

    st_tabs = st.tabs(tabs_list)
    with st_tabs[0]:
        settings_module.render_settings_page(palette)
    with st_tabs[1]:
        settings_module.render_profile_page(palette)
    if current_user and current_user.get("role") == "admin":
        with st_tabs[2]:
            analytics_dashboards.render_user_management_page(palette)

# =========================================================================
# TENANT-SPECIFIC CONSOLES
# =========================================================================
elif current_nav_key == "state_policy":
    analytics_module.render_state_authority_view(palette)
    wet_alloc = allocations.get("A", 0) + allocations.get("B", 0) + allocations.get("E", 0)
    dry_alloc = allocations.get("C", 0) + allocations.get("D", 0)
    analytics_module.render_carbon_scorecard(wet_alloc, dry_alloc, total_overflow, total_waste, palette)

elif current_nav_key == "allocation_exec":
    optimizer.render_smart_allocation_page(palette, wet_total, dry_total)

elif current_nav_key == "kpis_exec":
    analytics_dashboards.render_performance_dashboard_page(palette)

elif current_nav_key == "fleet_ops":
    vehicle_module.render_vehicle_tracking_page(palette)

elif current_nav_key in ["citizen_ops", "citizen_zonal"]:
    citizen_module.render_citizen_reports_page(palette)

elif current_nav_key == "ward_spots":
    analytics_module.render_zonal_officer_view(palette)
    alert_engine.render_alerts_dashboard(palette)

elif current_nav_key == "plant_inflow":
    facility_module.render_facility_management_page(palette)

elif current_nav_key == "recycling_ops":
    analytics_module.render_recycling_facility_view(active_facilities, allocations, palette)

elif current_nav_key == "users":
    analytics_dashboards.render_user_management_page(palette)

elif current_nav_key == "simulator":
    simulator_module.render_scenario_simulator_page(palette, wet_total, dry_total)

# =========================================================================
# PAGE 8: LOGOUT
# =========================================================================
elif current_nav_key == "logout":
    auth.logout()

# =========================================================================
# PROFESSIONAL REAL WEBSITE FOOTER
# =========================================================================
components.website_footer(palette)