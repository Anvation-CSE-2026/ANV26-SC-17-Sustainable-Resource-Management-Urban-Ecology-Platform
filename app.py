import streamlit as st
import pandas as pd

from wastegrid import data, optimizer, theme, components, forecast
from wastegrid import auth, calendar_module, truck_module, analytics_module

st.set_page_config(
    page_title="WasteGrid — AI Municipal Waste Reallocation",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Session state initialization ---
defaults = {
    "event_active": False,
    "reoptimized": True,
    "theme": "light",
    "outage_facility": None,
    "active_tab": "command",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- Theme resolution ---
param_theme = st.query_params.get("theme")
if param_theme in ["light", "dark"]:
    st.session_state.theme = param_theme
elif "theme" not in st.session_state or st.session_state.theme not in ["light", "dark"]:
    st.session_state.theme = "light"

st.query_params["theme"] = st.session_state.theme
palette = theme.get_palette(st.session_state.theme)
theme.inject_css(palette)

# --- Check logout trigger ---
if st.query_params.get("logout") == "1":
    if "logout" in st.query_params:
        del st.query_params["logout"]
    auth.logout()

# --- Authentication Gateway ---
current_user = auth.get_current_user()
if not current_user:
    # Render public header + login portal
    components.header(theme=st.session_state.theme, status="optimal", p=palette, user=None)
    auth.render_login_page(palette)
    st.stop()

# --- Load sources (from uploaded CSV widget or sample baseline) ---
uploaded = st.session_state.get("csv_uploader")
if uploaded is not None:
    try:
        sources = data.load_sources_from_csv(uploaded)
        data_mode = "CSV"
    except Exception:
        sources = data.SAMPLE_SOURCES
        data_mode = "Sample"
else:
    sources = data.SAMPLE_SOURCES
    data_mode = "Sample"

sources = data.apply_event_state(sources, st.session_state.event_active)

# --- Totals ---
wet_total, dry_total, total_waste = data.totals(sources)

# --- Apply outage ---
active_facilities = []
for f in data.FACILITIES:
    fc = dict(f)
    if st.session_state.outage_facility == fc["id"]:
        fc["capacity_kg"] = 0
    active_facilities.append(fc)

total_capacity = sum(f["capacity_kg"] for f in active_facilities)

# --- Allocation logic: Re-optimized vs Static baseline ---
if st.session_state.reoptimized:
    allocations, overflow = optimizer.optimize(active_facilities, wet_total, dry_total)
else:
    # Static allocation prior to running the optimizer
    allocations = {}
    base_plan = {"A": 2000, "B": 1800, "C": 1400}
    for f in active_facilities:
        fid = f["id"]
        if f["capacity_kg"] <= 0:
            allocations[fid] = 0
        else:
            allocations[fid] = min(base_plan.get(fid, 0), f["capacity_kg"])

    assigned_wet = allocations.get("A", 0) + allocations.get("B", 0)
    assigned_dry = allocations.get("C", 0)
    overflow = {}
    if wet_total > assigned_wet:
        overflow["wet"] = wet_total - assigned_wet
    if dry_total > assigned_dry:
        overflow["dry"] = dry_total - assigned_dry

st.session_state.allocations = allocations
st.session_state.overflow = overflow
total_overflow = optimizer.total_overflow(overflow)

# --- System status determination ---
if total_overflow > 0:
    system_status = "alert"
elif st.session_state.outage_facility:
    system_status = "warn"
else:
    system_status = "optimal"

# --- Main Dashboard Header with User Authority Badge & Logout ---
components.header(theme=st.session_state.theme, status=system_status, p=palette, user=current_user)

# --- Top Authority Switcher Bar (Quick Evaluation for Judges) ---
st.markdown(
    f'<div style="display:flex; justify-content:space-between; align-items:center; background:{palette["card_bg"]}; '
    f'border:1px solid {palette["border"]}; border-radius:8px; padding:8px 16px; margin-bottom:18px;">'
    f'<div style="font-size:0.7rem; font-weight:700; color:{palette["muted"]}; text-transform:uppercase; letter-spacing:0.12em;">'
    f'⚡ Quick Switch Authority Level:'
    f'</div>'
    f'<div style="display:flex; gap:8px;">'
    f'<span style="font-size:0.75rem; color:{palette["text"]};">Logged in as: <b>{current_user["title"]}</b> ({current_user["jurisdiction"]})</span>'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True,
)

col_s1, col_s2, col_s3, col_s4 = st.columns(4)
with col_s1:
    if st.button("🏛️ State Authority", key="sw_state", use_container_width=True):
        auth.quick_login("karnataka_admin")
with col_s2:
    if st.button("📍 District Authority", key="sw_district", use_container_width=True):
        auth.quick_login("district_admin")
with col_s3:
    if st.button("🏙️ Municipal Authority", key="sw_muni", use_container_width=True):
        auth.quick_login("municipality_admin")
with col_s4:
    if st.button("🏭 Factory Authority", key="sw_fact", use_container_width=True):
        auth.quick_login("factory_admin")

# --- Primary Module Navigation Tabs ---
tab_command, tab_calendar, tab_trucks, tab_carbon = st.tabs([
    "📊 Grid Command Center",
    "📅 Predictive Event & Holiday Calendar",
    "🚚 Truck-to-Municipality Telematics Bridge",
    "🌱 Carbon Offset & ESG Scorecard",
])

# =========================================================================
# TAB 1: GRID COMMAND CENTER
# =========================================================================
with tab_command:
    # Role-specific introductory modules
    user_role = current_user.get("role", "municipality")

    if user_role == "state":
        analytics_module.render_state_authority_view(palette)
    elif user_role == "district":
        analytics_module.render_district_authority_view(palette)
    elif user_role == "factory":
        analytics_module.render_factory_authority_view(active_facilities, allocations, palette)

    # Core WasteGrid Metrics Row
    components.section_title("REAL-TIME GRID METRICS")
    components.metrics_row(total_waste, total_capacity, total_overflow, data_mode, palette)

    # Multi-Stream Compatibility Flow
    components.stream_breakdown(wet_total, dry_total, palette)

    # Operational Status Banner
    components.status_banner(total_overflow, st.session_state.reoptimized, st.session_state.outage_facility)

    # 4 Interactive Action Buttons (Native Streamlit Buttons)
    btn_clicks = components.action_buttons(
        event_active=st.session_state.event_active,
        outage=st.session_state.outage_facility,
    )

    if btn_clicks["event"]:
        st.session_state.event_active = not st.session_state.event_active
        st.session_state.reoptimized = False
        st.rerun()

    if btn_clicks["outage"]:
        cycle = {None: "B", "B": "C", "C": None}
        st.session_state.outage_facility = cycle[st.session_state.outage_facility]
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

    # Data Ingestion Drawer (Positioned under Action Buttons)
    with st.expander("📁 DATA INGESTION — UPLOAD CSV OR DOWNLOAD TEMPLATE", expanded=False):
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
                    st.download_button("📥 SAMPLE CSV", f, file_name="sample_data.csv", mime="text/csv")
            except FileNotFoundError:
                pass

    # Facility Load Balancing Grid
    components.section_title("FACILITY UTILIZATION & LOAD BALANCING")
    components.facility_grid(active_facilities, allocations, palette, outage=st.session_state.outage_facility)

    # Fixed Allocation vs WasteGrid Dynamic Comparison
    components.section_title("FIXED ALLOCATION VS WASTEGRID")
    fixed_overflow = optimizer.fixed_allocation_overflow(total_waste, total_capacity)
    components.comparison_cards(fixed_overflow, total_overflow, palette)

    if fixed_overflow > 0 and total_overflow < fixed_overflow:
        pct = optimizer.reduction_pct(fixed_overflow, total_overflow)
        components.success_banner(f"WasteGrid prevented {fixed_overflow - total_overflow:,.0f} kg ({pct:.1f}%) of overflow vs static fixed routing!")

    # 7-Day Predictive Forecast Section
    components.section_title("7-DAY PREDICTIVE FORECAST & CAPACITY CEILING")
    forecast_rows = forecast.forecast_week(sources, total_capacity)
    forecast_df = pd.DataFrame(forecast_rows)
    components.forecast_section(forecast_df, palette)

    # Export Allocation Plan
    export_df = pd.DataFrame([
        {
            "Facility": f["id"],
            "Accepts": f["accepts"],
            "Capacity (kg)": f["capacity_kg"],
            "Allocated (kg)": round(allocations.get(f["id"], 0)),
            "Distance (km)": f["distance_km"],
        }
        for f in active_facilities
    ])
    st.download_button(
        "📥 DOWNLOAD ALLOCATION PLAN (CSV)",
        export_df.to_csv(index=False).encode("utf-8"),
        file_name="wastegrid_allocation.csv",
        mime="text/csv",
    )

# =========================================================================
# TAB 2: PREDICTIVE EVENT & HOLIDAY CALENDAR
# =========================================================================
with tab_calendar:
    calendar_module.render_calendar_section(palette, total_capacity=total_capacity)

# =========================================================================
# TAB 3: TRUCK-TO-MUNICIPALITY TELEMATICS BRIDGE
# =========================================================================
with tab_trucks:
    truck_module.render_truck_operations_section(
        palette,
        event_active=st.session_state.event_active,
        outage_facility=st.session_state.outage_facility,
    )

# =========================================================================
# TAB 4: CARBON OFFSET & ESG SCORECARD
# =========================================================================
with tab_carbon:
    wet_alloc = allocations.get("A", 0) + allocations.get("B", 0)
    dry_alloc = allocations.get("C", 0)
    analytics_module.render_carbon_scorecard(wet_alloc, dry_alloc, total_overflow, total_waste, palette)

# --- Footer ---
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f'<div style="text-align:center; color:{palette["muted"]}; font-size:0.7rem; '
    'letter-spacing:0.15em; text-transform:uppercase;">'
    "WasteGrid — Predict. Detect. Reallocate. · Powered by Linear Optimization & IoT Telematics"
    "</div>",
    unsafe_allow_html=True,
)