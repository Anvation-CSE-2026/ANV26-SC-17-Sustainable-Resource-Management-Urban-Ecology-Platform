import streamlit as st
import pandas as pd

from wastegrid import data, optimizer, theme, components, forecast

st.set_page_config(
    page_title="WasteGrid",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- Session state ---
defaults = {
    "event_active": False,
    "reoptimized": True,
    "theme": "light",
    "outage_facility": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- Handle query-param actions ---
qp = st.query_params
action = qp.get("action")
if action:
    if action == "event":
        st.session_state.event_active = True
        st.session_state.reoptimized = False
    elif action == "outage":
        cycle = {None: "B", "B": "C", "C": None}
        st.session_state.outage_facility = cycle[st.session_state.outage_facility]
        st.session_state.reoptimized = False
    elif action == "reopt":
        st.session_state.reoptimized = True
        st.session_state._force_reopt = True
    elif action == "reset":
        st.session_state.event_active = False
        st.session_state.reoptimized = False
        st.session_state.outage_facility = None
        for k in ["allocations", "overflow", "demand_signature", "_force_reopt"]:
            st.session_state.pop(k, None)
    st.query_params.clear()
    st.rerun()

# --- Theme ---
palette = theme.get_palette(st.session_state.theme)
theme.inject_css(palette)

# --- Header ---
components.header()

# --- Data source ---
with st.expander("DATA SOURCE — UPLOAD CSV OR USE SAMPLE DATA", expanded=False):
    uploaded = st.file_uploader("Upload CSV", type=["csv"], label_visibility="collapsed")
    try:
        with open("sample_data.csv", "rb") as f:
            st.download_button("DOWNLOAD SAMPLE CSV", f, file_name="sample_data.csv", mime="text/csv")
    except FileNotFoundError:
        pass

# --- Load sources ---
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

# --- Allocation logic ---
demand_sig = (round(wet_total), round(dry_total), st.session_state.outage_facility)
needs_init = "allocations" not in st.session_state
force = st.session_state.pop("_force_reopt", False)

if needs_init or force:
    allocs, ovf = optimizer.optimize(active_facilities, wet_total, dry_total)
    st.session_state.allocations = allocs
    st.session_state.overflow = ovf
    st.session_state.demand_signature = demand_sig
    st.session_state.reoptimized = True

allocations = st.session_state.allocations
overflow = st.session_state.overflow
total_overflow = optimizer.total_overflow(overflow)

# --- Metrics row ---
components.metrics_row(total_waste, total_capacity, total_overflow, data_mode, palette)

# --- Status ---
components.status_banner(total_overflow, st.session_state.reoptimized, st.session_state.outage_facility)

# --- Actions ---
components.action_buttons()

# --- Facility grid ---
components.section_title("FACILITY UTILIZATION")
components.facility_grid(active_facilities, allocations, palette)

# --- Comparison ---
components.section_title("FIXED ALLOCATION VS WASTEGRID")
fixed_overflow = optimizer.fixed_allocation_overflow(total_waste, total_capacity)
components.comparison_cards(fixed_overflow, total_overflow, palette)

if fixed_overflow > 0 and total_overflow < fixed_overflow:
    pct = optimizer.reduction_pct(fixed_overflow, total_overflow)
    components.success_banner(f"WasteGrid reduced overflow by {pct:.1f}% vs fixed allocation")

# --- 7-Day Forecast ---
components.section_title("7-DAY FORECAST")
forecast_rows = forecast.forecast_week(sources, total_capacity)
forecast_df = pd.DataFrame(forecast_rows)

def highlight_overflow(row):
    if row["Overflow (T)"] > 0:
        return ["background-color: rgba(213,0,28,0.08)"] * len(row)
    return [""] * len(row)

st.dataframe(
    forecast_df.style.apply(highlight_overflow, axis=1),
    use_container_width=True,
    hide_index=True,
)

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
    "DOWNLOAD ALLOCATION PLAN (CSV)",
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