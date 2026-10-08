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
