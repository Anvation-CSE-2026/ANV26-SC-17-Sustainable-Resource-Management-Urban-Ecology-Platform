import streamlit as st


def get_palette(theme):
    if theme == "light":
        # Soft warm beige — not white
        return {
            "bg": "#f0ece4",           # warm sand
            "bg_soft": "#e8e3d9",
            "card_bg": "#faf7f2",      # off-white card
            "card_border": "#d8d2c6",
            "text": "#1e293b",
            "text_muted": "#6b7280",
            "divider": "#d8d2c6",
            "input_bg": "#e8e3d9",
        }
    # Warm charcoal — not black, not navy
    return {
        "bg": "#2b2a28",               # warm dark gray
        "bg_soft": "#35332f",
        "card_bg": "#35332f",
        "card_border": "#46433d",
        "text": "#f0ece4",
        "text_muted": "#a8a49c",
        "divider": "#46433d",
        "input_bg": "#3d3b36",
    }

def inject_css(p):
    theme = st.session_state.get("theme", "light")
    ok_color = "#15803d" if theme == "light" else "#86efac"
    alert_color = "#b91c1c" if theme == "light" else "#fca5a5"
    warn_color = "#b45309" if theme == "light" else "#fcd34d"

    st.markdown(f"""
    <style>
        .stApp {{ background: {p['bg']}; }}
        h1, h2, h3, h4, p, span, div, label {{ color: {p['text']} !important; }}
        [data-testid="stSidebar"] {{ display: none; }}
        [data-testid="stHeader"] {{ background: {p['bg']}; }}

        .logo-title {{
            font-size: 2rem;
            font-weight: 800;
            background: linear-gradient(90deg, #16a34a 0%, #0891b2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
            line-height: 1.1;
        }}
        .logo-tagline {{
            font-size: 0.9rem;
            color: {p['text_muted']};
            margin-top: 4px;
            letter-spacing: 0.3px;
        }}

        .metric-card {{
            background: {p['card_bg']};
            border: 1px solid {p['card_border']};
            border-radius: 14px;
            padding: 18px;
            text-align: center;
            transition: all 0.25s ease;
            animation: fadeInUp 0.5s ease;
        }}
        .metric-card:hover {{
            border-color: #16a34a;
            transform: translateY(-2px);
            box-shadow: 0 6px 18px rgba(22, 163, 74, 0.12);
        }}
        .metric-label {{
            font-size: 0.75rem;
            color: {p['text_muted']};
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 6px;
        }}
        .metric-value {{ font-size: 1.9rem; font-weight: 700; }}

        .status-ok {{
            background: rgba(34,197,94,0.10);
            border-left: 4px solid #22c55e;
            padding: 14px 18px;
            border-radius: 8px;
            color: {ok_color};
            font-weight: 600;
            animation: slideIn 0.4s ease;
        }}
        .status-alert {{
            background: rgba(239,68,68,0.10);
            border-left: 4px solid #ef4444;
            padding: 14px 18px;
            border-radius: 8px;
            color: {alert_color};
            font-weight: 600;
            animation: slideIn 0.4s ease, pulse 2s infinite;
        }}
        .status-warn {{
            background: rgba(245,158,11,0.10);
            border-left: 4px solid #f59e0b;
            padding: 12px 18px;
            border-radius: 8px;
            color: {warn_color};
            margin-top: 10px;
            animation: slideIn 0.4s ease;
        }}
        .status-success {{
            background: rgba(34,197,94,0.12);
            border-left: 4px solid #22c55e;
            padding: 12px 18px;
            border-radius: 8px;
            color: {ok_color};
            font-weight: 600;
            margin-top: 10px;
            animation: slideIn 0.4s ease;
        }}

        .facility-card {{
            background: {p['card_bg']};
            border: 1px solid {p['card_border']};
            border-radius: 12px;
            padding: 16px;
            transition: all 0.25s ease;
        }}
        .facility-card:hover {{ border-color: #0891b2; }}
        .facility-name {{ font-weight: 700; font-size: 1rem; color: {p['text']}; }}
        .facility-type {{
            font-size: 0.72rem;
            color: {p['text_muted']};
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .util-bar {{
            height: 8px;
            background: {p['input_bg']};
            border-radius: 4px;
            overflow: hidden;
            margin-top: 10px;
        }}
        .util-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
            animation: growBar 1s ease-out;
        }}

        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to   {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes slideIn {{
            from {{ opacity: 0; transform: translateX(-10px); }}
            to   {{ opacity: 1; transform: translateX(0); }}
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50%      {{ opacity: 0.75; }}
        }}
        @keyframes growBar {{ from {{ width: 0%; }} }}

        .stButton > button {{
            background: linear-gradient(90deg, #16a34a 0%, #0891b2 100%);
            color: #ffffff;
            font-weight: 600;
            border: none;
            border-radius: 10px;
            padding: 10px 18px;
            transition: all 0.2s ease;
        }}
        .stButton > button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(22, 163, 74, 0.25);
        }}

        [data-testid="stExpander"] {{
            background: {p['card_bg']};
            border: 1px solid {p['card_border']};
            border-radius: 10px;
        }}
    </style>
    """, unsafe_allow_html=True)