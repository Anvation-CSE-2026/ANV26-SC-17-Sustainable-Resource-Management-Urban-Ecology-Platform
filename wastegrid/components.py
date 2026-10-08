import base64
import os
import streamlit as st


def header(logo_path="logo.png"):
    logo_html = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        logo_html = f'<img src="data:image/png;base64,{b64}" alt="logo" />'

    st.markdown(f"""
        <div class="wg-header">
            <div class="wg-brand">
                {logo_html}
                <div>
                    <div class="wg-title">WasteGrid</div>
                    <div class="wg-tagline">Predict. Detect. Reallocate.</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def section_title(text):
    st.markdown(f'<div class="sec-title">{text}</div>', unsafe_allow_html=True)


def metrics_row(total_waste, total_capacity, total_overflow, data_mode, p):
    overflow_cls = "red" if total_overflow > 0 else ""
    st.markdown(f"""
        <div class="metric-grid">
            <div class="m-card">
                <div class="m-label">Predicted Waste</div>
                <div class="m-value">{total_waste/1000:.2f} T</div>
            </div>
            <div class="m-card">
                <div class="m-label">Available Capacity</div>
                <div class="m-value">{total_capacity/1000:.2f} T</div>
            </div>
            <div class="m-card hero">
                <div class="m-label">Overflow</div>
                <div class="m-value {overflow_cls}">{total_overflow/1000:.2f} T</div>
            </div>
            <div class="m-card">
                <div class="m-label">Data Source</div>
                <div class="m-value text">{data_mode}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def status_banner(total_overflow, reoptimized, outage=None):
    if outage:
        st.markdown(
            f'<div class="wg-status warn">Facility <b>{outage}</b> is offline. Capacity reduced. Re-optimize to redistribute.</div>',
            unsafe_allow_html=True,
        )
    if total_overflow == 0:
        st.markdown(
            '<div class="wg-status">No predicted overflow — all waste can be processed</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="wg-status red">Potential overflow: {total_overflow/1000:.2f} T</div>',
            unsafe_allow_html=True,
        )
        if not reoptimized:
            st.markdown(
                '<div class="wg-status warn">Allocation plan is stale. Click RE-OPTIMIZE to respond.</div>',
                unsafe_allow_html=True,
            )


def action_buttons():
    st.markdown("""
        <div class="action-grid">
            <a class="act-btn" href="?action=event" target="_self">Add Event</a>
            <a class="act-btn" href="?action=outage" target="_self">Outage</a>
            <a class="act-btn primary" href="?action=reopt" target="_self">Re-optimize</a>
            <a class="act-btn" href="?action=reset" target="_self">Reset</a>
        </div>
    """, unsafe_allow_html=True)


def facility_grid(facilities, allocations, p):
    cards = []
    for f in facilities:
        alloc = allocations.get(f["id"], 0)
        util = alloc / f["capacity_kg"] * 100 if f["capacity_kg"] > 0 else 0
        if util < 70:
            color = p["success"]
        elif util < 95:
            color = p["warn"]
        else:
            color = p["accent"]

        cards.append(
            f'<div class="fac-card">'
            f'<div class="fac-name">Facility {f["id"]}</div>'
            f'<div class="fac-type">Accepts {f["accepts"]} · {f["distance_km"]} km</div>'
            f'<div class="fac-stat">{round(alloc):,} / {f["capacity_kg"]:,} kg</div>'
            f'<div class="fac-bar-wrap">'
            f'<div class="fac-bar" style="width:{min(util,100)}%; background:{color};"></div>'
            f'</div>'
            f'<div class="fac-util" style="color:{color};">{util:.0f}% utilized</div>'
            f'</div>'
        )

    st.markdown(
        '<div class="fac-grid">' + "".join(cards) + '</div>',
        unsafe_allow_html=True,
    )
def comparison_cards(fixed_overflow, total_overflow, p):
    f_cls = "red" if fixed_overflow > 0 else ""
    w_cls = "red" if total_overflow > 0 else ""
    st.markdown(f"""
        <div class="cmp-grid">
            <div class="cmp-card">
                <div class="cmp-label">Fixed Allocation — Overflow</div>
                <div class="cmp-value {f_cls}">{fixed_overflow/1000:.2f} T</div>
            </div>
            <div class="cmp-card">
                <div class="cmp-label">WasteGrid — Overflow</div>
                <div class="cmp-value {w_cls}">{total_overflow/1000:.2f} T</div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def success_banner(text):
    st.markdown(f'<div class="success-banner">{text}</div>', unsafe_allow_html=True)