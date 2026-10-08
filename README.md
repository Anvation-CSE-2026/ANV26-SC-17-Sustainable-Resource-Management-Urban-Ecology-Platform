# ♻️ WasteGrid 2.0 — Smart Municipal Operations Dashboard

**Predict. Detect. Reallocate. Dispatch.**  
*Next-Generation Smart Municipal Waste Management & Predictive Resource Reallocation Platform.*

---

## 🌟 Executive Summary

**WasteGrid 2.0** is an enterprise-grade municipal operations platform built for city corporations, urban local bodies (ULBs), and state urban development directorates. While conventional systems focus solely on collection vehicle routing, WasteGrid solves the critical **downstream processing capacity crisis**: dynamically balancing wet and dry waste streams across dynamic processing plants, biogas digesters, MRFs, and waste-to-energy facilities using high-performance Linear Programming (LP) and IoT telemetry.

---

## 🚀 Key Modules & Capabilities

WasteGrid 2.0 features a permanent, collapsible sidebar navigation organizing **17 dedicated operational dashboards**:

1. **📊 Overview Dashboard**: Real-time grid KPIs (generation, processed volume, available capacity, overflow risk, active fleet, alerts, recycling ratio, data mode, stream breakdown, interactive action buttons, facility utilization cards, baseline comparisons, and weekly trends).
2. **🗺️ Live Waste Map & Heatmap**: Interactive GIS console powered by Folium displaying color-coded facility nodes (Green: Online, Yellow: High Load, Orange: Warning, Red: Offline), thermal waste generation density heatmap, and active dispatch vectors.
3. **📈 Waste Analytics Dashboard**: Deep-dive stream composition charts, ward-level generation distributions, tech park vs residential comparisons, and processing balance analytics.
4. **🔮 Waste Forecast**: 7-day predictive demand models accounting for day-of-week occupancy, commercial cycles, weather runoff, and weekend surge ceilings.
5. **🏭 Facility Management**: Dynamic database-backed facility administration with unlimited plants, live capacity editing, stream compatibility controls, maintenance status toggles, and deletion.
6. **⚡ Smart Allocation**: Multi-objective Linear Programming (HiGHS LP) solver supporting four optimization targets:
   - *Minimum Overflow*
   - *Minimum Transportation Cost*
   - *Minimum Carbon Emissions*
   - *Balanced Multi-Objective*  
   Includes before-and-after reallocation metrics and an administrative **Approve & Apply** workflow.
7. **🚚 Vehicle Tracking & Dispatch**: Real-time cellular GPS telematics, hydraulic lifter payload sensing, and dynamic turnaround diversion advising for trucks heading to congested or offline facilities.
8. **📅 Event Calendar**: Predictive holiday, festival, and civic event simulator modeling demand spikes (e.g., Ganeshotsava, Diwali, Bengaluru Tech Summit).
9. **🧪 Scenario Simulator**: Risk-free sandbox enabling city planners to test catastrophic breakdowns, demographic growth (10%–100%), facility outages, and vehicle shortages without mutating operational data.
10. **🔔 Alerts & Notifications**: Automated threshold-driven predictive alert engine (<70% Normal, 70–84% Moderate, 85–94% Warning, ≥95% Critical) with Acknowledge and Resolve operational workflows.
11. **📢 Citizen Reports**: Civic grievance portal where citizens lodge issues (overflowing dumpsters, illegal roadside dumping, missed collections) with unique tracking IDs (`WG-REP-YYYY-XXXX`), and municipal officers assign compactor units and log resolution audits.
12. **🌱 Carbon & ESG Dashboard**: Environmental sustainability accounting measuring landfill methane diversion, diesel emission offsets, and ESG compliance ratings.
13. **🏆 Performance Dashboard**: Municipal SLA scorecard tracking plant uptime ratings, fleet route adherence, and citizen grievance resolution turnaround.
14. **📑 Reports & Exports**: Audit-ready data exports in both **multi-sheet Excel (.xlsx)** and **CSV** formats across all system tables.
15. **👥 User Management (Admin Only)**: Administrative security console to create official accounts, assign roles, toggle account activation, and perform password resets.
16. **⚙️ Settings**: System parameter editor for alert thresholds, optimizer penalty weights, and solver configurations.
17. **👤 Profile & Security**: Official identity inspection, self-service password update, and access to the system audit trail.

---

## 🔐 Security & Role-Based Access Control (RBAC)

WasteGrid 2.0 eliminates all plaintext credentials and bypass buttons. Authentication is database-backed (`wastegrid.db`) using industry-standard **PBKDF2-HMAC-SHA256 with cryptographically unique salts**:

| Role | Username | Initial Password | Scope / Jurisdiction | Clearance |
| :--- | :--- | :--- | :--- | :--- |
| **System Admin** | `admin` | `Admin@123` | Statewide & System Administration | Full access to all 17 dashboards & user governance |
| **State Authority** | `karnataka_admin` | `Waste@123` | Karnataka Urban Development Hubs | Macro state grid, ESG scorecard, policy reports |
| **District Authority** | `district_admin` | `District@123` | Bengaluru Urban District | Inter-municipal allocations, fleet coordination |
| **Municipal Authority** | `municipality_admin` | `Municipality@123` | BBMP Central Municipal Wards | Local ward telemetry, citizen grievance resolution, dispatch |
| **Factory Authority** | `factory_admin` | `Factory@123` | Processing Plants A, B, C & D | Plant capacity, dock queue management, downtime logging |

---

## 🛠️ Technology Architecture

- **Web Framework:** [Streamlit](https://streamlit.io/) with custom responsive CSS design tokens (light & dark mode support).
- **Optimization Engine:** `scipy.optimize.linprog` (HiGHS Simplex & Interior Point Solvers).
- **Geospatial Mapping:** [Folium](https://python-visualization.github.io/folium/) and `streamlit-folium` with Leaflet heatmaps.
- **Visual Analytics:** Plotly Interactive Charts (`plotly.express`, `plotly.graph_objects`) and Altair.
- **Database Engine:** SQLite (PostgreSQL-compatible architecture with parameterized queries and transaction management).
- **Export Formats:** Excel (`openpyxl`) and CSV.
- **Testing:** `pytest` automated test suite.

---

## 💻 Installation & Quickstart

### 1. Clone the repository
```bash
git clone https://github.com/Mokshitha9512/WasteGrid.git
cd WasteGrid
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run automated tests
```bash
python -m pytest tests/test_wastegrid.py -v
```

### 4. Launch the dashboard
```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser. Sign in using any of the official demo accounts above in the left sidebar.

---

## 📜 License
Developed under the Smart Municipal Infrastructure Consortium. All rights reserved.
