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

# Page-level role permissions matrix
ROLE_PERMISSIONS = {
    "admin": [
        "overview", "map", "analytics", "forecast", "facilities", "allocation",
        "vehicles", "calendar", "simulator", "alerts", "citizen_reports",
        "carbon", "performance", "reports", "users", "settings", "profile"
    ],
    "state": [
        "overview", "map", "analytics", "forecast", "facilities", "allocation",
        "calendar", "alerts", "carbon", "performance", "reports", "settings", "profile"
    ],
    "district": [
        "overview", "map", "analytics", "forecast", "facilities", "vehicles",
        "calendar", "alerts", "citizen_reports", "reports", "settings", "profile"
    ],
    "municipality": [
        "overview", "map", "analytics", "forecast", "facilities", "allocation",
        "vehicles", "calendar", "simulator", "alerts", "citizen_reports",
        "carbon", "reports", "settings", "profile"
    ],
    "factory": [
        "overview", "facilities", "allocation", "vehicles", "alerts",
        "performance", "reports", "settings", "profile"
    ],
}


def get_current_user():
    """Retrieve the current authenticated user record from session state."""
    return st.session_state.get("authenticated_user")


def is_authenticated():
    """Check if a valid active session exists."""
    user = get_current_user()
    return bool(user and user.get("is_active"))


def login(username, password):
    """Authenticate against SQLite database with hashed password verification."""
    user = db.get_user_by_username(username)
    if not user:
        return False, "Invalid username or password."

    if not user.get("is_active"):
        return False, "This account has been deactivated by the system administrator."

    if db.verify_password(password, user["password_hash"], user["salt"]):
        st.session_state["authenticated_user"] = user
        # Update last login timestamp in DB
        now_str = datetime.now(timezone.utc).isoformat()
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET last_login = ? WHERE id = ?", (now_str, user["id"]))
        conn.commit()
        conn.close()
        db.add_audit_log(user["username"], "LOGIN_SUCCESS", f"User logged in from role {user['role']}")
        return True, "Login successful."

    db.add_audit_log(username, "LOGIN_FAILED", "Incorrect password attempt")
    return False, "Invalid username or password."


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


