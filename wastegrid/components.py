import streamlit as st


def section_title(icon, text):
    icon_html = f"{icon}&nbsp;&nbsp;" if icon else ""
    st.markdown(f'<div class="section-title">{icon_html}{text}</div>', unsafe_allow_html=True)


def metric_card(col, label, value, accent, sub=None, emphasize=False):
    sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
    card_cls = "metric-card emphasize" if emphasize else "metric-card"
    col.markdown(f"""
        <div class="{card_cls}">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color:{accent};">{value}</div>
            {sub_html}
        </div>
    """, unsafe_allow_html=True)


def status_banner(total_overflow, reoptimized):
    if total_overflow == 0:
        st.markdown(
            '<div class="status-ok">&nbsp;No predicted overflow — all waste can be processed</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="status-alert">&nbsp;Potential overflow: <b>{total_overflow/1000:.2f} T</b></div>',
            unsafe_allow_html=True,
        )
        if not reoptimized:
            st.markdown(
                '<div class="status-warn">&nbsp;Allocation plan is stale. Click <b>Re-optimize</b> to respond.</div>',
                unsafe_allow_html=True,
            )


def facility_card(col, facility, allocated_kg, text_muted, normal_color=None):
    theme = st.session_state.get("theme", "light")
    if normal_color is None:
        normal_color = "#0a0a0a" if theme == "light" else "#fafafa"

    util = allocated_kg / facility["capacity_kg"] * 100 if facility["capacity_kg"] > 0 else 0
    if util < 70:
        color = normal_color
    elif util < 95:
        color = "#b45309"
    else:
        color = "#d5001c"

    col.markdown(f"""
        <div class="facility-card">
            <div class="facility-name">Facility {facility['id']}</div>
            <div class="facility-type">Accepts: {facility['accepts']} · {facility['distance_km']} km</div>
            <div style="margin-top:16px; font-size:0.82rem; color:{text_muted}; font-weight:400; font-variant-numeric: tabular-nums;">
                {round(allocated_kg):,} / {facility['capacity_kg']:,} kg
            </div>
            <div class="util-bar">
                <div class="util-fill" style="width:{min(util,100)}%; background:{color};"></div>
            </div>
            <div style="margin-top:10px; font-size:0.7rem; color:{color}; font-weight:500; letter-spacing:0.08em; text-transform:uppercase;">
                {util:.0f}% utilized
            </div>
        </div>
    """, unsafe_allow_html=True)


def success_banner(text):
    st.markdown(f'<div class="status-success">&nbsp;{text}</div>', unsafe_allow_html=True)