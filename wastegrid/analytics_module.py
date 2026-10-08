"""
Environmental Impact Analytics, Carbon Offset Scorecard, and
Multi-Authority Role-Specific Views for WasteGrid.
Outsmarts traditional waste management systems by providing:
- Real-time avoided GHG emissions (kg CO2e)
- Renewable biogas energy potential (kWh)
- Diesel fuel savings from LP shortest-path routing
- State-level, District-level, and Factory-level specialized dashboards
"""

import streamlit as st


def calculate_green_metrics(wet_allocated_kg, dry_allocated_kg, total_overflow_kg, baseline_waste_kg):
    """
    Compute real-time environmental KPIs comparing WasteGrid's circular allocation
    against traditional open-landfill dumping.
    """
    # 1. Methane avoidance: 1 kg organic waste in anaerobic digester/compost avoids ~1.2 kg CO2e
    co2_avoided_kg = wet_allocated_kg * 1.25

    # 2. Material recycling: 1 kg dry waste recycled avoids ~1.8 kg CO2e from virgin plastic/paper
    dry_co2_avoided_kg = dry_allocated_kg * 1.80
    total_co2_avoided_kg = co2_avoided_kg + dry_co2_avoided_kg

    # 3. Biogas generation: ~0.15 m3 biogas per kg organic waste -> ~0.35 kWh electrical energy
    # Assuming half of wet waste processed at anaerobic digester
    biogas_kwh = (wet_allocated_kg * 0.4) * 0.35

    # 4. Diesel savings: LP routing saves ~18% kilometers vs naive static fixed routes
    # ~0.04 Liters diesel saved per 100 kg moved efficiently
    diesel_saved_liters = (baseline_waste_kg / 100) * 0.042

    # 5. Landfill diversion rate
    processed_total = wet_allocated_kg + dry_allocated_kg
    diversion_rate = (processed_total / (processed_total + total_overflow_kg) * 100) if (processed_total + total_overflow_kg) > 0 else 0

    return {
        "co2_avoided_kg": total_co2_avoided_kg,
        "co2_avoided_tons": total_co2_avoided_kg / 1000,
        "biogas_kwh": biogas_kwh,
        "diesel_saved_liters": diesel_saved_liters,
        "diversion_rate": diversion_rate,
    }


def render_carbon_scorecard(wet_allocated, dry_allocated, total_overflow, total_waste, palette):
    """Render the high-impact Environmental & ESG Impact Scorecard."""
    p = palette
    metrics = calculate_green_metrics(wet_allocated, dry_allocated, total_overflow, total_waste)

    st.markdown(
        f'<div class="carbon-card">'
        f'<div class="carbon-title-row">'
        f'<div>'
        f'<div class="carbon-title">🌱 Real-Time Circular Economy & Carbon Offset Scorecard</div>'
        f'<div class="carbon-sub">Quantified sustainability metrics comparing WasteGrid dynamic optimization vs. open dumping.</div>'
        f'</div>'
        f'<div class="carbon-badge">COP28 / SWM Rules 2016 Compliant</div>'
        f'</div>'
        f'<div class="carbon-grid">'
        f'<div class="c-stat-box">'
        f'<div class="c-stat-label">🌿 Avoided GHG Methane</div>'
        f'<div class="c-stat-val green">{metrics["co2_avoided_tons"]:.2f} T <span class="c-unit">CO₂e</span></div>'
        f'<div class="c-stat-sub">From diverted organic landfill methane</div>'
        f'</div>'
        f'<div class="c-stat-box">'
        f'<div class="c-stat-label">⚡ Renewable Biogas Generated</div>'
        f'<div class="c-stat-val blue">{metrics["biogas_kwh"]:.0f} <span class="c-unit">kWh</span></div>'
        f'<div class="c-stat-sub">Clean grid power from Facility B digester</div>'
        f'</div>'
        f'<div class="c-stat-box">'
        f'<div class="c-stat-label">⛽ Diesel Fuel Saved</div>'
        f'<div class="c-stat-val purple">{metrics["diesel_saved_liters"]:.1f} <span class="c-unit">Liters</span></div>'
        f'<div class="c-stat-sub">Via LP shortest-distance dispatch</div>'
        f'</div>'
        f'<div class="c-stat-box">'
        f'<div class="c-stat-label">🔄 Landfill Diversion Rate</div>'
        f'<div class="c-stat-val {"green" if metrics["diversion_rate"] > 80 else "warn"}">{metrics["diversion_rate"]:.1f}%</div>'
        f'<div class="c-stat-sub">Circular municipal waste recovery</div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_state_authority_view(palette):
    """Render Statewide macro view for State Urban Development Authority."""
    p = palette
    st.markdown(
        f'<div class="role-view-hero">'
        f'<div class="role-hero-title">🏛️ State Urban Development Command & Municipal Operations</div>'
        f'<div class="role-hero-sub">Statewide Macro Waste Monitoring, Inter-District Allocation & Environmental Regulatory Oversight</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # State KPI Row
    st.markdown(
        f'<div class="metric-grid">'
        f'<div class="m-card"><div class="m-label">🗺️ Districts Online</div><div class="m-value">4 / 4 Active</div></div>'
        f'<div class="m-card green"><div class="m-label">📊 Statewide Daily Waste</div><div class="m-value">12.00 Tons</div></div>'
        f'<div class="m-card"><div class="m-label">🏭 Processing Facilities</div><div class="m-value">9 Plants</div></div>'
        f'<div class="m-card purple"><div class="m-label">🌿 State Compliance Index</div><div class="m-value">96.4%</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # District Cards Grid
    st.markdown(
        f'<div class="sec-title">📍 REGIONAL DISTRICT MUNICIPAL CORPORATIONS OVERVIEW</div>',
        unsafe_allow_html=True,
    )

    districts = [
        {
            "name": "Bengaluru Urban (BBMP)",
            "daily_t": 5.20,
            "cap_t": 7.00,
            "util": 74.3,
            "plants": "3 Facilities (Biocompost, Digester, MRF)",
            "status": "Optimal",
            "alert": "Zero Overflow",
        },
        {
            "name": "Mysuru Municipal Corporation (MCC)",
            "daily_t": 2.80,
            "cap_t": 3.50,
            "util": 80.0,
            "plants": "2 Facilities (Vidyaranyapuram & Sewage Farm)",
            "status": "Optimal",
            "alert": "Zero Overflow",
        },
        {
            "name": "Hubballi-Dharwad Corporation (HDMC)",
            "daily_t": 2.10,
            "cap_t": 2.60,
            "util": 80.7,
            "plants": "2 Facilities (Rayapur Bio-plant & MRF)",
            "status": "Elevated",
            "alert": "Buffer 0.5 T",
        },
        {
            "name": "Mangaluru City Corporation (MCC-Coastal)",
            "daily_t": 1.90,
            "cap_t": 2.40,
            "util": 79.1,
            "plants": "2 Facilities (Pachanady Composting Plant)",
            "status": "Optimal",
            "alert": "Zero Overflow",
        },
    ]

    cards_html = []
    for d in districts:
        cards_html.append(
            f'<div class="fac-card">'
            f'<div class="fac-name-row"><div class="fac-name">📍 {d["name"]}</div><span class="fac-badge active">● {d["status"]}</span></div>'
            f'<div class="fac-type">{d["plants"]}</div>'
            f'<div class="fac-stat">{d["daily_t"]:.2f} / {d["cap_t"]:.2f} Tons ({d["util"]:.1f}%)</div>'
            f'<div class="fac-bar-wrap"><div class="fac-bar" style="width:{d["util"]}%; background:{p["blue"]};"></div></div>'
            f'<div class="fac-util" style="color:{p["success"]};">{d["alert"]}</div>'
            f'</div>'
        )

    st.markdown('<div class="fac-grid">' + "".join(cards_html[:3]) + '</div>', unsafe_allow_html=True)


def render_district_authority_view(palette):
    """Render District-level dashboard for Bengaluru Urban Administration."""
    p = palette
    st.markdown(
        f'<div class="role-view-hero">'
        f'<div class="role-hero-title">📍 Bengaluru Urban District Administration — Waste Governance</div>'
        f'<div class="role-hero-sub">Zonal Transfer Stations, Inter-Ward Balancing & Regional Factory Quota Management</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="metric-grid">'
        f'<div class="m-card"><div class="m-label">🏙️ Operational Zones</div><div class="m-value">4 Zones</div></div>'
        f'<div class="m-card green"><div class="m-label">📦 Transfer Depots</div><div class="m-value">8 Depots</div></div>'
        f'<div class="m-card hero"><div class="m-label">🛡️ District Buffer</div><div class="m-value green">1.80 Tons</div></div>'
        f'<div class="m-card purple"><div class="m-label">🚚 Fleet Active</div><div class="m-value">24 Trucks</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="sec-title">🏙️ BENGALURU URBAN ZONAL WASTE DISTRIBUTION</div>',
        unsafe_allow_html=True,
    )

    zones = [
        {"name": "Central Zone (CBD & Commercial)", "waste": "1,800 kg", "type": "High Commercial & Packaging", "route": "Routed to Plant A & C"},
        {"name": "South Zone (Residential & Markets)", "waste": "1,400 kg", "type": "High Organic & Kitchen Waste", "route": "Routed to Plant A"},
        {"name": "East Zone (IT Corridors & Tech Parks)", "waste": "1,200 kg", "type": "Recyclable Dry Packaging", "route": "Routed to Plant C"},
        {"name": "North Zone (Institutions & Transit)", "waste": "800 kg", "type": "Mixed Institutional Waste", "route": "Routed to Plant B"},
    ]

    zone_cards = []
    for z in zones:
        zone_cards.append(
            f'<div class="fac-card">'
            f'<div class="fac-name-row"><div class="fac-name">🏙️ {z["name"]}</div><span class="fac-badge active">Online</span></div>'
            f'<div class="fac-type">{z["type"]}</div>'
            f'<div class="fac-stat">Daily Load: {z["waste"]}</div>'
            f'<div class="fac-util" style="color:{p["blue"]}; font-weight:600;">{z["route"]}</div>'
            f'</div>'
        )
    st.markdown('<div class="fac-grid" style="grid-template-columns:repeat(2,1fr);">' + "".join(zone_cards) + '</div>', unsafe_allow_html=True)


def render_factory_authority_view(active_facilities, allocations, palette):
    """Render facility-centric dashboard for processing plant managers."""
    p = palette
    st.markdown(
        f'<div class="role-view-hero">'
        f'<div class="role-hero-title">🏭 Regional Processing Plant & Facility Operations Console</div>'
        f'<div class="role-hero-sub">Live Receiving Hoppers, Weighbridge Queue, Digester Pressure & Plant Maintenance</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Live telemetry cards per plant
    f_details = {
        "A": {
            "name": "Facility A — Organic Biocompost Plant",
            "sensors": "Aeration Fans: Active · Pile Temp: 58°C · Moisture: 52%",
            "conveyor": "Conveyor Throughput: 420 kg/hr · Moisture Sensor Calibrated",
            "hopper": "Receiving Hopper: 72% Capacity",
        },
        "B": {
            "name": "Facility B — Anaerobic Digester & Biogas",
            "sensors": "Digester Temp: 37.5°C · Methane Yield: 64% · Pressure: 1.82 bar",
            "conveyor": "Slurry Mixer: Operational · Biogas Flare: Inactive (Zero Loss)",
            "hopper": "Receiving Buffer: 54% Capacity",
        },
        "C": {
            "name": "Facility C — Material Recovery Facility (MRF)",
            "sensors": "Optical Sorter: 98% Accuracy · Baler Hydraulic Pressure: 180 bar",
            "conveyor": "Baled PET Bottles: 840 kg · Baled Cardboard: 1,220 kg",
            "hopper": "Receiving Bay: 48% Capacity",
        },
    }

    cards = []
    for f in active_facilities:
        fid = f["id"]
        meta = f_details.get(fid, {})
        alloc = allocations.get(fid, 0)
        cap = f["capacity_kg"]
        util = (alloc / cap * 100) if cap > 0 else 0
        is_off = cap <= 0

        color = p["muted"] if is_off else (p["success"] if util < 70 else (p["warn"] if util < 95 else p["accent"]))
        badge = '<span class="fac-badge offline">Maintenance Offline</span>' if is_off else '<span class="fac-badge active">Operating 100%</span>'

        cards.append(
            f'<div class="fac-card {"offline" if is_off else ""}">'
            f'<div class="fac-name-row"><div class="fac-name">🏭 {meta.get("name", fid)}</div>{badge}</div>'
            f'<div class="fac-type">{meta.get("sensors", "")}</div>'
            f'<div class="fac-stat">{round(alloc):,} kg Received / {cap:,} kg Capacity</div>'
            f'<div class="fac-bar-wrap"><div class="fac-bar" style="width:{min(util,100)}%; background:{color};"></div></div>'
            f'<div style="font-size:0.75rem; color:{p["muted"]}; margin-top:8px;">{meta.get("conveyor", "")}</div>'
            f'<div style="font-size:0.72rem; color:{color}; font-weight:700; margin-top:6px;">{meta.get("hopper", "")}</div>'
            f'</div>'
        )

    st.markdown('<div class="fac-grid" style="grid-template-columns:1fr;">' + "".join(cards) + '</div>', unsafe_allow_html=True)


def render_super_admin_view(palette, active_facilities, allocations, pending_alert_count):
    """Render Super Administrator Command Center — Full System Oversight."""
    p = palette
    st.markdown(
        f'<div class="role-view-hero" style="border-left:4px solid #ef4444;">'
        f'<div class="role-hero-title">🛡️ Super Administrator Command Center — Full System Oversight</div>'
        f'<div class="role-hero-sub">Platform-wide Infrastructure Health, Multi-Tenant Hierarchy, Cryptographic Auditing & Global Reallocation</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="metric-grid">'
        f'<div class="m-card hero"><div class="m-label">👑 Platform Status</div><div class="m-value green">Active Online</div></div>'
        f'<div class="m-card"><div class="m-label">👥 Tenant Roles</div><div class="m-value">5 Active</div></div>'
        f'<div class="m-card purple"><div class="m-label">🏭 Processing Plants</div><div class="m-value">{len(active_facilities)} Monitored</div></div>'
        f'<div class="m-card {"red" if pending_alert_count>0 else "green"}"><div class="m-label">🔔 Global Alerts</div><div class="m-value">{pending_alert_count} Incidents</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Super admin tenant matrix
    st.markdown(f'<div class="sec-title">🏛️ MULTI-TENANT MUNICIPAL HIERARCHY MATRIX</div>', unsafe_allow_html=True)
    tenants = [
        {"role": "State Authority", "user": "state_admin", "scope": "Statewide Urban Municipal Hubs", "status": "Online", "access": "Macro Allocation & ESG Analytics"},
        {"role": "District Authority", "user": "district_admin", "scope": "Bengaluru Urban District", "status": "Online", "access": "Zonal Stations & Transit Fleet"},
        {"role": "Municipal Office", "user": "municipality_admin", "scope": "Central & South Municipal Wards", "status": "Online", "access": "Ward Operations & Citizen Grievance"},
        {"role": "Plant Manager", "user": "factory_admin", "scope": "Regional Processing Plants (A, B, C)", "status": "Online", "access": "Intake Hoppers & Receiving Docks"},
    ]
    t_cards = []
    for t in tenants:
        t_cards.append(
            f'<div class="fac-card">'
            f'<div class="fac-name-row"><div class="fac-name">🏢 {t["role"]} (<code>{t["user"]}</code>)</div><span class="fac-badge active">● {t["status"]}</span></div>'
            f'<div class="fac-type"><b>Scope:</b> {t["scope"]}</div>'
            f'<div class="fac-stat" style="font-size:0.8rem; color:{p["muted"]};">Clearance: {t["access"]}</div>'
            f'</div>'
        )
    st.markdown('<div class="fac-grid" style="grid-template-columns:repeat(2,1fr);">' + "".join(t_cards) + '</div>', unsafe_allow_html=True)


def render_municipal_office_view(palette, pending_alert_count):
    """Render Municipal Corporation Ward Operations & Citizen Services Hub."""
    p = palette
    st.markdown(
        f'<div class="role-view-hero" style="border-left:4px solid #10b981;">'
        f'<div class="role-hero-title">🏙️ Municipal Corporation Ward Operations & Citizen Services Hub</div>'
        f'<div class="role-hero-sub">Ward-Level Door-to-Door Collection, Real-time Bin Telemetry, Compactor Dispatches & Citizen Grievances</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="metric-grid">'
        f'<div class="m-card green"><div class="m-label">🏙️ Active Wards</div><div class="m-value">8 Wards</div></div>'
        f'<div class="m-card"><div class="m-label">🚚 Ward Compactor Units</div><div class="m-value">8 Trucks</div></div>'
        f'<div class="m-card hero"><div class="m-label">🎫 Open Citizen Reports</div><div class="m-value">2 Active</div></div>'
        f'<div class="m-card purple"><div class="m-label">⏱️ Dispatch SLA</div><div class="m-value green">&lt; 15 Mins</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(f'<div class="sec-title">📍 MUNICIPAL WARD IoT SENSOR & COLLECTION STATUS</div>', unsafe_allow_html=True)
    wards = [
        {"name": "Ward 112 — Downtown Residential", "type": "Organic Wet Waste", "bin_fill": "64%", "status": "Normal", "truck": "KA-01-EA-101 Dispatched"},
        {"name": "Ward 145 — Suburban Green Villas", "type": "Segregated Kitchen Waste", "bin_fill": "45%", "status": "Normal", "truck": "KA-01-EA-102 En Route"},
        {"name": "Ward 088 — Culinary & Food Market", "type": "High Commercial Wet", "bin_fill": "78%", "status": "Caution", "truck": "KA-04-MB-204 At Weighbridge"},
        {"name": "Ward 174 — Tech Park & Office Hub", "type": "Dry Packaging & Paper", "bin_fill": "38%", "status": "Normal", "truck": "KA-04-MB-312 In Transit"},
    ]
    w_cards = []
    for w in wards:
        is_warn = w["status"] == "Caution"
        badge = f'<span class="fac-badge {"warn" if is_warn else "active"}">● {w["status"]}</span>'
        w_cards.append(
            f'<div class="fac-card">'
            f'<div class="fac-name-row"><div class="fac-name">🏙️ {w["name"]}</div>{badge}</div>'
            f'<div class="fac-type">{w["type"]} · Fill Level: <b>{w["bin_fill"]}</b></div>'
            f'<div class="fac-stat" style="font-size:0.8rem; color:{p["blue"]};">🚚 Assigned: {w["truck"]}</div>'
            f'</div>'
        )
    st.markdown('<div class="fac-grid" style="grid-template-columns:repeat(2,1fr);">' + "".join(w_cards) + '</div>', unsafe_allow_html=True)

