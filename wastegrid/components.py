import base64
import os
import streamlit as st
import pandas as pd
import altair as alt


def header(theme="light", status="optimal", logo_path="logo.png", p=None):
    logo_html = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        logo_html = f'<img src="data:image/png;base64,{b64}" alt="logo" />'

    if status == "alert":
        badge_cls, badge_dot, badge_text = "alert", "red", "Overflow Alert"
    elif status == "warn":
        badge_cls, badge_dot, badge_text = "warn", "yellow", "Facility Offline"
    else:
        badge_cls, badge_dot, badge_text = "optimal", "green", "System Optimal"

    next_theme = "dark" if theme == "light" else "light"
    toggle_icon = "🌙" if theme == "light" else "☀️"
    toggle_label = "Dark" if theme == "light" else "Light"

    st.markdown(
        f'<div class="wg-header">'
        f'<div class="wg-brand">{logo_html}<div><div class="wg-title">WasteGrid</div><div class="wg-tagline">Predict. Detect. Reallocate.</div></div></div>'
        f'<div class="hdr-controls">'
        f'<div class="hdr-badge {badge_cls}"><span class="pulse-dot {badge_dot}"></span>{badge_text}</div>'
        f'<a class="theme-toggle-link" href="?theme={next_theme}" target="_self"><span>{toggle_icon}</span><span>{toggle_label}</span></a>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def section_title(text):
    st.markdown(f'<div class="sec-title">{text}</div>', unsafe_allow_html=True)


def metrics_row(total_waste, total_capacity, total_overflow, data_mode, p):
    overflow_cls = "red" if total_overflow > 0 else "green"
    overflow_icon = "⚠️" if total_overflow > 0 else "🛡️"
    st.markdown(
        f'<div class="metric-grid">'
        f'<div class="m-card"><div class="m-label">📊 Predicted Demand</div><div class="m-value">{total_waste/1000:.2f} T</div></div>'
        f'<div class="m-card green"><div class="m-label">🏭 Available Capacity</div><div class="m-value">{total_capacity/1000:.2f} T</div></div>'
        f'<div class="m-card hero"><div class="m-label">{overflow_icon} Overflow Risk</div><div class="m-value {overflow_cls}">{total_overflow/1000:.2f} T</div></div>'
        f'<div class="m-card purple"><div class="m-label">📁 Data Stream</div><div class="m-value text">{data_mode}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def stream_breakdown(wet_total, dry_total, p):
    total = wet_total + dry_total
    wet_pct = (wet_total / total * 100) if total > 0 else 50
    dry_pct = 100 - wet_pct

    st.markdown(
        f'<div class="breakdown-card">'
        f'<div class="breakdown-header">'
        f'<div class="breakdown-title">🔄 Multi-Stream Composition & Compatibility Flow</div>'
        f'<div class="breakdown-ratio">Wet {wet_pct:.0f}% · Dry {dry_pct:.0f}%</div>'
        f'</div>'
        f'<div class="split-bar-wrap">'
        f'<div class="split-bar-wet" style="width:{wet_pct}%;"></div>'
        f'<div class="split-bar-dry" style="width:{dry_pct}%;"></div>'
        f'</div>'
        f'<div class="breakdown-legend">'
        f'<div class="legend-item"><span class="legend-dot" style="background:{p["blue"]};"></span><span><b>💧 Organic / Wet:</b> {wet_total:,.0f} kg ({wet_pct:.1f}%) → Routed to Facilities A & B</span></div>'
        f'<div class="legend-item"><span class="legend-dot" style="background:{p["purple"]};"></span><span><b>📦 Recyclable / Dry:</b> {dry_total:,.0f} kg ({dry_pct:.1f}%) → Routed to Facility C</span></div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def status_banner(total_overflow, reoptimized, outage=None):
    if outage:
        st.markdown(
            f'<div class="wg-status warn">⚡ <b>Alert:</b> Facility <b>{outage}</b> is offline. Processing capacity reduced. Click Re-optimize to redistribute!</div>',
            unsafe_allow_html=True,
        )
    if total_overflow == 0:
        st.markdown(
            '<div class="wg-status">✅ <b>System Nominal:</b> Zero predicted overflow — all active waste streams accommodated by compatible processing facilities.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="wg-status red">🚨 <b>Capacity Breach:</b> Potential overflow of <b>{total_overflow/1000:.2f} Tons</b> detected beyond facility processing limits!</div>',
            unsafe_allow_html=True,
        )
        if not reoptimized:
            st.markdown(
                '<div class="wg-status warn">⚠️ <b>Action Required:</b> Allocation matrix is out of sync. Click <b>RE-OPTIMIZE</b> to compute rebalancing.</div>',
                unsafe_allow_html=True,
            )


def action_buttons(event_active=False, outage=None):
    event_label = "⚡ Dismiss Event" if event_active else "⚡ Add Event Spike"
    outage_label = f"🔌 Outage ({outage})" if outage else "🔌 Simulate Outage"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        click_event = st.button(event_label, key="btn_act_event", use_container_width=True)
    with col2:
        click_outage = st.button(outage_label, key="btn_act_outage", use_container_width=True)
    with col3:
        click_reopt = st.button("⚙️ Re-optimize Grid", key="btn_act_reopt", type="primary", use_container_width=True)
    with col4:
        click_reset = st.button("🔄 Reset System", key="btn_act_reset", use_container_width=True)

    return {
        "event": click_event,
        "outage": click_outage,
        "reopt": click_reopt,
        "reset": click_reset,
    }


def facility_grid(facilities, allocations, p, outage=None):
    cards = []
    fac_meta = {
        "A": {"icon": "🏢", "desc": "Organic Biocompost Plant"},
        "B": {"icon": "♻️", "desc": "Anaerobic Digester & Biogas"},
        "C": {"icon": "📦", "desc": "Material Recovery Facility (MRF)"},
    }

    for f in facilities:
        fid = f["id"]
        meta = fac_meta.get(fid, {"icon": "🏭", "desc": "Processing Facility"})
        is_off = (outage == fid) or (f["capacity_kg"] <= 0)
        alloc = allocations.get(fid, 0)
        util = (alloc / f["capacity_kg"] * 100) if f["capacity_kg"] > 0 else 0

        if is_off:
            badge_html = '<span class="fac-badge offline">Offline</span>'
            card_extra = "offline"
            color = p["muted"]
            util_str = "Offline"
        else:
            badge_html = '<span class="fac-badge active">● Online</span>'
            card_extra = ""
            if util < 70:
                color = p["success"]
            elif util < 95:
                color = p["warn"]
            else:
                color = p["accent"]
            util_str = f"{util:.0f}% utilized"

        cards.append(
            f'<div class="fac-card {card_extra}">'
            f'<div class="fac-name-row"><div class="fac-name">{meta["icon"]} Facility {fid}</div>{badge_html}</div>'
            f'<div class="fac-type">{meta["desc"]} · Accepts {f["accepts"].upper()} · {f["distance_km"]} km</div>'
            f'<div class="fac-stat">{round(alloc):,} / {f["capacity_kg"]:,} kg</div>'
            f'<div class="fac-bar-wrap"><div class="fac-bar" style="width:{min(util,100)}%; background:{color};"></div></div>'
            f'<div class="fac-util" style="color:{color};">{util_str}</div>'
            f'</div>'
        )

    st.markdown(
        '<div class="fac-grid">' + "".join(cards) + '</div>',
        unsafe_allow_html=True,
    )


def comparison_cards(fixed_overflow, total_overflow, p):
    f_cls = "red" if fixed_overflow > 0 else "green"
    w_cls = "red" if total_overflow > 0 else "green"
    w_card = "" if total_overflow > 0 else "win"
    st.markdown(
        f'<div class="cmp-grid">'
        f'<div class="cmp-card"><div class="cmp-label">🛑 Fixed Static Allocation — Overflow</div><div class="cmp-value {f_cls}">{fixed_overflow/1000:.2f} T</div></div>'
        f'<div class="cmp-card {w_card}"><div class="cmp-label">🚀 WasteGrid Dynamic Solver — Overflow</div><div class="cmp-value {w_cls}">{total_overflow/1000:.2f} T</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def success_banner(text):
    st.markdown(f'<div class="success-banner">{text}</div>', unsafe_allow_html=True)


def forecast_section(df, p):
    if df.empty:
        return

    # 1. Visual 7-Day Meter Grid
    day_cards = []
    max_pred = max(df["Predicted (T)"].max(), df["Capacity (T)"].max(), 1.0) * 1.15

    for _, row in df.iterrows():
        day = row["Day"]
        pred = row["Predicted (T)"]
        cap = row["Capacity (T)"]
        ovf = row["Overflow (T)"]

        pct = min(100, max(10, (pred / max_pred) * 100))
        is_overflow = ovf > 0

        fill_cls = "surge" if is_overflow else "normal"
        card_cls = "overflow" if is_overflow else ""
        badge_html = f'<span class="fc-day-badge risk">▲ +{ovf:.2f} T</span>' if is_overflow else '<span class="fc-day-badge safe">✓ Safe</span>'

        day_cards.append(
            f'<div class="fc-day-card {card_cls}">'
            f'<div class="fc-day-name">{day}</div>'
            f'<div class="fc-meter-wrap"><div class="fc-meter-fill {fill_cls}" style="height:{pct:.0f}%;"></div></div>'
            f'<div class="fc-day-val">{pred:.2f} T</div>'
            f'{badge_html}'
            f'</div>'
        )

    st.markdown(
        '<div class="fc-visual-grid">' + "".join(day_cards) + '</div>',
        unsafe_allow_html=True,
    )

    # 2. Executive Forecast Table
    rows_html = []
    for _, row in df.iterrows():
        day = row["Day"]
        pred = row["Predicted (T)"]
        cap = row["Capacity (T)"]
        ovf = row["Overflow (T)"]

        if ovf > 0:
            pill = f'<span class="fc-pill overflow">▲ Capacity Exceeded (+{ovf:.2f} T)</span>'
            ovf_style = f'color:{p["accent"]}; font-weight:700;'
        else:
            pill = '<span class="fc-pill safe">● Optimal Flow (0.00 T)</span>'
            ovf_style = f'color:{p["success"]}; font-weight:600;'

        rows_html.append(
            f'<tr>'
            f'<td><b>{day}</b></td>'
            f'<td>{pred:.2f} Tons</td>'
            f'<td>{cap:.2f} Tons</td>'
            f'<td style="{ovf_style}">{ovf:.2f} Tons</td>'
            f'<td>{pill}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<div class="fc-table-wrap">'
        f'<table class="fc-table">'
        f'<thead><tr>'
        f'<th>Forecasted Day</th>'
        f'<th>Predicted Demand</th>'
        f'<th>Capacity Ceiling</th>'
        f'<th>Overflow Risk</th>'
        f'<th>Operational Status</th>'
        f'</tr></thead>'
        f'<tbody>'
        f'{"".join(rows_html)}'
        f'</tbody>'
        f'</table>'
        f'</div>',
        unsafe_allow_html=True,
    )