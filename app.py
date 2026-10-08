import streamlit as st
import pandas as pd

from wastegrid import data, optimizer, theme, components, forecast

st.set_page_config(
    page_title="WasteGrid",
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
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- Theme resolution ---
# Check URL query param first so toggling between ?theme=dark and ?theme=light is 100% reliable
param_theme = st.query_params.get("theme")
if param_theme in ["light", "dark"]:
    st.session_state.theme = param_theme
elif "theme" not in st.session_state or st.session_state.theme not in ["light", "dark"]:
    st.session_state.theme = "light"

# Sync URL query param to reflect active theme
st.query_params["theme"] = st.session_state.theme

# --- Theme ---
palette = theme.get_palette(st.session_state.theme)
theme.inject_css(palette)

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
    # Static allocation prior to running the optimizer:
    # Baseline static plan is A: 2000, B: 1800, C: 1400.
    # Offline facilities lose their allocation (stranded overflow),
    # and unscheduled surges cannot be re-routed until user clicks Re-optimize.
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

# --- Header with live status badge & theme toggle ---
if total_overflow > 0:
    system_status = "alert"
elif st.session_state.outage_facility:
    system_status = "warn"
else:
    system_status = "optimal"

components.header(theme=st.session_state.theme, status=system_status, p=palette)

# --- Metrics row ---
components.metrics_row(total_waste, total_capacity, total_overflow, data_mode, palette)

# --- Waste Stream Breakdown ---
components.stream_breakdown(wet_total, dry_total, palette)

# --- Status Banner ---
components.status_banner(total_overflow, st.session_state.reoptimized, st.session_state.outage_facility)

# --- Actions with active scenario indicators (Native Streamlit Buttons) ---
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

# --- Data Ingestion Drawer (Positioned under Action Buttons) ---
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

# --- Facility grid with active/offline pills ---
components.section_title("FACILITY UTILIZATION & LOAD BALANCING")
components.facility_grid(active_facilities, allocations, palette, outage=st.session_state.outage_facility)

# --- Comparison ---
components.section_title("FIXED ALLOCATION VS WASTEGRID")
fixed_overflow = optimizer.fixed_allocation_overflow(total_waste, total_capacity)
components.comparison_cards(fixed_overflow, total_overflow, palette)

if fixed_overflow > 0 and total_overflow < fixed_overflow:
    pct = optimizer.reduction_pct(fixed_overflow, total_overflow)
    components.success_banner(f"WasteGrid prevented {fixed_overflow - total_overflow:,.0f} kg ({pct:.1f}%) of overflow vs static fixed routing!")

# --- 7-Day Forecast ---
components.section_title("7-DAY PREDICTIVE FORECAST & CAPACITY CEILING")
forecast_rows = forecast.forecast_week(sources, total_capacity)
forecast_df = pd.DataFrame(forecast_rows)
components.forecast_section(forecast_df, palette)

# --- Export ---
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

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f'<div style="text-align:center; color:{palette["muted"]}; font-size:0.7rem; '
    'letter-spacing:0.15em; text-transform:uppercase;">'
    "WasteGrid — Predict. Detect. Reallocate."
    "</div>",
    unsafe_allow_html=True,
)