"""
Smart Vehicle Dispatch, Fleet Telematics, and Route Maps for WasteGrid 2.0.
Features:
- Live GPS vehicle location tracking and interactive route map
- Fleet telematics (speed, payload, hydraulic lift sensor logs)
- Automated dynamic turnaround dispatch suggestions
- Vehicle CRUD and status management (Available, Assigned, In Transit, Diverted, Maintenance)
"""

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from wastegrid import db


def render_vehicle_tracking_page(palette):
    """Render the full interactive Vehicle Tracking & Dispatch console."""
    p = palette

    st.markdown(
        f"""
        <div style="background:{p['card_bg']}; border:1px solid {p['border']}; border-left:4px solid {p['blue']};
                    border-radius:8px; padding:18px 22px; margin-bottom:20px;">
            <div style="font-size:1.15rem; font-weight:800; color:{p['text']};">🚚 Municipal Compactor Vehicle Tracking & Smart Dispatch</div>
            <div style="font-size:0.75rem; color:{p['muted']}; margin-top:4px;">
                Real-time IoT hydraulic lifter payload tracking, GPS geofencing, route telemetry, and automated turnaround diversion.
            </div>
            <div style="margin-top:6px; font-size:0.68rem; color:#8ba3c7;">
                <b>Notice:</b> Telemetry represents real-time cellular transponder streaming combined with municipal simulation test feeds.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    vehicles = db.get_all_vehicles()
    facilities = db.get_all_facilities(include_offline=True)
    fac_dict = {f["id"]: f for f in facilities}

    if not vehicles:
        st.warning("No vehicles registered in database.")
        return

    # 1. Fleet Telematics KPIs
    total_trucks = len(vehicles)
    in_transit = sum(1 for v in vehicles if v["status"] in ["in_transit", "diverted"])
    available_trucks = sum(1 for v in vehicles if v["status"] == "available")
    maintenance_trucks = sum(1 for v in vehicles if v["status"] == "maintenance")
    tot_payload = sum(v["current_payload_kg"] for v in vehicles)
    tot_capacity = sum(v["capacity_kg"] for v in vehicles)
    fleet_util = (tot_payload / tot_capacity * 100) if tot_capacity > 0 else 0

    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="m-card"><div class="m-label">🚛 Active Fleet</div><div class="m-value">{total_trucks} Trucks</div></div>
            <div class="m-card green"><div class="m-label">🛣️ En Route / Diverted</div><div class="m-value">{in_transit} Trucks</div></div>
            <div class="m-card hero"><div class="m-label">⚖️ In-Transit Payload</div><div class="m-value">{tot_payload/1000:.2f} Tons</div></div>
            <div class="m-card purple"><div class="m-label">📊 Fleet Load %</div><div class="m-value">{fleet_util:.1f}%</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Interactive Vehicle Tracking Map (Folium)
    st.markdown(f'<div class="sec-title">🗺️ LIVE FLEET GPS LOCATIONS & ROUTE VECTORS</div>', unsafe_allow_html=True)

    m = folium.Map(
        location=[12.9650, 77.6050],
        zoom_start=12,
        tiles="CartoDB dark_matter" if palette["bg"] == "#0d131d" else "CartoDB positron",
        prefer_canvas=True,
    )

    # Add Facilities
    for f in facilities:
        folium.Marker(
            location=[f["latitude"], f["longitude"]],
            icon=folium.Icon(color="green" if f["status"] == "online" else "red", icon="industry", prefix="fa"),
            tooltip=f"Plant {f['id']}: {f['name']} ({f['status'].upper()})",
        ).add_to(m)

    # Add Vehicles and Route Lines
    for v in vehicles:
        v_lat = v.get("current_lat") or 12.9716
        v_lon = v.get("current_lon") or 77.5946
        stat = v.get("status", "available")
        vid = v["id"]
        tfid = v.get("target_facility_id", "A")

        if stat == "diverted":
            m_color = "red"
        elif stat == "in_transit":
            m_color = "blue"
        elif stat == "weighbridge":
            m_color = "orange"
        elif stat == "maintenance":
            m_color = "gray"
        else:
            m_color = "green"

        v_popup = f"""
        <div style="font-family:sans-serif; font-size:12px; width:220px;">
            <b>Vehicle: <code>{vid}</code></b><br>
            <b>Driver:</b> {v['driver_name']} ({v['phone']})<br>
            <b>Status:</b> <span style="text-transform:uppercase; color:{m_color};"><b>{stat}</b></span><br>
            <b>Payload:</b> {v['current_payload_kg']:,.0f} / {v['capacity_kg']:,.0f} kg<br>
            <b>Target:</b> Plant {tfid}<br>
            <b>Speed:</b> {v.get('speed_kmh', 0)} km/h | <b>ETA:</b> {v.get('eta_mins', 0)} mins
        </div>
        """

        folium.Marker(
            location=[v_lat, v_lon],
            icon=folium.Icon(color=m_color, icon="truck", prefix="fa"),
            popup=folium.Popup(v_popup, max_width=240),
            tooltip=f"{vid} ({v['driver_name']}) · {stat.upper()}",
        ).add_to(m)

        # Draw Route Line to Target Facility
        if stat in ["in_transit", "diverted"] and tfid in fac_dict:
            tf = fac_dict[tfid]
            line_col = "#ff3856" if stat == "diverted" else "#3b82f6"
            folium.PolyLine(
                locations=[(v_lat, v_lon), (tf["latitude"], tf["longitude"])],
                color=line_col,
                weight=3,
                opacity=0.6,
                dash_array="6, 6" if stat == "diverted" else None,
                tooltip=f"Route: {vid} ➔ Plant {tfid} (ETA {v.get('eta_mins', 10)}m)",
            ).add_to(m)

    st_folium(m, width="100%", height=460)

    # 3. Dynamic Reroute Dispatch Advisor
    st.markdown(f'<div class="sec-title">⚡ REAL-TIME DYNAMIC TURNAROUND DISPATCH ADVISOR</div>', unsafe_allow_html=True)

    divert_candidates = []
    for v in vehicles:
        tfid = v.get("target_facility_id")
        if tfid and tfid in fac_dict:
            tf = fac_dict[tfid]
            if tf["status"] != "online" or (tf["current_load_kg"] >= tf["capacity_kg"]):
                divert_candidates.append(v)

    if divert_candidates:
        st.markdown(
            f"""<div class="wg-status red">
                🚨 <b>Bottleneck Alert:</b> {len(divert_candidates)} vehicle(s) currently dispatched to offline
                or overloaded facilities. WasteGrid dynamic turnaround diversion recommended below!
            </div>""",
            unsafe_allow_html=True,
        )

        for dv in divert_candidates:
            col_d1, col_d2, col_d3 = st.columns([2, 2, 1])
            with col_d1:
                st.markdown(f"<b>Vehicle:</b> <code>{dv['id']}</code> ({dv['driver_name']}) · Payload: {dv['current_payload_kg']:,.0f} kg ({dv['waste_type'].upper()})")
            with col_d2:
                # Suggest alternate online facility
                avail_facs = [f for f in facilities if f["status"] == "online" and (f["accepts"] == dv["waste_type"] or f["accepts"] == "mixed")]
                rec_fid = avail_facs[0]["id"] if avail_facs else "A"
                st.markdown(f"Blocked Target: Plant {dv['target_facility_id']} ➔ <b>Recommended Divert: Plant {rec_fid}</b>")
            with col_d3:
                if st.button(f"Reroute ➔", key=f"btn_reroute_{dv['id']}"):
                    db.update_vehicle_dispatch(dv["id"], rec_fid, "diverted")
                    st.success(f"Turnaround notice dispatched! {dv['id']} rerouted to Plant {rec_fid}.")
                    st.rerun()
    else:
        st.markdown(
            f"""<div class="wg-status">
                ✅ <b>All Dispatch Routes Nominal:</b> All active trucks are routed to online facilities with available capacity.
            </div>""",
            unsafe_allow_html=True,
        )

    # 4. Fleet Telemetry Register Table
    st.markdown(f'<div class="sec-title">📋 REGISTERED MUNICIPAL VEHICLE FLEET LOG</div>', unsafe_allow_html=True)

    v_rows = []
    for v in vehicles:
        stat = v["status"]
        if stat == "diverted":
            pill = '<span class="fc-pill overflow">⚡ Diverted</span>'
        elif stat == "in_transit":
            pill = '<span class="fc-pill safe">● En Route</span>'
        elif stat == "weighbridge":
            pill = '<span class="fc-pill overflow" style="background:rgba(245,158,11,0.15); color:#f59e0b;">⏳ Weighbridge</span>'
        elif stat == "maintenance":
            pill = '<span class="fc-pill overflow">🛑 Maintenance</span>'
        else:
            pill = '<span class="fc-pill safe">✓ Available</span>'

        pct = (v["current_payload_kg"] / v["capacity_kg"] * 100) if v["capacity_kg"] > 0 else 0

        v_rows.append(
            f"""<tr>
                <td><b><code>{v['id']}</code></b></td>
                <td>{v['driver_name']}</td>
                <td>{v['phone']}</td>
                <td>{v['assigned_zone']}</td>
                <td><b>{v['current_payload_kg']:,.0f} / {v['capacity_kg']:,.0f} kg ({pct:.0f}%)</b></td>
                <td><span style="text-transform:uppercase;">{v['waste_type']}</span></td>
                <td><b>Plant {v.get('target_facility_id', 'N/A')}</b></td>
                <td>{v.get('speed_kmh', 0)} km/h · ETA {v.get('eta_mins', 0)}m</td>
                <td>{pill}</td>
            </tr>"""
        )

    st.markdown(
        f"""<div class="fc-table-wrap">
            <table class="fc-table">
                <thead><tr>
                    <th>Registration</th><th>Driver</th><th>Contact</th><th>Zone</th>
                    <th>Payload / Capacity</th><th>Stream</th><th>Target Plant</th><th>Speed / ETA</th><th>Status</th>
                </tr></thead>
                <tbody>{''.join(v_rows)}</tbody>
            </table>
        </div>""",
        unsafe_allow_html=True,
    )
