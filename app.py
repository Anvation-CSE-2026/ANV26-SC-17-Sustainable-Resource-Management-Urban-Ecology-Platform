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
if "event_active" not in st.session_state:
    st.session_state.event_active = False
if "reoptimized" not in st.session_state:
    st.session_state.reoptimized = False
if "theme" not in st.session_state:
    st.session_state.theme = "light"
if "outage_facility" not in st.session_state:
    st.session_state.outage_facility = None

# --- Theme ---
palette = theme.get_palette(st.session_state.theme)
theme.inject_css(palette)

# --- Header ---
h1, h2 = st.columns([6, 1])
with h1:
    logo_col, title_col = st.columns([1, 12])
    with logo_col:
        try:
            st.image("logo.png", width=64)
        except Exception:
            pass
    with title_col:
        st.markdown("""
            <div style="margin-left:-10px; padding-top: 6px;">
                <div class="logo-title">WasteGrid</div>
                <div class="logo-tagline">Predict. Detect. Reallocate.</div>
            </div>
        """, unsafe_allow_html=True)
with h2:
    st.markdown("<div style='padding-top: 10px;'></div>", unsafe_allow_html=True)
    label = "DARK" if st.session_state.theme == "light" else "LIGHT"
    if st.button(label, key="theme_toggle", use_container_width=True):
        st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
        st.rerun()

st.markdown(f"""
    <div style="
        height: 1px;
        background: {palette['divider']};
        margin: 20px 0 32px 0;
    "></div>
""", unsafe_allow_html=True)

# --- Data source (expander) ---
with st.expander("DATA SOURCE  —  UPLOAD CSV OR USE SAMPLE DATA", expanded=False):
    st.markdown(
        f"<p style='color:{palette['text_muted']}; font-size:0.85rem;'>"
        "Upload a CSV with columns <code>source, baseline_kg, waste_type</code>. "
        "If no file is uploaded, the app uses built-in sample data.</p>",
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader("Upload waste data CSV", type=["csv"], label_visibility="collapsed")
    try:
        with open("sample_data.csv", "rb") as f:
            st.download_button("DOWNLOAD SAMPLE CSV", f, file_name="sample_data.csv", mime="text/csv")
    except FileNotFoundError:
        st.caption("sample_data.csv not found in repo root.")

# --- Load sources ---
if uploaded is not None:
    try:
        sources = data.load_sources_from_csv(uploaded)
        st.success(f"Loaded {len(sources)} sources from CSV")
        data_mode = "CSV"
    except Exception as e:
        st.error(f"CSV error: {e}")
        sources = data.SAMPLE_SOURCES
        data_mode = "Sample"
else:
    sources = data.SAMPLE_SOURCES
    data_mode = "Sample"

sources = data.apply_event_state(sources, st.session_state.event_active)

# --- Compute current totals ---
wet_total, dry_total, total_waste = data.totals(sources)

# --- Apply facility outage if active ---
active_facilities = []
for f in data.FACILITIES:
    f_copy = dict(f)
    if st.session_state.outage_facility == f_copy["id"]:
        f_copy["capacity_kg"] = 0
    active_facilities.append(f_copy)

total_capacity = sum(f["capacity_kg"] for f in active_facilities)

# --- Demand signature + freeze logic ---
demand_signature = (round(wet_total), round(dry_total), st.session_state.outage_facility)

if "allocations" not in st.session_state or "demand_signature" not in st.session_state:
    allocs, ovf = optimizer.optimize(active_facilities, wet_total, dry_total)
    st.session_state.allocations = allocs
    st.session_state.overflow = ovf
    st.session_state.demand_signature = demand_signature
    st.session_state.reoptimized = True

allocations = st.session_state.allocations
overflow = st.session_state.overflow
total_overflow = optimizer.total_overflow(overflow)

# --- Metric cards ---
neutral = palette["text"]
accent_red = palette["accent"]
muted = palette["text_muted"]

m1, m2, m3, m4 = st.columns([1, 1, 1.4, 1])
components.metric_card(m1, "PREDICTED WASTE", f"{total_waste/1000:.2f} T", neutral)
components.metric_card(m2, "AVAILABLE CAPACITY", f"{total_capacity/1000:.2f} T", neutral)
components.metric_card(
    m3, "OVERFLOW", f"{total_overflow/1000:.2f} T",
    accent_red if total_overflow > 0 else neutral,
    emphasize=True,
)
components.metric_card(m4, "DATA SOURCE", data_mode, muted)

st.markdown("<br>", unsafe_allow_html=True)

# Outage indicator
if st.session_state.outage_facility:
    st.markdown(
        f'<div class="status-warn">&nbsp;Facility <b>{st.session_state.outage_facility}</b> is offline. '
        'Capacity reduced. Re-optimize to redistribute.</div>',
        unsafe_allow_html=True,
    )

components.status_banner(total_overflow, st.session_state.reoptimized)
st.markdown("<br>", unsafe_allow_html=True)

# --- Controls ---
b1, b2, b3, b4 = st.columns(4)
with b1:
    if st.button("ADD LARGE EVENT", use_container_width=True):
        st.session_state.event_active = True
        st.session_state.reoptimized = False
        st.rerun()
with b2:
    if st.button("FACILITY OUTAGE", use_container_width=True):
        cycle = {None: "B", "B": "C", "C": None}
        st.session_state.outage_facility = cycle[st.session_state.outage_facility]
        st.session_state.reoptimized = False
        st.rerun()
with b3:
    if st.button("RE-OPTIMIZE", use_container_width=True):
        allocs, ovf = optimizer.optimize(active_facilities, wet_total, dry_total)
        st.session_state.allocations = allocs
        st.session_state.overflow = ovf
        st.session_state.demand_signature = demand_signature
        st.session_state.reoptimized = True
        st.rerun()
with b4:
    if st.button("RESET", use_container_width=True):
        st.session_state.event_active = False
        st.session_state.reoptimized = False
        st.session_state.outage_facility = None
        for k in ["allocations", "overflow", "demand_signature"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# --- Facility cards ---
components.section_title("", "FACILITY UTILIZATION")
f_cols = st.columns(len(active_facilities))
for i, f in enumerate(active_facilities):
    components.facility_card(f_cols[i], f, allocations.get(f["id"], 0), palette["text_muted"])

st.markdown("<br>", unsafe_allow_html=True)

# --- Comparison ---
components.section_title("", "FIXED ALLOCATION VS WASTEGRID")

fixed_overflow = optimizer.fixed_allocation_overflow(total_waste, total_capacity)

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">FIXED ALLOCATION — OVERFLOW</div>
            <div class="metric-value" style="color:{accent_red if fixed_overflow > 0 else neutral};">
                {fixed_overflow/1000:.2f} T
            </div>
        </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">WASTEGRID — OVERFLOW</div>
            <div class="metric-value" style="color:{accent_red if total_overflow > 0 else neutral};">
                {total_overflow/1000:.2f} T
            </div>
        </div>
    """, unsafe_allow_html=True)

if fixed_overflow > 0 and total_overflow < fixed_overflow:
    pct = optimizer.reduction_pct(fixed_overflow, total_overflow)
    components.success_banner(f"WasteGrid reduced overflow by {pct:.1f}% vs fixed allocation")

st.markdown("<br>", unsafe_allow_html=True)

# --- 7-Day Forecast ---
components.section_title("", "7-DAY FORECAST")

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

st.markdown("<br>", unsafe_allow_html=True)

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
csv_bytes = export_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "DOWNLOAD ALLOCATION PLAN (CSV)",
    csv_bytes,
    file_name="wastegrid_allocation.csv",
    mime="text/csv",
)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f'<div style="text-align:center; color:{palette["text_muted"]}; font-size:0.72rem; '
    'letter-spacing:0.15em; text-transform:uppercase;">'
    "WasteGrid — Predict. Detect. Reallocate."
    "</div>",
    unsafe_allow_html=True,
)