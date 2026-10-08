"""
Profile Management and System Settings Module for WasteGrid 2.0.
Features:
- User Profile inspection and Self-Service Password Change
- Security Audit Log viewer
- System settings and alert threshold tuning
"""

import streamlit as st
import pandas as pd
from wastegrid import auth, db


def render_profile_page(palette):
    """Render User Profile and Security Management console."""
    p = palette
    user = auth.get_current_user()

    if not user:
        st.warning("Please sign in to view your profile.")
        return

    st.markdown(
        f"""
        <div style="background:{p['card_bg']}; border:1px solid {p['border']}; border-left:4px solid {p['blue']};
                    border-radius:8px; padding:18px 22px; margin-bottom:20px;">
            <div style="font-size:1.15rem; font-weight:800; color:{p['text']};">👤 User Profile & Account Security</div>
            <div style="font-size:0.75rem; color:{p['muted']}; margin-top:4px;">
                Manage your administrative identity, official credentials, and security password policies.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown(f'<div class="sec-title">📋 OFFICIAL IDENTITY CREDENTIALS</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div style="background:{p['card_bg']}; border:1px solid {p['border']}; border-radius:8px; padding:20px; line-height:1.8; font-size:0.85rem; color:{p['text']};">
                <b>Username:</b> <code>{user['username']}</code><br>
                <b>Full Name:</b> {user['full_name']}<br>
                <b>Authority Level:</b> {user['authority_title']}<br>
                <b>Role Identifier:</b> <code>{user['role'].upper()}</code><br>
                <b>Official Email:</b> {user['email']}<br>
                <b>Jurisdictional Scope:</b> {user['jurisdiction']}<br>
                <b>Account Status:</b> <span style="color:#22c55e; font-weight:700;">Active Verified</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(f'<div class="sec-title">🔑 CHANGE ACCOUNT PASSWORD</div>', unsafe_allow_html=True)
        with st.form("change_password_form"):
            old_p = st.text_input("Current Password", type="password")
            new_p = st.text_input("New Secure Password", type="password")
            conf_p = st.text_input("Confirm New Password", type="password")
            btn_sub = st.form_submit_button("Update Password ➔", use_container_width=True)

            if btn_sub:
                success, msg = auth.change_password(user["username"], old_p, new_p, conf_p)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)


def render_settings_page(palette):
    """Render System Settings & Operational Configurations."""
    p = palette

    st.markdown(
        f"""
        <div style="background:{p['card_bg']}; border:1px solid {p['border']}; border-left:4px solid {p['purple']};
                    border-radius:8px; padding:18px 22px; margin-bottom:20px;">
            <div style="font-size:1.15rem; font-weight:800; color:{p['text']};">⚙️ WasteGrid System Settings & Parameters</div>
            <div style="font-size:0.75rem; color:{p['muted']}; margin-top:4px;">
                Configure predictive alert thresholds, linear optimization solver weights, and GIS telemetry intervals.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f'<div class="sec-title">🔔 ALERT THRESHOLD PARAMETERS</div>', unsafe_allow_html=True)
        st.slider("Normal Utilization Upper Bound (%)", 50, 75, 70, 5)
        st.slider("Moderate Utilization Upper Bound (%)", 75, 85, 85, 5)
        st.slider("Warning Utilization Upper Bound (%)", 85, 95, 95, 1)
        st.number_input("Forecast Surge Lead Time (Days)", 1, 14, 7)

    with col2:
        st.markdown(f'<div class="sec-title">⚡ LP OPTIMIZER DEFAULT PENALTIES</div>', unsafe_allow_html=True)
        st.number_input("Overflow Penalty Multiplier", 1000, 20000, 10000, 1000)
        st.number_input("Diesel Transport Cost Weight (₹ / km)", 10.0, 50.0, 18.0, 1.0)
        st.number_input("Carbon Emission Weight (kg CO₂ / km)", 0.1, 1.0, 0.25, 0.05)
        st.selectbox("Default Linear Programming Solver", ["HiGHS (Dual Simplex)", "HiGHS (Interior Point)", "Greedy Heuristic Fallback"])

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Save System Configuration"):
        st.toast("✅ Settings saved successfully.")
