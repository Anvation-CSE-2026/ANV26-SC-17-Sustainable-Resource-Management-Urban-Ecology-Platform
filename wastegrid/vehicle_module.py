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
        tiles="OpenStreetMap",
        prefer_canvas=True,
    )
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri",
        name="Esri World Streets",
        control=True,
    ).add_to(m)

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

    folium.LayerControl(position="topright").add_to(m)
    st_folium(m, use_container_width=True, height=480, returned_objects=[])

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

    # 4. Tri-Party Medium: How Driver, Commissioner, and Plant Synchronize
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f'<div class="sec-title">📡 THE TRI-PARTY SYNCHRONIZATION MEDIUM (COMMISSIONER ➔ DRIVER ➔ PLANT)</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="background:{p['card_bg']}; border:1.5px solid {p['blue']}; border-radius:12px; padding:20px 24px; margin-bottom:20px; box-shadow:{p['shadow']};">
            <div style="font-size:1.1rem; font-weight:800; color:{p['text']}; margin-bottom:8px;">
                🔄 How the Truck Driver Knows Which Destination to Go to: The Closed-Loop Medium
            </div>
            <div style="font-size:0.83rem; color:{p['muted']}; line-height:1.7; margin-bottom:14px;">
                Municipal waste logistics requires instant, tamper-proof coordination across three distinct stakeholders. 
                WasteGrid connects them through an automated closed-loop digital pipeline:
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px; margin-bottom:12px;">
                <div style="background:{p['bg_soft']}; border:1px solid {p['border']}; border-radius:10px; padding:16px;">
                    <div style="font-size:0.75rem; font-weight:800; color:{p['blue']}; text-transform:uppercase; margin-bottom:4px;">1. The Municipal Commissioner</div>
                    <div style="font-size:0.95rem; font-weight:800; color:{p['text']}; margin-bottom:6px;">Central LP Allocation Engine</div>
                    <div style="font-size:0.77rem; color:{p['muted']}; line-height:1.6;">
                        Runs the Linear Programming solver to calculate citywide mass-balance, avoid facility overload, and issue real-time digital manifests.
                    </div>
                </div>
                <div style="background:{p['bg_soft']}; border:1px solid {p['border']}; border-radius:10px; padding:16px;">
                    <div style="font-size:0.75rem; font-weight:800; color:{p['success']}; text-transform:uppercase; margin-bottom:4px;">2. The Truck Driver</div>
                    <div style="font-size:0.95rem; font-weight:800; color:{p['text']}; margin-bottom:6px;">In-Cab MDT / Driver App (PWA)</div>
                    <div style="font-size:0.77rem; color:{p['muted']}; line-height:1.6;">
                        Connected via 4G cellular IoT. Receives automated turn-by-turn GPS route manifests and instant audible diversion orders if a plant queues up.
                    </div>
                </div>
                <div style="background:{p['bg_soft']}; border:1px solid {p['border']}; border-radius:10px; padding:16px;">
                    <div style="font-size:0.75rem; font-weight:800; color:{p['purple']}; text-transform:uppercase; margin-bottom:4px;">3. The Processing Plant Manager</div>
                    <div style="font-size:0.95rem; font-weight:800; color:{p['text']}; margin-bottom:6px;">Automated Weighbridge ERP</div>
                    <div style="font-size:0.77rem; color:{p['muted']}; line-height:1.6;">
                        Scans inbound RFID / ANPR windshield tags at the entry gate, validates waste stream, auto-logs tare/gross weights, and confirms delivery.
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 5. Interactive In-Cab Mobile Driver Terminal Simulator
    st.markdown(f'<div class="sec-title">📱 IN-CAB TRUCK DRIVER TERMINAL (LIVE SIMULATOR)</div>', unsafe_allow_html=True)
    driver_truck_options = [f"{v['id']} — {v['driver_name']} ({v['assigned_zone']})" for v in vehicles]
    sel_driver_truck = st.selectbox("Select Truck to View In-Cab Driver Tablet Display:", driver_truck_options)
    
    selected_v_id = sel_driver_truck.split(" — ")[0]
    matched_v = next((v for v in vehicles if v["id"] == selected_v_id), vehicles[0])
    target_fac = fac_dict.get(matched_v.get("target_facility_id", "A"), {"name": "Facility A (Biocompost)", "status": "online"})

    col_cab_left, col_cab_right = st.columns([1.3, 1], gap="large")
    with col_cab_left:
        st.markdown(
            f"""
            <div style="background:#090d16; border:3px solid #10b981; border-radius:16px; padding:20px; color:#ffffff; font-family:monospace; box-shadow:0 8px 30px rgba(0,0,0,0.6);">
                <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.15); padding-bottom:10px; margin-bottom:14px;">
                    <span style="font-size:0.9rem; font-weight:800; color:#10b981;">📶 4G LTE CONNECTED · GPS LOCK</span>
                    <span style="font-size:0.8rem; background:rgba(16,185,129,0.2); padding:3px 10px; border-radius:6px; color:#10b981;">IN-CAB MDT v2.4</span>
                </div>
                <div style="font-size:1.4rem; font-weight:900; margin-bottom:4px; letter-spacing:-0.02em;">
                    {matched_v['id']} · {matched_v['driver_name']}
                </div>
                <div style="font-size:0.85rem; color:#94a3b8; margin-bottom:16px;">
                    Assigned Collection Zone: <b>{matched_v['assigned_zone']}</b>
                </div>

                <div style="background:rgba(255,255,255,0.05); border-radius:10px; padding:14px; margin-bottom:14px;">
                    <div style="font-size:0.75rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.1em;">CURRENT ROUTE DESTINATION</div>
                    <div style="font-size:1.2rem; font-weight:800; color:#38bdf8; margin:4px 0;">
                        ➔ {target_fac.get('name', 'Facility A')}
                    </div>
                    <div style="font-size:0.8rem; color:#cbd5e1;">
                        Stream: <b style="text-transform:uppercase; color:#10b981;">{matched_v['waste_type']} WASTE</b> · Current Payload: <b>{matched_v['current_payload_kg']:,.0f} kg</b>
                    </div>
                </div>

                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:16px;">
                    <div style="background:rgba(255,255,255,0.04); padding:10px; border-radius:8px; text-align:center;">
                        <div style="font-size:0.7rem; color:#94a3b8;">TRANSIT SPEED</div>
                        <div style="font-size:1.3rem; font-weight:800;">{matched_v.get('speed_kmh', 34)} km/h</div>
                    </div>
                    <div style="background:rgba(255,255,255,0.04); padding:10px; border-radius:8px; text-align:center;">
                        <div style="font-size:0.7rem; color:#94a3b8;">PLANT GATE ETA</div>
                        <div style="font-size:1.3rem; font-weight:800; color:#f59e0b;">{matched_v.get('eta_mins', 12)} Mins</div>
                    </div>
                </div>

                <div style="background:rgba(16,185,129,0.1); border:1px dashed #10b981; border-radius:8px; padding:10px; text-align:center; font-size:0.78rem;">
                    <b>DIGITAL WEIGHBRIDGE GATE PASS:</b> <code>WG-PASS-2026-{matched_v['id'][-4:]}</code>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_cab_right:
        st.markdown(
            f"""
            <div style="background:{p['card_bg']}; border:1px solid {p['border']}; border-radius:14px; padding:20px; box-shadow:{p['shadow']};">
                <div style="font-size:1.05rem; font-weight:800; color:{p['text']}; margin-bottom:8px;">
                    ⚡ Dynamic Turnaround & Rerouting
                </div>
                <div style="font-size:0.8rem; color:{p['muted']}; line-height:1.6; margin-bottom:16px;">
                    When a facility queues beyond 85% or enters unexpected maintenance, Central Command pushes an instant audible diversion command to the driver's cab.
                </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("📢 Simulate Emergency In-Cab Reroute Alert", key="btn_sim_divert", use_container_width=True):
            st.warning(
                f"🚨 **IN-CAB DIVERSION NOTICE PUSHED TO {matched_v['id']}:**\n\n"
                f"Facility {matched_v.get('target_facility_id', 'A')} experiencing intake congestion.\n"
                f"**Rerouted to Facility B (Anaerobic Digester)** — Turn right at Outer Ring Road junction. ETA +4 mins."
            )
        st.markdown("</div>", unsafe_allow_html=True)
