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
        cab_html = f"""
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
"""
        st.markdown(cab_html.strip(), unsafe_allow_html=True)

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


def render_truck_driver_dashboard(palette, driver_user=None):
    """
    Dedicated Mobile-First In-Cab Logistics Portal for Municipal Compactor Truck Drivers.
    Designed like Uber Driver / Blinkit Partner Apps:
    - Live On-Duty / Off-Duty toggle
    - Active Assigned Vehicle & Ward Corridor
    - Real-Time Turn-by-Turn GPS Navigation Simulation
    - Onboard Hydraulic Scale & Waste Load Gauge
    - Security OTP & Digital Weighbridge Gate Pass verification
    - Citizen Grievance Task Clearance (Direct integration with Citizen Module)
    - Dynamic Central Dispatch Siren / Rerouting alerts
    """
    p = palette
    is_light = (p.get("name") == "light")

    card_surface = p.get("card_bg", "#ffffff")
    inner_surface = p.get("bg_soft", "#e2e7ef") if is_light else "rgba(255,255,255,0.04)"
    border_col = p.get("border", "#dbe3ec")
    text_main = p.get("text", "#0f172a")
    text_muted = p.get("muted", "#64748b")
    blue_accent = p.get("blue", "#0284c7")
    success_accent = p.get("success", "#16a34a")
    warn_accent = p.get("warn", "#d97706")
    shadow_effect = p.get("shadow", "0 2px 8px rgba(0,0,0,0.06)")

    if "driver_on_duty" not in st.session_state:
        st.session_state.driver_on_duty = True
    if "driver_payload_kg" not in st.session_state:
        st.session_state.driver_payload_kg = 4200.0
    if "driver_runs_completed" not in st.session_state:
        st.session_state.driver_runs_completed = 2
    if "driver_rerouted" not in st.session_state:
        st.session_state.driver_rerouted = False
    if "driver_weighbridge_done" not in st.session_state:
        st.session_state.driver_weighbridge_done = False
    if "driver_blackspot_cleared" not in st.session_state:
        st.session_state.driver_blackspot_cleared = False

    driver_name = driver_user.get("full_name") if driver_user else "Ramesh Kumar"
    vehicle_reg = "KA-01-EA-101"
    assigned_zone = "Central Zone (Ward 112 Domlur)"
    gate_otp = "7492"

    duty_color = success_accent if st.session_state.driver_on_duty else "#ef4444"
    duty_text = "🟢 ACTIVE ON-DUTY (SHIFT 06:00 - 14:00)" if st.session_state.driver_on_duty else "🔴 OFF-DUTY / REST BREAK"
    banner_bg = f"linear-gradient(135deg, {card_surface} 0%, {inner_surface} 100%)"
    duty_badge_bg = "rgba(22,163,74,0.12)" if st.session_state.driver_on_duty else "rgba(239,68,68,0.12)"

    banner_html = f"""
<div style="background:{banner_bg}; border:2px solid {duty_color}; border-radius:14px; padding:18px 22px; margin-bottom:20px; color:{text_main}; box-shadow:{shadow_effect};">
<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
<div>
<div style="font-size:0.75rem; color:{duty_color}; font-weight:800; letter-spacing:0.15em; text-transform:uppercase;">
🚚 IN-CAB DRIVER PARTNER MDT · v2.4 (LIVE TELEMETRY)
</div>
<div style="font-size:1.6rem; font-weight:900; letter-spacing:-0.02em; margin-top:2px; color:{text_main};">
{vehicle_reg} · {driver_name}
</div>
<div style="font-size:0.8rem; color:{text_muted}; margin-top:4px;">
{assigned_zone} · High-Density Hydraulic Compactor (5.0 MT Capacity)
</div>
</div>
<div style="text-align:right;">
<div style="display:inline-block; background:{duty_badge_bg}; border:1.5px solid {duty_color}; border-radius:8px; padding:6px 14px; font-size:0.8rem; font-weight:800; color:{duty_color};">
{duty_text}
</div>
<div style="font-size:0.7rem; color:{text_muted}; margin-top:6px;">
📶 4G Cellular Linked · GNSS Fix: ±1.2m Accuracy
</div>
</div>
</div>
</div>
"""
    st.markdown(banner_html.strip(), unsafe_allow_html=True)

    q_col1, q_col2, q_col3, q_col4 = st.columns([1, 1, 1.2, 1.2])
    with q_col1:
        if st.session_state.driver_on_duty:
            if st.button("⏸️ Take Rest / Go Off-Duty", key="drv_toggle_duty", use_container_width=True):
                st.session_state.driver_on_duty = False
                st.rerun()
        else:
            if st.button("▶️ Resume Active Collection", key="drv_resume_duty", type="primary", use_container_width=True):
                st.session_state.driver_on_duty = True
                st.rerun()
    with q_col2:
        if st.button("🔄 Reset Shift Simulation", key="drv_reset_sim", use_container_width=True):
            st.session_state.driver_payload_kg = 4200.0
            st.session_state.driver_rerouted = False
            st.session_state.driver_weighbridge_done = False
            st.session_state.driver_blackspot_cleared = False
            st.toast("Simulation state reset to standard active collection run!")
            st.rerun()
    with q_col3:
        if st.session_state.driver_payload_kg <= 5000.0:
            if st.button("⚡ Simulate Overload (+1,200 kg)", key="drv_overload_sim", use_container_width=True, help="Simulate truck picking up extra unexpected waste"):
                st.session_state.driver_payload_kg = 5400.0
                st.session_state.driver_rerouted = True
                st.toast("⚠️ Scale telemetry triggered: 5,400 kg recorded! Dynamic LP diversion initiated.")
                st.rerun()
        else:
            if st.button("↩️ Revert Normal Load (4,200 kg)", key="drv_normal_load", use_container_width=True):
                st.session_state.driver_payload_kg = 4200.0
                st.session_state.driver_rerouted = False
                st.rerun()
    with q_col4:
        if st.button("📞 1-Tap Call Zonal Dispatch", key="drv_call_dispatch", use_container_width=True, help="Direct radio/telephony hotline to Central Control Room"):
            st.toast("📞 Connecting Driver Ramesh Kumar to Central Dispatch Shift Officer (BBMP Command: +91 80 2266 0000)... Connected!")

    if st.session_state.driver_rerouted:
        siren_bg = "rgba(239,68,68,0.08)" if is_light else "rgba(239,68,68,0.2)"
        is_overload = (st.session_state.driver_payload_kg > 5000.0)
        reroute_title = "CENTRAL DISPATCH DIVERSION ORDER: OVERLOAD SURGE DETECTED" if is_overload else "CENTRAL DISPATCH DIVERSION ORDER PUSHED"
        reroute_desc = (
            f"<b>⚠️ Hydraulic Load-Cell Telemetry:</b> Onboard scale registered <b>{st.session_state.driver_payload_kg:,.0f} kg</b> (exceeds rated 5.0 MT). "
            f"WasteGrid LP optimizer automatically rerouted truck from congested Plant A to <b>Facility B (High-Capacity Anaerobic Digester & Biogas)</b> to prevent dock refusal. "
            f"<br><i>No manual CSV upload or phone call needed — IoT sensor synced automatically with municipal grid!</i>"
        ) if is_overload else (
            "Plant A (Biocompost) intake hopper queue exceeded 85%. <b>Diverting vehicle to Facility B (Anaerobic Digester & Biogas)</b>. "
            "Turn RIGHT at Domlur Ring Road Flyover. New ETA: 14 mins."
        )

        st.markdown(
            f"""
<div style="background:{siren_bg}; border:2px solid #ef4444; border-radius:12px; padding:16px 20px; margin:16px 0; color:{text_main};">
<div style="display:flex; align-items:center; gap:12px;">
<span style="font-size:1.8rem;">🚨</span>
<div>
<div style="font-size:1.05rem; font-weight:800; color:#ef4444; text-transform:uppercase;">
{reroute_title}
</div>
<div style="font-size:0.85rem; color:{text_main}; margin-top:2px;">
{reroute_desc}
</div>
</div>
</div>
</div>
""",
            unsafe_allow_html=True,
        )

    c_left, c_right = st.columns([1.3, 1], gap="medium")

    with c_left:
        curr_dest = "Facility B: Anaerobic Digester & Biogas" if st.session_state.driver_rerouted else "Facility A: Organic Biocompost Plant"
        curr_eta = "14 Mins (Surge Detour)" if st.session_state.driver_rerouted else "9 Mins (Direct Route)"
        curr_dist = "5.2 km" if st.session_state.driver_rerouted else "3.6 km"
        load_pct = min(100.0, (st.session_state.driver_payload_kg / 5000.0) * 100)
        load_color = success_accent if load_pct < 75 else (warn_accent if load_pct < 90 else "#ef4444")

        mission_html = f"""
<div style="background:{card_surface}; border:1.5px solid {border_col}; border-radius:14px; padding:20px; color:{text_main}; margin-bottom:18px; box-shadow:{shadow_effect};">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
<div style="font-size:0.8rem; font-weight:800; color:{blue_accent}; text-transform:uppercase; letter-spacing:0.1em;">
🎯 ACTIVE LOGISTICS MISSION
</div>
<span style="background:rgba(2,132,199,0.12); color:{blue_accent}; padding:3px 10px; border-radius:6px; font-size:0.75rem; font-weight:700;">
RUN #{st.session_state.driver_runs_completed + 1} OF 4
</span>
</div>

<div style="font-size:1.35rem; font-weight:900; color:{text_main}; margin-bottom:6px;">
➔ {curr_dest}
</div>
<div style="font-size:0.8rem; color:{text_muted}; margin-bottom:16px;">
Stream: <b style="color:{success_accent}; text-transform:uppercase;">WET BIODEGRADABLE WASTE</b> · Origin: Ward 112 Micro-Collector Points
</div>

<div style="background:{inner_surface}; border:1px solid {border_col}; border-radius:10px; padding:14px; margin-bottom:16px;">
<div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:6px;">
<span style="color:{text_main}; font-weight:600;">Hydraulic Scale Payload</span>
<span style="font-weight:800; color:{load_color};">{st.session_state.driver_payload_kg:,.0f} kg / 5,000 kg ({load_pct:.1f}%)</span>
</div>
<div style="background:{border_col}; border-radius:6px; height:10px; overflow:hidden;">
<div style="background:{load_color}; width:{load_pct}%; height:100%; transition:width 0.5s ease;"></div>
</div>
</div>

<div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; text-align:center;">
<div style="background:{inner_surface}; border:1px solid {border_col}; border-radius:8px; padding:10px;">
<div style="font-size:0.68rem; color:{text_muted}; font-weight:700;">DISTANCE</div>
<div style="font-size:1.15rem; font-weight:800; color:{text_main};">{curr_dist}</div>
</div>
<div style="background:{inner_surface}; border:1px solid {border_col}; border-radius:8px; padding:10px;">
<div style="font-size:0.68rem; color:{text_muted}; font-weight:700;">GATE ETA</div>
<div style="font-size:1.15rem; font-weight:800; color:{warn_accent};">{curr_eta}</div>
</div>
<div style="background:{inner_surface}; border:1px solid {border_col}; border-radius:8px; padding:10px;">
<div style="font-size:0.68rem; color:{text_muted}; font-weight:700;">TRANSIT SPEED</div>
<div style="font-size:1.15rem; font-weight:800; color:{blue_accent};">34 km/h</div>
</div>
</div>
</div>
"""
        st.markdown(mission_html.strip(), unsafe_allow_html=True)

        st.markdown(f'<div class="sec-title">📍 ASSIGNED RAPID-RESPONSE PICKUP</div>', unsafe_allow_html=True)
        ticket_stat_color = success_accent if st.session_state.driver_blackspot_cleared else warn_accent
        ticket_status_text = "CLEARED & COMPACTED" if st.session_state.driver_blackspot_cleared else "PENDING PICKUP"

        task_html = f"""
<div style="background:{card_surface}; border:1px solid {border_col}; border-left:4px solid {ticket_stat_color}; border-radius:10px; padding:16px; margin-bottom:16px; box-shadow:{shadow_effect};">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
<div><b>Ticket #WG-REP-2026-153F</b> · <span style="font-size:0.8rem; font-weight:700;">Overflowing Dumpster</span></div>
<span style="font-size:0.75rem; font-weight:800; color:{ticket_stat_color};">● {ticket_status_text}</span>
</div>
<div style="font-size:0.82rem; color:{text_main}; margin-bottom:4px;">
<b>Location:</b> Indiranagar 12th Main Junction (Ward 112)
</div>
<div style="font-size:0.78rem; color:{text_muted}; margin-bottom:12px;">
Citizen report: Commercial market packaging waste overflowing onto sidewalk. High priority.
</div>
</div>
"""
        st.markdown(task_html.strip(), unsafe_allow_html=True)

        if not st.session_state.driver_blackspot_cleared:
            if st.button("🧹 Clear Blackspot & Log Compaction Proof", key="drv_clear_ticket", type="primary", use_container_width=True):
                st.session_state.driver_blackspot_cleared = True
                try:
                    reps = db.get_all_citizen_reports()
                    for r in reps:
                        if "153" in r.get("tracking_id", ""):
                            db.update_citizen_report_status(r["id"], "resolved", assigned_to="KA-01-EA-101 (Ramesh Kumar)", resolution_notes="Dumpster fully cleared and compacted by Compactor KA-01-EA-101.")
                except Exception:
                    pass
                st.success("✅ Blackspot ticket marked RESOLVED! Municipal dispatch log updated.")
                st.rerun()
        else:
            st.info("✅ Grievance verified and cleared. Photo manifest submitted to Zonal Sanitary Inspector.")

    with c_right:
        st.markdown(f'<div class="sec-title">🔐 DIGITAL WEIGHBRIDGE GATE PASS & OTP</div>', unsafe_allow_html=True)

        wb_status_color = success_accent if st.session_state.driver_weighbridge_done else blue_accent
        wb_status_txt = "GATE ENTRY APPROVED · NET TARE VERIFIED" if st.session_state.driver_weighbridge_done else "READY FOR WEIGHBRIDGE CHECK-IN"

        otp_html = f"""
<div style="background:{card_surface}; border:2px solid {wb_status_color}; border-radius:14px; padding:20px; color:{text_main}; text-align:center; margin-bottom:16px; box-shadow:{shadow_effect};">
<div style="font-size:0.7rem; color:{text_muted}; text-transform:uppercase; letter-spacing:0.12em; font-weight:800;">
SECURITY BOOM BARRIER PASS
</div>
<div style="font-size:1.25rem; font-weight:900; color:{blue_accent}; margin:6px 0;">
WG-PASS-2026-101
</div>

<div style="background:{inner_surface}; border:1px solid {border_col}; border-radius:10px; padding:14px; margin:14px 0;">
<div style="font-size:0.72rem; color:{text_muted}; font-weight:700; margin-bottom:4px;">DRIVER SECURITY ENTRY OTP (UBER-STYLE)</div>
<div style="font-size:2.4rem; font-weight:900; letter-spacing:0.25em; color:{success_accent}; font-family:monospace;">
{gate_otp}
</div>
<div style="font-size:0.7rem; color:{text_muted}; margin-top:2px;">Show or speak this OTP at the plant entry weighbridge sensor</div>
</div>

<div style="font-size:0.78rem; color:{wb_status_color}; font-weight:800;">
● {wb_status_txt}
</div>
</div>
"""
        st.markdown(otp_html.strip(), unsafe_allow_html=True)

        if not st.session_state.driver_weighbridge_done:
            if st.button("⚖️ 1. Check-In at Weighbridge (Verify OTP)", key="drv_wb_checkin", use_container_width=True):
                st.session_state.driver_weighbridge_done = True
                st.toast("✅ Gate weighbridge verified: Gross Weight 8,420 kg · Tare 4,220 kg · Net Waste 4,200 kg recorded!")
                st.rerun()
        else:
            audit_bg = "rgba(22,163,74,0.08)" if is_light else "rgba(16,185,129,0.18)"
            st.markdown(
                f"""
<div style="background:{audit_bg}; border:1.5px solid {success_accent}; border-radius:8px; padding:12px 14px; font-size:0.8rem; color:{text_main}; margin-bottom:12px;">
<b>Weighbridge Audit Log:</b><br>
• Gross Vehicle Weight: <b>8,420 kg</b><br>
• Tare (Unladen) Weight: <b>4,220 kg</b><br>
• Net Waste Accepted: <b>4,200 kg</b><br>
• Boom Barrier: <span style="color:{success_accent}; font-weight:800;">OPEN (BAY #2)</span>
</div>
""",
                unsafe_allow_html=True,
            )

            if st.session_state.driver_payload_kg > 0:
                if st.button("🚜 2. Unload Payload at Hopper & Complete Run", key="drv_unload_payload", type="primary", use_container_width=True):
                    st.session_state.driver_payload_kg = 0.0
                    st.session_state.driver_runs_completed += 1
                    st.session_state.driver_weighbridge_done = False
                    st.balloons()
                    st.success("🎉 Payload successfully discharged into Biocompost Hopper! Run #3 logged in central municipal ledger.")
                    st.rerun()
            else:
                st.success("✨ Hopper discharge complete! Truck empty and ready for next ward pickup cycle.")
                if st.button("🚚 Start Next Ward Collection Cycle", key="drv_next_cycle", use_container_width=True):
                    st.session_state.driver_payload_kg = 4200.0
                    st.session_state.driver_rerouted = False
                    st.session_state.driver_blackspot_cleared = False
                    st.session_state.driver_weighbridge_done = False
                    st.rerun()
