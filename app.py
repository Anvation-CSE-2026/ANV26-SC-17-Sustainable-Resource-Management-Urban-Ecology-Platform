import streamlit as st

from wastegrid import data, optimizer, theme, components

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

# --- Theme ---
palette = theme.get_palette(st.session_state.theme)
theme.inject_css(palette)

# --- Header ---
h1, h2 = st.columns([6, 1])
with h1:
    logo_col, title_col = st.columns([1, 12])
    with logo_col:
        try:
            st.image("logo.png", width=100)
        except Exception:
            pass
    with title_col:
        st.markdown("""
            <div style="margin-left:-15px; padding-top: 12px;">
                <div class="logo-title">WasteGrid</div>
                <div class="logo-tagline">Predict. Detect. Reallocate. — Dynamic Reallocation of Urban Waste-Processing Capacity</div>
            </div>
        """, unsafe_allow_html=True)
with h2:
    st.markdown("<div style='padding-top: 20px;'></div>", unsafe_allow_html=True)
    label = "🌙 Dark" if st.session_state.theme == "light" else "☀️ Light"
    if st.button(label, key="theme_toggle", use_container_width=True):
        st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"
        st.rerun()

st.markdown(f"<hr style='border-color:{palette['divider']}; margin: 12px 0 20px 0;'>", unsafe_allow_html=True)

# --- Data source (expander) ---
with st.expander("📁  Data Source  —  Upload CSV or use sample data", expanded=False):
    st.markdown(
        f"<p style='color:{palette['text_muted']}; font-size:0.9rem;'>"
        "Upload a CSV with columns <code>source, baseline_kg, waste_type</code>. "
        "If no file is uploaded, the app uses built-in sample data.</p>",
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader("Upload waste data CSV", type=["csv"], label_visibility="collapsed")
    try:
        with open("sample_data.csv", "rb") as f:
            st.download_button("⬇️  Download sample CSV", f, file_name="sample_data.csv", mime="text/csv")
    except FileNotFoundError:
        st.caption("sample_data.csv not found in repo root — add it to enable the download button.")

# --- Load sources ---
if uploaded is not None:
    try:
        sources = data.load_sources_from_csv(uploaded)
        st.success(f"✅ Loaded {len(sources)} sources from CSV")
        data_mode = "CSV"
    except Exception as e:
        st.error(f"CSV error: {e}")
        sources = data.SAMPLE_SOURCES
        data_mode = "Sample"
else:
    sources = data.SAMPLE_SOURCES
    data_mode = "Sample"

sources = data.apply_event_state(sources, st.session_state.event_active)

# --- Compute ---
wet_total, dry_total, total_waste = data.totals(sources)
total_capacity = sum(f["capacity_kg"] for f in data.FACILITIES)

allocations, overflow = optimizer.optimize(data.FACILITIES, wet_total, dry_total)
total_overflow = optimizer.total_overflow(overflow)

# --- Metric cards ---
m1, m2, m3, m4 = st.columns(4)
components.metric_card(m1, "Predicted Waste", f"{total_waste/1000:.2f} T", "#0891b2")
components.metric_card(m2, "Available Capacity", f"{total_capacity/1000:.2f} T", "#16a34a")
components.metric_card(m3, "Overflow", f"{total_overflow/1000:.2f} T", "#dc2626" if total_overflow > 0 else "#16a34a")
components.metric_card(m4, "Data Source", data_mode, "#7c3aed")

st.markdown("<br>", unsafe_allow_html=True)
components.status_banner(total_overflow, st.session_state.reoptimized)
st.markdown("<br>", unsafe_allow_html=True)

# --- Controls ---
b1, b2, b3 = st.columns(3)
with b1:
    if st.button("➕  Add Large Event", use_container_width=True):
        st.session_state.event_active = True
        st.session_state.reoptimized = False
        st.rerun()
with b2:
    if st.button("⚙️  Re-optimize", use_container_width=True):
        st.session_state.reoptimized = True
        st.rerun()
with b3:
    if st.button("🔄  Reset", use_container_width=True):
        st.session_state.event_active = False
        st.session_state.reoptimized = False
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# --- Facility cards ---
st.markdown(f"<h3 style='color:{palette['text']};'>📦 Facility Utilization</h3>", unsafe_allow_html=True)
f_cols = st.columns(len(data.FACILITIES))
for i, f in enumerate(data.FACILITIES):
    components.facility_card(f_cols[i], f, allocations[f["id"]], palette["text_muted"])

st.markdown("<br>", unsafe_allow_html=True)

# --- Comparison (themed cards, no dataframe) ---
st.markdown(f"<h3 style='color:{palette['text']};'>📊 Fixed Allocation vs WasteGrid</h3>", unsafe_allow_html=True)

fixed_overflow = optimizer.fixed_allocation_overflow(total_waste, total_capacity)

c1, c2 = st.columns(2)
with c1:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Fixed Allocation — Overflow</div>
            <div class="metric-value" style="color:{'#dc2626' if fixed_overflow > 0 else '#16a34a'};">
                {fixed_overflow/1000:.2f} T
            </div>
        </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">WasteGrid — Overflow</div>
            <div class="metric-value" style="color:{'#dc2626' if total_overflow > 0 else '#16a34a'};">
                {total_overflow/1000:.2f} T
            </div>
        </div>
    """, unsafe_allow_html=True)

if fixed_overflow > 0 and total_overflow < fixed_overflow:
    pct = optimizer.reduction_pct(fixed_overflow, total_overflow)
    components.success_banner(f"✅ WasteGrid reduced overflow by {pct:.1f}% vs fixed allocation")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f'<div style="text-align:center; color:{palette["text_muted"]}; font-size:0.85rem;">'
    "WasteGrid MVP — Predict. Detect. Reallocate."
    "</div>",
    unsafe_allow_html=True,
)
