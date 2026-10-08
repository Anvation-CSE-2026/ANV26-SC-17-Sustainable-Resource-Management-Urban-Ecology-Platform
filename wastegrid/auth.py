"""
Authentication and Role-Based Access Control (RBAC) for WasteGrid.
Supports multi-authority login matching government and municipal hierarchy:
1. State Authority – Karnataka (karnataka_admin / Waste@123)
2. District Authority (district_admin / District@123)
3. Municipal Authority (municipality_admin / Municipality@123)
4. Processing/Factory Authority (factory_admin / Factory@123)
"""

import streamlit as st

USERS = {
    "karnataka_admin": {
        "password": "Waste@123",
        "role": "state",
        "title": "State Authority – Karnataka",
        "org": "Karnataka Urban Development Department (UDD)",
        "badge": "State Command",
        "icon": "🏛️",
        "jurisdiction": "Statewide (All Districts & Regional Hubs)",
        "access_desc": "View all districts, inter-district waste flow, macro factory capacity, and statewide emergency alerts.",
    },
    "district_admin": {
        "password": "District@123",
        "role": "district",
        "title": "District Authority",
        "org": "Bengaluru Urban District Administration",
        "badge": "District HQ",
        "icon": "📍",
        "jurisdiction": "Bengaluru Urban District (Central, North, South, East)",
        "access_desc": "View and manage waste flow across district transfer stations and monitor regional plant quotas.",
    },
    "municipality_admin": {
        "password": "Municipality@123",
        "role": "municipality",
        "title": "Municipal Authority",
        "org": "BBMP Solid Waste Management Command",
        "badge": "Municipal Operations",
        "icon": "🏙️",
        "jurisdiction": "Municipal Wards & Micro-Collection Routes",
        "access_desc": "Manage ward collections, inject surge events, simulate facility outages, re-optimize allocations, and dispatch truck fleets.",
    },
    "factory_admin": {
        "password": "Factory@123",
        "role": "factory",
        "title": "Processing / Factory Authority",
        "org": "Regional Waste Processing & Recycling Consortium",
        "badge": "Plant Operations",
        "icon": "🏭",
        "jurisdiction": "Processing Facilities A, B, and C",
        "access_desc": "Inspect real-time incoming truck weighbridges, hopper capacity, digester pressure, and maintenance schedules.",
    },
}


def get_current_user():
    """Return the authenticated user profile dict or None."""
    username = st.session_state.get("auth_username")
    if username and username in USERS:
        return {**USERS[username], "username": username}
    return None


def authenticate(username, password):
    """Validate username and password."""
    user = USERS.get(username.strip().lower())
    if user and user["password"] == password:
        st.session_state["auth_username"] = username.strip().lower()
        st.session_state["auth_role"] = user["role"]
        return True
    return False


def quick_login(username):
    """1-Click login for evaluator convenience."""
    if username in USERS:
        st.session_state["auth_username"] = username
        st.session_state["auth_role"] = USERS[username]["role"]
        st.rerun()


def logout():
    """Clear authentication session state."""
    st.session_state.pop("auth_username", None)
    st.session_state.pop("auth_role", None)
    st.rerun()


def render_login_page(palette):
    """Render a modern, glassmorphic login interface with quick-login buttons."""
    p = palette

    st.markdown(
        f'<div class="login-wrapper">'
        f'<div class="login-card">'
        f'<div class="login-header">'
        f'<div class="login-brand">'
        f'<div class="login-title">WasteGrid</div>'
        f'<div class="login-sub">Next-Generation Dynamic Waste Reallocation System</div>'
        f'</div>'
        f'</div>'
        f'<div class="login-notice">'
        f'Select your administrative authority level to enter the WasteGrid command dashboard.'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown(
            f'<div class="login-box-header">🔑 Standard Credential Login</div>',
            unsafe_allow_html=True,
        )
        with st.form("login_form", clear_on_submit=False):
            username_input = st.text_input("Username", placeholder="e.g. municipality_admin")
            password_input = st.text_input("Password", type="password", placeholder="Enter password")
            submit = st.form_submit_button("Sign In to WasteGrid", use_container_width=True)

            if submit:
                if authenticate(username_input, password_input):
                    st.success("Authentication successful! Loading dashboard...")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please check your username and password.")

    with col_right:
        st.markdown(
            f'<div class="login-box-header">⚡ 1-Click Role Switcher (Hackathon MVP Access)</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="font-size:0.75rem; color:{p["muted"]}; margin-bottom:12px;">'
            'Click any role below to instantly demo the corresponding dashboard with pre-configured authority:'
            '</div>',
            unsafe_allow_html=True,
        )

        for uname, udata in USERS.items():
            col_b1, col_b2 = st.columns([3, 1])
            with col_b1:
                st.markdown(
                    f'<div class="quick-role-row">'
                    f'<div class="quick-role-title">{udata["icon"]} {udata["title"]}</div>'
                    f'<div class="quick-role-sub">User: <code>{uname}</code> · {udata["badge"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_b2:
                if st.button("Enter ➔", key=f"quick_{uname}", use_container_width=True):
                    quick_login(uname)

    # Reference credentials table card
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f'<div class="creds-card">'
        f'<div class="creds-title">📋 Official Authority Credentials Matrix</div>'
        f'<table class="fc-table">'
        f'<thead><tr>'
        f'<th>Authority Level</th>'
        f'<th>Username</th>'
        f'<th>Password</th>'
        f'<th>Jurisdiction & Access Scope</th>'
        f'</tr></thead>'
        f'<tbody>'
        f'<tr><td>🏛️ State Authority – Karnataka</td><td><code>karnataka_admin</code></td><td><code>Waste@123</code></td><td>Statewide overview, multi-district flow & factory capacity</td></tr>'
        f'<tr><td>📍 District Authority</td><td><code>district_admin</code></td><td><code>District@123</code></td><td>District-level waste flow, transfer stations & quotas</td></tr>'
        f'<tr><td>🏙️ Municipal Authority</td><td><code>municipality_admin</code></td><td><code>Municipality@123</code></td><td>Wards, live collection, event/outage solver & truck dispatch</td></tr>'
        f'<tr><td>🏭 Processing/Factory Authority</td><td><code>factory_admin</code></td><td><code>Factory@123</code></td><td>Facility hoppers, weighbridge queue & plant maintenance</td></tr>'
        f'</tbody>'
        f'</table>'
        f'</div>',
        unsafe_allow_html=True,
    )
