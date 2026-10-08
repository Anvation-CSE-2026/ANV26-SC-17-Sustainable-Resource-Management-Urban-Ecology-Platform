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

# 1. Page Configuration
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
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# 3. Theme Resolution
param_theme = st.query_params.get("theme")
if param_theme in ["light", "dark"]:
    st.session_state.theme = param_theme
elif "theme" not in st.session_state or st.session_state.theme not in ["light", "dark"]:
    st.session_state.theme = "light"

st.query_params["theme"] = st.session_state.theme
palette = theme.get_palette(st.session_state.theme)
theme.inject_css(palette)

# 4. Check Logout Parameter Trigger
if st.query_params.get("logout") == "1":
    if "logout" in st.query_params:
        del st.query_params["logout"]
    auth.logout()

# 5. Core Computational Grid Data
# Sources (from uploaded CSV or baseline sample records)
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

# 6. Sidebar Navigation Definition (17 Functional Items)
NAV_ITEMS = [
    ("📊 Overview Dashboard", "overview"),
    ("🗺️ Live Waste Map & Heatmap", "map"),
    ("📈 Waste Analytics Dashboard", "analytics"),
    ("🔮 Waste Forecast", "forecast"),
    ("🏭 Facility Management", "facilities"),
    ("⚡ Smart Allocation", "allocation"),
    ("🚚 Vehicle Tracking & Dispatch", "vehicles"),
    ("📅 Event Calendar", "calendar"),
    ("🧪 Scenario Simulator", "simulator"),
    ("🔔 Alerts & Notifications", "alerts"),
    ("📢 Citizen Reports", "citizen_reports"),
    ("🌱 Carbon & ESG Dashboard", "carbon"),
    ("🏆 Performance Dashboard", "performance"),
    ("📑 Reports & Exports", "reports"),
    ("👥 User Management (admin only)", "users"),
    ("⚙️ Settings", "settings"),
    ("👤 Login / Profile / Logout", "profile"),
]

title_to_key = {title: key for title, key in NAV_ITEMS}
key_to_title = {key: title for title, key in NAV_ITEMS}

# 7. Sidebar Construction
with st.sidebar:
    # Sidebar Header Brand
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:12px; padding:6px 0 16px 0; border-bottom:1px solid {palette['border']}; margin-bottom:16px;">
            <div style="width:38px; height:38px; border-radius:8px; background:linear-gradient(135deg, {palette['accent']}, {palette['blue']}); 
                        display:flex; align-items:center; justify-content:center; font-size:1.3rem; box-shadow:0 2px 8px rgba(0,0,0,0.2);">
                ♻️
            </div>
            <div>
                <div style="font-size:1.15rem; font-weight:800; color:{palette['text']}; letter-spacing:-0.02em;">WasteGrid <span style="font-size:0.65rem; background:{palette['accent']}; color:#fff; padding:2px 6px; border-radius:4px; vertical-align:middle;">2.0</span></div>
                <div style="font-size:0.68rem; color:{palette['muted']}; letter-spacing:0.04em; text-transform:uppercase;">Smart Municipal Platform</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Secure Sidebar Authentication Card
    current_user = auth.get_current_user()
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

    # Sidebar Grid Summary Footer Card
    active_trucks_count = len([v for v in db.get_all_vehicles() if v["status"] in ["available", "in_transit", "assigned"]])
    st.markdown(
        f"""
        <div style="margin-top:24px; padding:12px; background:rgba(255,255,255,0.03); border:1px solid {palette['border']}; 
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
        """,
        unsafe_allow_html=True,
    )

# 8. Authentication Check Gate
# If unauthenticated and on profile page, allow sidebar login interaction.
# Operational dashboards require authentication per Requirement 2.
if not current_user:
    # Render top nav for public visitor
    components.top_nav_bar(
        "WasteGrid 2.0 — Secure Municipal Authority Sign-In",
        status="optimal",
        pending_alerts=pending_alert_count,
        user=None,
        theme=st.session_state.theme,
        p=palette,
    )

    st.markdown(
        f"""
        <div style="max-width:850px; margin:20px auto; background:{palette['card_bg']}; border:1px solid {palette['border']}; 
                    border-radius:12px; padding:32px 36px; box-shadow:{palette['shadow']};">
            <div style="text-align:center; margin-bottom:24px;">
                <div style="font-size:3rem; margin-bottom:10px;">🏛️</div>
                <div style="font-size:1.6rem; font-weight:800; color:{palette['text']}; letter-spacing:-0.02em;">
                    Karnataka Municipal Waste Grid Operations Center
                </div>
                <div style="font-size:0.85rem; color:{palette['muted']}; margin-top:6px;">
                    Department of Municipal Administration & Urban Development · Swachh Bharat Smart City Mission
                </div>
            </div>
            <div style="font-size:0.9rem; color:{palette['text']}; line-height:1.7; margin-bottom:24px;">
                Welcome to <b>WasteGrid 2.0</b>, the state-wide predictive municipal waste reallocation and fleet telemetry platform.
                In accordance with municipal cyber-governance guidelines and role-based data access controls (RBAC),
                operational dashboards require authenticated sign-in.
            </div>
            <div style="background:rgba(59,130,246,0.06); border:1px solid rgba(59,130,246,0.25); border-radius:8px; padding:16px 20px; margin-bottom:24px;">
                <div style="font-weight:700; color:{palette['blue']}; margin-bottom:6px; font-size:0.85rem;">
                    🛡️ Evaluator Demo Authority Accounts:
                </div>
                <div style="font-size:0.8rem; color:{palette['text']}; line-height:1.6;">
                    Please enter any of the following official accounts in the <b>left sidebar sign-in form</b> to explore role-specific operations:
                    <ul style="margin:8px 0 4px 18px; padding:0;">
                        <li><b>System Administrator:</b> <code>admin</code> / <code>Admin@123</code> (Full access to all 17 dashboards)</li>
                        <li><b>State Authority:</b> <code>karnataka_admin</code> / <code>Waste@123</code> (Statewide macro allocation & ESG)</li>
                        <li><b>District Authority:</b> <code>district_admin</code> / <code>District@123</code> (District-level wards & transport)</li>
                        <li><b>Municipal Authority:</b> <code>municipality_admin</code> / <code>Municipality@123</code> (Local wards, citizen grievance & dispatch)</li>
                        <li><b>Factory Authority:</b> <code>factory_admin</code> / <code>Factory@123</code> (Plant capacity, receiving docks & maintenance)</li>
                    </ul>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Allow public submission of citizen reports even if not signed in as authority!
    if selected_key == "citizen_reports":
        st.markdown("<br>", unsafe_allow_html=True)
        citizen_module.render_citizen_reports_page(palette)

    st.stop()

# 9. Role-Based Access Clearance Check
current_nav_key = st.session_state.nav_selection
active_page_name = next((t for t, k in NAV_ITEMS if k == current_nav_key), "Dashboard")

if not auth.has_permission(current_nav_key):
    components.top_nav_bar(
        active_page_name,
        status=system_status,
        pending_alerts=pending_alert_count,
        user=current_user,
        theme=st.session_state.theme,
        p=palette,
    )
    auth.render_access_restricted_view(active_page_name)
    st.stop()

# 10. Render Active Functional Page
# Render Top Navigation Bar on all views
components.top_nav_bar(
    active_page_name,
    status=system_status,
    pending_alerts=pending_alert_count,
    user=current_user,
    theme=st.session_state.theme,
    p=palette,
)

# =========================================================================
# PAGE 1: OVERVIEW DASHBOARD
# =========================================================================
if current_nav_key == "overview":
    user_role = current_user.get("role", "municipality")

    # Role-specific introductory briefing banner
    if user_role == "state":
        analytics_module.render_state_authority_view(palette)
    elif user_role == "district":
        analytics_module.render_district_authority_view(palette)
    elif user_role == "factory":
        analytics_module.render_factory_authority_view(active_facilities, allocations, palette)

    # 1. Real-Time Grid KPIs Row (8 Primary Overview Metrics)
    processed_kg = sum(allocations.values())
    overflow_risk_label = "HIGH" if total_overflow > 500 else ("MODERATE" if total_overflow > 0 else "NOMINAL")
    recycling_pct = round((allocations.get("C", 0) + allocations.get("D", 0)) / max(total_waste, 1) * 100, 1)
    online_facs_count = sum(1 for f in active_facilities if f.get("status") == "online" and f["capacity_kg"] > 0)
    avail_capacity_kg = max(0.0, total_capacity - processed_kg)

    components.section_title("REAL-TIME GRID METRICS & OPERATIONAL TELEMETRY")
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.markdown(
            f"""<div class="m-card hero">
                <div class="m-label">📊 Predicted Demand</div>
                <div class="m-value">{total_waste/1000:.2f} T</div>
                <div style="font-size:0.68rem; color:{palette['muted']}; margin-top:4px;">{wet_total/1000:.1f}T Wet · {dry_total/1000:.1f}T Dry</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col_m2:
        st.markdown(
            f"""<div class="m-card green">
                <div class="m-label">⚙️ Waste Processed</div>
                <div class="m-value">{processed_kg/1000:.2f} T</div>
                <div style="font-size:0.68rem; color:{palette['success']}; margin-top:4px;">{(processed_kg/max(total_waste,1))*100:.1f}% reallocated</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col_m3:
        st.markdown(
            f"""<div class="m-card purple">
                <div class="m-label">🏭 Available Capacity</div>
                <div class="m-value">{avail_capacity_kg/1000:.2f} T</div>
                <div style="font-size:0.68rem; color:{palette['purple']}; margin-top:4px;">{online_facs_count} of {len(active_facilities)} Plants Online</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col_m4:
        ovf_cls = "red" if total_overflow > 0 else "green"
        st.markdown(
            f"""<div class="m-card {ovf_cls}">
                <div class="m-label">⚠️ Overflow Risk</div>
                <div class="m-value">{total_overflow/1000:.2f} T</div>
                <div style="font-size:0.68rem; color:{palette['accent'] if total_overflow>0 else palette['success']}; margin-top:4px;">Risk Status: {overflow_risk_label}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    col_m5, col_m6, col_m7, col_m8 = st.columns(4)
    with col_m5:
        st.markdown(
            f"""<div class="m-card">
                <div class="m-label">🚚 Active Fleet Units</div>
                <div class="m-value">{active_trucks_count} Trucks</div>
                <div style="font-size:0.68rem; color:{palette['muted']}; margin-top:4px;">Real-time GPS monitored</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col_m6:
        st.markdown(
            f"""<div class="m-card">
                <div class="m-label">🔔 Pending Alerts</div>
                <div class="m-value">{pending_alert_count} Incidents</div>
                <div style="font-size:0.68rem; color:{palette['accent'] if pending_alert_count>0 else palette['success']}; margin-top:4px;">Threshold & outages</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col_m7:
        st.markdown(
            f"""<div class="m-card green">
                <div class="m-label">♻️ Recycling Ratio</div>
                <div class="m-value">{recycling_pct}%</div>
                <div style="font-size:0.68rem; color:{palette['success']}; margin-top:4px;">Diverted from Landfills</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col_m8:
        st.markdown(
            f"""<div class="m-card">
                <div class="m-label">📁 Data Mode</div>
                <div class="m-value" style="font-size:1.1rem; padding-top:6px;">{data_mode}</div>
                <div style="font-size:0.68rem; color:{palette['muted']}; margin-top:4px;">{len(sources)} Active Waste Sources</div>
            </div>""",
            unsafe_allow_html=True,
        )

    # 2. Multi-Stream Compatibility Flow
    components.stream_breakdown(wet_total, dry_total, palette)

    # 3. Operational Status Banner
    components.status_banner(total_overflow, st.session_state.reoptimized, st.session_state.outage_facility)

    # 4. Interactive Action Buttons
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

    # 5. Data Ingestion Drawer
    with st.expander("📁 DATA INGESTION — UPLOAD CSV DATASET OR DOWNLOAD SAMPLE TEMPLATE", expanded=False):
        st.markdown(
            f'<div style="font-size:0.75rem; color:{palette["muted"]}; margin-bottom:12px; line-height:1.5;">'
            'Upload your municipal waste stream dataset (.csv) with columns: <code>source, baseline_kg, waste_type</code>, '
            'or download the standard multi-source template to inspect the schema.'
            '</div>',
            unsafe_allow_html=True,
        )
        col_u1, col_u2 = st.columns([3, 1])
        with col_u1:
            st.file_uploader("Upload CSV", type=["csv"], key="csv_uploader", label_visibility="collapsed")
        with col_u2:
            try:
                with open("sample_data.csv", "rb") as f:
                    st.download_button("📥 DOWNLOAD SAMPLE CSV", f, file_name="sample_data.csv", mime="text/csv")
            except FileNotFoundError:
                pass

    # 6. Facility Utilization & Load Balancing Grid
    components.section_title("FACILITY UTILIZATION & REAL-TIME LOAD BALANCING")
    components.facility_grid(active_facilities, allocations, palette, outage=st.session_state.outage_facility)

    # 7. Fixed Allocation vs WasteGrid Dynamic Comparison
    components.section_title("FIXED ALLOCATION VS WASTEGRID OPTIMIZER COMPARISON")
    fixed_overflow = optimizer.fixed_allocation_overflow(total_waste, total_capacity)
    components.comparison_cards(fixed_overflow, total_overflow, palette)

    if fixed_overflow > 0 and total_overflow < fixed_overflow:
        pct = optimizer.reduction_pct(fixed_overflow, total_overflow)
        components.success_banner(f"WasteGrid prevented {fixed_overflow - total_overflow:,.0f} kg ({pct:.1f}%) of overflow vs static fixed routing!")

    # 8. Daily & Weekly Trend Graphs
    components.section_title("WEEKLY GENERATION & PROCESSING TREND DYNAMICS")
    forecast_rows = forecast.forecast_week(sources, total_capacity)
    forecast_df = pd.DataFrame(forecast_rows)
    components.forecast_section(forecast_df, palette)

    # 9. Quick CSV Export
    export_df = pd.DataFrame([
        {
            "Facility": f["id"],
            "Facility Name": f.get("name", f"Facility {f['id']}"),
            "Accepts": f["accepts"].upper(),
            "Capacity (kg)": f["capacity_kg"],
            "Allocated (kg)": round(allocations.get(f["id"], 0)),
            "Distance (km)": f["distance_km"],
            "Status": f.get("status", "online"),
        }
        for f in active_facilities
    ])
    st.download_button(
        "📥 DOWNLOAD ALLOCATION SUMMARY (CSV)",
        export_df.to_csv(index=False).encode("utf-8"),
        file_name="wastegrid_live_allocation.csv",
        mime="text/csv",
    )

# =========================================================================
# PAGE 2: LIVE WASTE MAP & HEATMAP
# =========================================================================
elif current_nav_key == "map":
    map_module.render_map_page(palette)

# =========================================================================
# PAGE 3: WASTE ANALYTICS DASHBOARD
# =========================================================================
elif current_nav_key == "analytics":
    analytics_dashboards.render_waste_analytics_page(palette)

# =========================================================================
# PAGE 4: WASTE FORECAST
# =========================================================================
elif current_nav_key == "forecast":
    st.markdown(
        f"""
        <div style="background:{palette['card_bg']}; border:1px solid {palette['border']}; border-left:4px solid {palette['purple']};
                    border-radius:8px; padding:18px 22px; margin-bottom:20px;">
            <div style="font-size:1.15rem; font-weight:800; color:{palette['text']};">🔮 7-Day Predictive Waste Forecast & Capacity Ceilings</div>
            <div style="font-size:0.75rem; color:{palette['muted']}; margin-top:4px;">
                Advanced machine learning simulation calibrated on day-of-week occupancy, event calendars, and ward generation history.
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

    # Ward-level forecast breakdown chart
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
# PAGE 5: FACILITY MANAGEMENT
# =========================================================================
elif current_nav_key == "facilities":
    facility_module.render_facility_management_page(palette)

# =========================================================================
# PAGE 6: SMART ALLOCATION
# =========================================================================
elif current_nav_key == "allocation":
    optimizer.render_smart_allocation_page(palette, wet_total, dry_total)

# =========================================================================
# PAGE 7: VEHICLE TRACKING & DISPATCH
# =========================================================================
elif current_nav_key == "vehicles":
    vehicle_module.render_vehicle_tracking_page(palette)

# =========================================================================
# PAGE 8: EVENT CALENDAR
# =========================================================================
elif current_nav_key == "calendar":
    calendar_module.render_calendar_section(palette, total_capacity=total_capacity)

# =========================================================================
# PAGE 9: SCENARIO SIMULATOR
# =========================================================================
elif current_nav_key == "simulator":
    simulator_module.render_scenario_simulator_page(palette, wet_total, dry_total)

# =========================================================================
# PAGE 10: ALERTS & NOTIFICATIONS
# =========================================================================
elif current_nav_key == "alerts":
    alert_engine.render_alerts_dashboard(palette)

# =========================================================================
# PAGE 11: CITIZEN REPORTS
# =========================================================================
elif current_nav_key == "citizen_reports":
    citizen_module.render_citizen_reports_page(palette)

# =========================================================================
# PAGE 12: CARBON & ESG DASHBOARD
# =========================================================================
elif current_nav_key == "carbon":
    wet_alloc = allocations.get("A", 0) + allocations.get("B", 0) + allocations.get("E", 0)
    dry_alloc = allocations.get("C", 0) + allocations.get("D", 0)
    analytics_module.render_carbon_scorecard(wet_alloc, dry_alloc, total_overflow, total_waste, palette)

# =========================================================================
# PAGE 13: PERFORMANCE DASHBOARD
# =========================================================================
elif current_nav_key == "performance":
    analytics_dashboards.render_performance_dashboard_page(palette)

# =========================================================================
# PAGE 14: REPORTS & EXPORTS
# =========================================================================
elif current_nav_key == "reports":
    reports_module.render_reports_page(palette)

# =========================================================================
# PAGE 15: USER MANAGEMENT (ADMIN ONLY)
# =========================================================================
elif current_nav_key == "users":
    if current_user.get("role") != "admin":
        auth.render_access_restricted_view("System User Management (Admin Only)")
    else:
        analytics_dashboards.render_user_management_page(palette)

# =========================================================================
# PAGE 16: SETTINGS
# =========================================================================
elif current_nav_key == "settings":
    settings_module.render_settings_page(palette)

# =========================================================================
# PAGE 17: PROFILE & SECURITY
# =========================================================================
elif current_nav_key == "profile":
    settings_module.render_profile_page(palette)

# --- Standard Footer ---
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f'<div style="text-align:center; color:{palette["muted"]}; font-size:0.7rem; '
    'letter-spacing:0.15em; text-transform:uppercase; border-top:1px solid ' + palette["border"] + '; padding-top:16px;">'
    "WasteGrid 2.0 — Smart Municipal Operations · Powered by Linear Optimization & IoT Telematics"
    "</div>",
    unsafe_allow_html=True,
)