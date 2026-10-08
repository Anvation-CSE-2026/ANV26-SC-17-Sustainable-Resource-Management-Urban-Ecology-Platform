"""
Secure Database-Backed Authentication and Role-Based Access Control (RBAC) for WasteGrid 2.0.
- PBKDF2-HMAC-SHA256 password verification with unique salts
- Persistent user sessions in st.session_state
- Role and jurisdiction-based permission enforcement
- Change password & forgot password security workflows
- Admin user management hooks
"""

import streamlit as st
from datetime import datetime, timezone
from wastegrid import db

# Official 6 Municipal Authority Roles
OFFICIAL_ROLES = [
    "State Waste Management Authority",
    "Municipal Commissioner",
    "Municipal Waste Officer",
    "Zonal Officer",
    "Waste Processing Facility",
    "Recycling Facility",
]

# Canonical role matching dictionary
ROLE_CANONICAL = {
    "State Waste Management Authority": ["state", "state_authority", "State Waste Management Authority"],
    "Municipal Commissioner": ["commissioner", "municipality", "Municipal Commissioner"],
    "Municipal Waste Officer": ["waste_officer", "municipality", "Municipal Waste Officer"],
    "Zonal Officer": ["zonal_officer", "district", "Zonal Officer"],
    "Waste Processing Facility": ["processing_facility", "factory", "Waste Processing Facility"],
    "Recycling Facility": ["recycling_facility", "factory", "Recycling Facility"],
}

# Page-level role permissions matrix
BASE_PERMS = [
    "home", "services", "events", "map", "alerts", "reports", "settings", "logout",
    "overview", "operations", "allocation", "analytics", "alerts_citizen", "admin_reports",
    "facilities", "vehicles", "calendar", "carbon", "profile"
]

ROLE_PERMISSIONS = {
    "admin": BASE_PERMS + ["users", "simulator", "performance"],
    "state": BASE_PERMS,
    "state_authority": BASE_PERMS,
    "commissioner": BASE_PERMS,
    "municipality": BASE_PERMS + ["citizen_reports", "simulator"],
    "waste_officer": BASE_PERMS + ["citizen_reports"],
    "zonal_officer": BASE_PERMS + ["citizen_reports"],
    "district": BASE_PERMS + ["citizen_reports"],
    "processing_facility": BASE_PERMS,
    "factory": BASE_PERMS,
    "recycling_facility": BASE_PERMS,
}


def get_current_user():
    """Retrieve the current authenticated user record from session state."""
    return st.session_state.get("authenticated_user")


def is_authenticated():
    """Check if a valid active session exists."""
    user = get_current_user()
    return bool(user and user.get("is_active"))


def login(username, password, selected_role=None):
    """Authenticate against SQLite database with hashed password verification and role validation."""
    clean_user = username.strip().lower()
    user = db.get_user_by_username(clean_user)
    if not user:
        return False, "Invalid Authority ID / Username or Password."

    if not user.get("is_active"):
        return False, "This authority account has been deactivated by the system administrator."

    if not db.verify_password(password, user["password_hash"], user["salt"]):
        db.add_audit_log(username, "LOGIN_FAILED", "Incorrect password attempt")
        return False, "Invalid Authority ID / Username or Password."

    # Validate role if specified
    if selected_role and user.get("role") != "admin":
        allowed_keys = ROLE_CANONICAL.get(selected_role, [selected_role])
        u_role = user.get("role", "")
        u_title = user.get("authority_title", "")
        if u_role not in allowed_keys and u_title != selected_role:
            return False, f"Role Mismatch: Account '{username}' is registered as '{u_title}', not '{selected_role}'. Please select the assigned authority role."

    st.session_state["authenticated_user"] = user
    if selected_role:
        st.session_state["active_role_title"] = selected_role
    else:
        st.session_state["active_role_title"] = user.get("authority_title", "Authorized Officer")

    # Update last login timestamp in DB
    now_str = datetime.now(timezone.utc).isoformat()
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET last_login = ? WHERE id = ?", (now_str, user["id"]))
    conn.commit()
    conn.close()
    db.add_audit_log(user["username"], "LOGIN_SUCCESS", f"User logged in with role {user['role']}")
    return True, "Login successful."


def logout():
    """Terminate the authenticated session."""
    user = get_current_user()
    if user:
        db.add_audit_log(user["username"], "LOGOUT", "User logged out")
    st.session_state.pop("authenticated_user", None)
    st.rerun()


def change_password(username, current_password, new_password, confirm_password):
    """Handle secure self-service password update."""
    if new_password != confirm_password:
        return False, "New passwords do not match."

    if len(new_password) < 8:
        return False, "Password must be at least 8 characters long."

    user = db.get_user_by_username(username)
    if not user:
        return False, "User not found."

    if not db.verify_password(current_password, user["password_hash"], user["salt"]):
        return False, "Current password verification failed."

    db.update_user_password(username, new_password)
    db.add_audit_log(username, "PASSWORD_CHANGED", "User successfully changed password")
    return True, "Password updated successfully. Please use your new password next time."


def forgot_password_reset(username, verified_email, new_password, confirm_password):
    """Reset password if verified official email matches account record."""
    if new_password != confirm_password:
        return False, "New passwords do not match."

    if len(new_password) < 8:
        return False, "Password must be at least 8 characters long."

    user = db.get_user_by_username(username)
    if not user:
        return False, "No account found matching this username."

    if user["email"].strip().lower() != verified_email.strip().lower():
        return False, "Provided email address does not match official records on file."

    db.update_user_password(username, new_password)
    db.add_audit_log(username, "PASSWORD_RESET", "Password reset via verified email match")
    return True, "Password reset successfully! You can now log in."


def has_permission(page_key):
    """Check if the current authenticated user has access to the specified page."""
    user = get_current_user()
    if not user:
        return False
    allowed_pages = ROLE_PERMISSIONS.get(user.get("role"), [])
    return page_key in allowed_pages


def render_sidebar_auth_widget():
    """
    Renders login form or current user profile in Streamlit's sidebar.
    """
    user = get_current_user()

    if user:
        # User is authenticated: Render user profile card in sidebar
        role_icons = {
            "state": "🏛️",
            "district": "📍",
            "municipality": "🏙️",
            "factory": "🏭",
            "admin": "🛡️",
        }
        u_icon = role_icons.get(user["role"], "👤")

        card_html = (
            f'<div style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1); '
            f'border-radius: 8px; padding: 12px; margin-bottom: 16px;">'
            f'<div style="display:flex; align-items:center; gap:8px;">'
            f'<span style="font-size:1.4rem;">{u_icon}</span>'
            f'<div style="overflow:hidden;">'
            f'<div style="font-size:0.85rem; font-weight:700; text-overflow:ellipsis; white-space:nowrap;">{user["full_name"]}</div>'
            f'<div style="font-size:0.68rem; color:#8ba3c7; text-transform:uppercase; letter-spacing:0.08em;">{user["authority_title"]}</div>'
            f'</div></div>'
            f'<div style="margin-top:8px; font-size:0.68rem; color:#8ba3c7; border-top:1px solid rgba(255,255,255,0.06); padding-top:6px;">'
            f'<b>Scope:</b> {user["jurisdiction"]}'
            f'</div></div>'
        )
        st.sidebar.markdown(card_html, unsafe_allow_html=True)

        col_out, col_pwd = st.sidebar.columns([1, 1])
        with col_out:
            if st.button("🚪 Logout", key="btn_sb_logout", use_container_width=True):
                logout()
        with col_pwd:
            if st.button("🔑 Profile", key="btn_sb_profile", use_container_width=True):
                st.session_state["nav_selection"] = "profile"
                st.rerun()

    else:
        # User is NOT authenticated: Render secure login card in sidebar
        st.sidebar.markdown(
            """
            <div style="margin-bottom:12px; font-size:0.8rem; font-weight:700; letter-spacing:0.08em; text-transform:uppercase; color:#8ba3c7;">
                🔐 Secure Authority Sign-In
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.sidebar.form("sb_login_form"):
            uname = st.text_input("Username", placeholder="e.g. municipality_admin")
            pword = st.text_input("Password", type="password", placeholder="••••••••")
            submit = st.form_submit_button("Sign In ➔", use_container_width=True)

            if submit:
                if uname and pword:
                    success, msg = login(uname, pword)
                    if success:
                        st.toast("✅ Signed in successfully!")
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Please enter both username and password.")

        with st.sidebar.expander("❓ Forgot Password", expanded=False):
            st.markdown("<small style='color:#8ba3c7;'>Official account recovery via verified email:</small>", unsafe_allow_html=True)
            with st.form("sb_forgot_form"):
                f_user = st.text_input("Account Username")
                f_mail = st.text_input("Registered Official Email")
                f_p1 = st.text_input("New Password", type="password")
                f_p2 = st.text_input("Confirm New Password", type="password")
                f_sub = st.form_submit_button("Reset Password", use_container_width=True)
                if f_sub:
                    s, m = forgot_password_reset(f_user, f_mail, f_p1, f_p2)
                    if s:
                        st.success(m)
                    else:
                        st.error(m)


def register_account(username, password, full_name, email, role="municipality", jurisdiction="City Ward Operations"):
    """Register a new user account and log in immediately."""
    if len(username.strip()) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if "@" not in email:
        return False, "Please provide a valid email address."

    role_titles = {
        "admin": "System Administrator",
        "state": "State Urban Authority",
        "district": "District Magistrate / Authority",
        "municipality": "Municipal Operations Officer",
        "factory": "Processing Plant Manager",
    }
    title = role_titles.get(role, "Municipal Field Officer")

    success, msg = db.create_user(username, password, role, title, jurisdiction, full_name, email)
    if not success:
        return False, msg

    # Auto-login after creation
    user = db.get_user_by_username(username)
    if user:
        st.session_state["authenticated_user"] = user
        db.add_audit_log(username, "USER_REGISTERED", f"New user created and logged in with role {role}")
        return True, "Account created successfully! You are now logged in."
    return True, "Account created successfully."


def render_auth_modal(palette):
    """
    Renders an in-page modal/panel for Login, Account Registration, or Active Profile.
    Triggered when Profile icon is clicked in the header.
    """
    p = palette
    user = get_current_user()

    st.markdown(
        f"""
        <div style="background:{p['card_bg']}; border:2px solid {p['blue']}; border-radius:14px; 
                    padding:24px 28px; margin-bottom:24px; box-shadow:{p['shadow']};">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid {p['border']}; padding-bottom:14px; margin-bottom:18px;">
                <div style="font-size:1.25rem; font-weight:800; color:{p['text']}; display:flex; align-items:center; gap:10px;">
                    <span>👤</span>
                    <span>{'My Account & Active Profile' if user else 'Sign In or Create Account'}</span>
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    if user:
        # User is already signed in
        col_info, col_pwd = st.columns([1.2, 1], gap="large")
        with col_info:
            role_colors = {"admin": "#ef4444", "state": "#3b82f6", "district": "#8b5cf6", "municipality": "#10b981", "factory": "#f59e0b"}
            r_col = role_colors.get(user["role"], "#3b82f6")
            st.markdown(
                f"""
                <div style="background:{p['bg_soft']}; border:1px solid {p['border']}; border-radius:10px; padding:18px; line-height:1.8; font-size:0.85rem;">
                    <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
                        <div style="width:44px; height:44px; border-radius:50%; background:{r_col}; color:#fff; display:flex; align-items:center; justify-content:center; font-size:1.3rem; font-weight:800;">
                            {user['full_name'][:1]}
                        </div>
                        <div>
                            <div style="font-size:1.1rem; font-weight:800; color:{p['text']};">{user['full_name']}</div>
                            <span style="background:{r_col}; color:#fff; padding:2px 8px; border-radius:999px; font-size:0.68rem; font-weight:700; text-transform:uppercase;">{user['role']} Authority</span>
                        </div>
                    </div>
                    <div><b>Username:</b> <code>{user['username']}</code></div>
                    <div><b>Official Title:</b> {user['authority_title']}</div>
                    <div><b>Jurisdiction Scope:</b> {user['jurisdiction']}</div>
                    <div><b>Official Email:</b> {user['email']}</div>
                    <div><b>Account Status:</b> <span style="color:#10b981; font-weight:700;">● Active Verified</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown("<br>", unsafe_allow_html=True)
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("🚪 Sign Out / Logout", key="btn_modal_logout", type="primary", use_container_width=True):
                    logout()
            with col_b2:
                if st.button("✖️ Close Profile", key="btn_modal_close_user", use_container_width=True):
                    st.session_state["show_auth_modal"] = False
                    st.rerun()

        with col_pwd:
            st.markdown(f'<div style="font-weight:700; color:{p["text"]}; margin-bottom:8px;">🔑 Change Account Password</div>', unsafe_allow_html=True)
            with st.form("modal_change_pwd_form"):
                cur_p = st.text_input("Current Password", type="password")
                new_p = st.text_input("New Secure Password", type="password")
                cfm_p = st.text_input("Confirm New Password", type="password")
                sub_pwd = st.form_submit_button("Update Password ➔", use_container_width=True)
                if sub_pwd:
                    s, m = change_password(user["username"], cur_p, new_p, cfm_p)
                    if s:
                        st.success(m)
                    else:
                        st.error(m)

    else:
        # User is NOT signed in: Provide Sign In, Create Account, and 1-Click Demo Logins!
        tab_login, tab_register, tab_forgot = st.tabs(["🔑 Sign In to Existing Account", "📝 Create New Account", "❓ Forgot Password"])

        with tab_login:
            col_f, col_quick = st.columns([1, 1], gap="large")
            with col_f:
                st.markdown(f'<div style="font-weight:700; color:{p["text"]}; margin-bottom:8px;">Enter Your Official Credentials</div>', unsafe_allow_html=True)
                with st.form("modal_login_form"):
                    u_in = st.text_input("Username", placeholder="e.g. municipality_admin", key="modal_u_in")
                    p_in = st.text_input("Password", type="password", placeholder="••••••••", key="modal_p_in")
                    btn_login = st.form_submit_button("Sign In ➔", type="primary", use_container_width=True)
                    if btn_login:
                        if u_in and p_in:
                            ok, msg = login(u_in, p_in)
                            if ok:
                                st.session_state["show_auth_modal"] = False
                                st.toast("✅ Signed in successfully!")
                                st.rerun()
                            else:
                                st.error(msg)
                        else:
                            st.warning("Please enter both username and password.")

            with col_quick:
                st.markdown(
                    f"""
                    <div style="font-weight:700; color:{p['blue']}; margin-bottom:8px;">
                        ⚡ 1-Click Fast Login (Evaluator Demo Presets)
                    </div>
                    <div style="font-size:0.75rem; color:{p['muted']}; margin-bottom:12px;">
                        Click any role below to instantly log in and experience the tailored dashboard:
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                q_col1, q_col2 = st.columns(2)
                with q_col1:
                    if st.button("👑 Super Admin", use_container_width=True):
                        login("admin", "Admin@123")
                        st.session_state["show_auth_modal"] = False
                        st.rerun()
                    if st.button("🏛️ State Authority", use_container_width=True):
                        login("state_admin", "Waste@123")
                        st.session_state["show_auth_modal"] = False
                        st.rerun()
                    if st.button("🏢 District Authority", use_container_width=True):
                        login("district_admin", "District@123")
                        st.session_state["show_auth_modal"] = False
                        st.rerun()
                with q_col2:
                    if st.button("🏙️ Municipal Office", use_container_width=True):
                        login("municipality_admin", "Municipality@123")
                        st.session_state["show_auth_modal"] = False
                        st.rerun()
                    if st.button("🏭 Plant Manager", use_container_width=True):
                        login("factory_admin", "Factory@123")
                        st.session_state["show_auth_modal"] = False
                        st.rerun()

        with tab_register:
            st.markdown(f'<div style="font-weight:700; color:{p["text"]}; margin-bottom:8px;">Register Official Municipal or Citizen Account</div>', unsafe_allow_html=True)
            with st.form("modal_reg_form"):
                r_c1, r_c2 = st.columns(2)
                with r_c1:
                    reg_fname = st.text_input("Full Name", placeholder="e.g. Ramesh Chandra")
                    reg_uname = st.text_input("Desired Username", placeholder="e.g. ramesh_officer")
                    reg_email = st.text_input("Email Address", placeholder="officer@smartcity.gov.in")
                with r_c2:
                    reg_role = st.selectbox("Role / Authority Category", ["municipality", "factory", "district", "state"], format_func=lambda x: {
                        "municipality": "🏙️ Municipal Ward Officer",
                        "factory": "🏭 Processing Plant Manager",
                        "district": "🏢 District Urban Inspector",
                        "state": "🏛️ State Urban Authority",
                    }.get(x, x))
                    reg_juris = st.text_input("Jurisdiction / Ward", placeholder="e.g. Ward 112 - Central Zone")
                    reg_pwd1 = st.text_input("Password (min 6 chars)", type="password")
                    reg_pwd2 = st.text_input("Confirm Password", type="password")

                btn_reg = st.form_submit_button("Register & Sign In ➔", type="primary", use_container_width=True)
                if btn_reg:
                    if reg_pwd1 != reg_pwd2:
                        st.error("Passwords do not match.")
                    else:
                        ok, msg = register_account(reg_uname, reg_pwd1, reg_fname, reg_email, reg_role, reg_juris)
                        if ok:
                            st.session_state["show_auth_modal"] = False
                            st.toast("🎉 Account created and logged in!")
                            st.rerun()
                        else:
                            st.error(msg)

        with tab_forgot:
            st.markdown(f'<div style="font-weight:700; color:{p["text"]}; margin-bottom:8px;">Self-Service Password Reset via Verified Email</div>', unsafe_allow_html=True)
            with st.form("modal_forgot_form"):
                f_u = st.text_input("Account Username")
                f_e = st.text_input("Registered Official Email")
                f_p = st.text_input("New Password", type="password")
                f_cp = st.text_input("Confirm New Password", type="password")
                btn_f = st.form_submit_button("Reset Password ➔", use_container_width=True)
                if btn_f:
                    s, m = forgot_password_reset(f_u, f_e, f_p, f_cp)
                    if s:
                        st.success(m)
                    else:
                        st.error(m)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✖️ Close Sign In Panel", key="btn_close_auth_modal", use_container_width=True):
            st.session_state["show_auth_modal"] = False
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_access_restricted_view(page_name):
    """Renders a clean notice when a user tries to access a page outside their role authority."""
    user = get_current_user()
    role_title = user["authority_title"] if user else "Public User"

    msg_html = (
        f'<div style="max-width: 650px; margin: 40px auto; text-align: center; background: rgba(255,56,86,0.06); '
        f'border: 1px solid rgba(255,56,86,0.3); border-radius: 12px; padding: 36px 28px;">'
        f'<div style="font-size: 2.8rem; margin-bottom: 12px;">🛡️</div>'
        f'<div style="font-size: 1.3rem; font-weight: 800; color: #ff3856; margin-bottom: 8px;">Jurisdictional Access Restricted</div>'
        f'<div style="font-size: 0.85rem; color: #8ba3c7; margin-bottom: 20px; line-height: 1.6;">'
        f'Your logged-in role as <b>{role_title}</b> does not have administrative clearance to access the <b>{page_name}</b> view.'
        f'</div>'
        f'<div style="font-size: 0.75rem; color: #8ba3c7; background: rgba(0,0,0,0.2); padding: 12px; border-radius: 6px;">'
        f'Please contact the State Urban Development IT Administrator if you require elevated clearance.'
        f'</div></div>'
    )
    st.markdown(msg_html, unsafe_allow_html=True)


def render_full_login_page(palette):
    """
    Renders the modern, full-screen WasteGrid Authority Login Page.
    Serves as the exclusive entry point of the website when unauthenticated.
    """
    p = palette

    # Waste-management themed background styling
    st.markdown(
        """
        <style>
        /* Hide sidebar when unauthenticated on login page */
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        .main .block-container {
            max-width: 900px !important;
            padding-top: 1.5rem !important;
            padding-bottom: 3rem !important;
        }
        .wg-login-brand {
            text-align: center;
            margin-bottom: 24px;
        }
        .wg-login-logo {
            width: 60px;
            height: 60px;
            margin: 0 auto 12px auto;
            border-radius: 16px;
            background: linear-gradient(135deg, #10b981 0%, #0284c7 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.2rem;
            box-shadow: 0 10px 25px rgba(16, 185, 129, 0.35);
        }
        .wg-login-title {
            font-size: 2.4rem;
            font-weight: 900;
            letter-spacing: -0.03em;
            line-height: 1.1;
            background: linear-gradient(135deg, #10b981, #38bdf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .wg-login-tagline {
            font-size: 0.95rem;
            font-weight: 800;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            color: #10b981;
            margin-top: 6px;
        }
        .wg-login-subtitle {
            font-size: 0.85rem;
            color: #8ba3c7;
            margin-top: 4px;
        }
        .wg-login-badge {
            display: inline-block;
            margin-top: 10px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            padding: 4px 14px;
            border-radius: 999px;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.35);
            color: #10b981;
        }
        .wg-login-card {
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid rgba(16, 185, 129, 0.25);
            border-radius: 16px;
            padding: 28px 32px;
            box-shadow: 0 20px 45px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(12px);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 1. Top Brand Header: WasteGrid Logo & Tagline
    st.markdown(
        """
        <div class="wg-login-brand">
            <div class="wg-login-logo">♻️</div>
            <div class="wg-login-title">WasteGrid</div>
            <div class="wg-login-tagline">Predict. Detect. Allocate.</div>
            <div class="wg-login-subtitle">Intelligent Municipal Solid-Waste Management System</div>
            <div class="wg-login-badge">🛡️ Authorized Government & Municipal Access Only</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. Centered Login Card
    col_l, col_c, col_r = st.columns([1, 1.8, 1])
    with col_c:
        st.markdown(
            f"""
            <div style="background:{p['card_bg']}; border:1px solid {p['border']}; border-radius:14px; padding:24px 28px; box-shadow:{p['shadow']}; margin-bottom:18px;">
                <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid {p['border']}; padding-bottom:12px; margin-bottom:18px;">
                    <div>
                        <div style="font-size:1.15rem; font-weight:800; color:{p['text']};">🏛️ Authority Sign-In</div>
                        <div style="font-size:0.75rem; color:{p['muted']};">Enter your municipal credentials to access the grid</div>
                    </div>
                    <span style="font-size:0.68rem; font-weight:700; color:#10b981; background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3); padding:2px 8px; border-radius:4px;">
                        256-bit PBKDF2
                    </span>
                </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("main_authority_login_form"):
            # 1. Authority ID / Username
            auth_user = st.text_input(
                "Authority ID / Username",
                placeholder="e.g. commissioner or state_authority",
                key="input_auth_user",
            )

            # 2. Password
            auth_pwd = st.text_input(
                "Password",
                type="password",
                placeholder="••••••••••••",
                key="input_auth_pwd",
            )

            # 3. Role Dropdown
            auth_role = st.selectbox(
                "Designated Authority Role",
                OFFICIAL_ROLES,
                index=0,
                key="select_auth_role",
            )

            # Remember Me Checkbox
            col_rem, col_blank = st.columns([1.2, 1])
            with col_rem:
                remember_me = st.checkbox(
                    "Remember this authority terminal",
                    value=True,
                    key="chk_auth_remember",
                )

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

            # Prominent Login Button
            login_submitted = st.form_submit_button(
                "Access WasteGrid Dashboard ➔",
                type="primary",
                use_container_width=True,
            )

            if login_submitted:
                if not auth_user or not auth_pwd:
                    st.warning("⚠️ Please provide both Authority ID and Password.")
                else:
                    success, message = login(auth_user, auth_pwd, auth_role)
                    if success:
                        st.toast("✅ Authorized access granted. Redirecting to WasteGrid...")
                        st.session_state["nav_selection"] = "home"
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")

        # Forgot Password Section
        with st.expander("❓ Forgot Password?", expanded=False):
            st.markdown(
                f"<div style='font-size:0.75rem; color:{p['muted']}; margin-bottom:8px;'>"
                "Self-service official password recovery via verified government email:"
                "</div>",
                unsafe_allow_html=True,
            )
            with st.form("login_page_forgot_form"):
                fgt_user = st.text_input("Account Authority ID / Username", key="fgt_u")
                fgt_email = st.text_input("Registered Official Email", key="fgt_e")
                fgt_p1 = st.text_input("New Secure Password", type="password", key="fgt_p1")
                fgt_p2 = st.text_input("Confirm New Password", type="password", key="fgt_p2")
                fgt_sub = st.form_submit_button("Reset Password", use_container_width=True)
                if fgt_sub:
                    if not fgt_user or not fgt_email or not fgt_p1:
                        st.warning("Please fill out all fields.")
                    else:
                        ok, msg = forgot_password_reset(fgt_user, fgt_email, fgt_p1, fgt_p2)
                        if ok:
                            st.success(f"✅ {msg}")
                        else:
                            st.error(f"❌ {msg}")

        # Restricted Registration Notice (No Public Registration)
        st.markdown(
            f"""
            <div style="margin-top:14px; padding-top:12px; border-top:1px solid {p['border']}; font-size:0.72rem; color:{p['muted']}; text-align:center; line-height:1.5;">
                🔒 <b>Restricted Authority Dashboard:</b> Public registration is disabled under Municipal Solid-Waste Regulations. 
                Accounts are provisioned solely to verified urban authorities, municipal commissioners, zonal officers, and facility directors.
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Evaluator & Auditor Fast Access Presets (1-Click Login for All 6 Roles)
        with st.expander("⚡ Evaluator Quick-Login (1-Click Demo Presets)", expanded=True):
            st.markdown(
                f"<div style='font-size:0.75rem; color:{p['muted']}; margin-bottom:10px;'>"
                "Click any designated authority below to sign in instantly with calibrated sample data:"
                "</div>",
                unsafe_allow_html=True,
            )

            col_q1, col_q2 = st.columns(2)
            with col_q1:
                if st.button("🏛️ State Authority", use_container_width=True, key="quick_state_btn"):
                    login("state_authority", "Waste@123", "State Waste Management Authority")
                    st.session_state["nav_selection"] = "home"
                    st.rerun()

                if st.button("🏙️ Municipal Commissioner", use_container_width=True, key="quick_comm_btn"):
                    login("commissioner", "Waste@123", "Municipal Commissioner")
                    st.session_state["nav_selection"] = "home"
                    st.rerun()

                if st.button("📋 Municipal Waste Officer", use_container_width=True, key="quick_wo_btn"):
                    login("waste_officer", "Waste@123", "Municipal Waste Officer")
                    st.session_state["nav_selection"] = "home"
                    st.rerun()

            with col_q2:
                if st.button("📍 Zonal Officer", use_container_width=True, key="quick_zo_btn"):
                    login("zonal_officer", "Waste@123", "Zonal Officer")
                    st.session_state["nav_selection"] = "home"
                    st.rerun()

                if st.button("🏭 Waste Processing Facility", use_container_width=True, key="quick_pf_btn"):
                    login("processing_facility", "Waste@123", "Waste Processing Facility")
                    st.session_state["nav_selection"] = "home"
                    st.rerun()

                if st.button("♻️ Recycling Facility", use_container_width=True, key="quick_rf_btn"):
                    login("recycling_facility", "Waste@123", "Recycling Facility")
                    st.session_state["nav_selection"] = "home"
                    st.rerun()

    # Subtle Footer for Login Page
    st.markdown(
        f"""
        <div style="text-align:center; font-size:0.73rem; color:{p['muted']}; margin-top:32px;">
            WasteGrid · Predict. Detect. Allocate. · © 2026 Municipal SWM Directorate. All rights reserved.
        </div>
        """,
        unsafe_allow_html=True,
    )



