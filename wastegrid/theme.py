import streamlit as st


def get_palette(theme):
    if theme == "light":
        return {
            "bg": "#f4f4f5",
            "bg_soft": "#eaeaec",
            "card_bg": "#ffffff",
            "card_border": "#e4e4e7",
            "card_shadow": "0 1px 2px rgba(0,0,0,0.03), 0 1px 3px rgba(0,0,0,0.04)",
            "text": "#0a0a0a",
            "text_muted": "#71717a",
            "divider": "#e4e4e7",
            "input_bg": "#f4f4f5",
            "accent": "#d5001c",
            "accent_2": "#0a0a0a",
            "danger": "#d5001c",
            "warn": "#b45309",
            "map_bg": "#efeff1",
        }
    return {
        "bg": "#0c0c0d",
        "bg_soft": "#18181b",
        "card_bg": "#18181b",
        "card_border": "#27272a",
        "card_shadow": "0 1px 2px rgba(0,0,0,0.4), 0 1px 3px rgba(0,0,0,0.3)",
        "text": "#fafafa",
        "text_muted": "#a1a1aa",
        "divider": "#27272a",
        "input_bg": "#1f1f23",
        "accent": "#ff2d3f",
        "accent_2": "#fafafa",
        "danger": "#ff2d3f",
        "warn": "#fbbf24",
        "map_bg": "#1a1a1d",
    }


def inject_css(p):
    theme = st.session_state.get("theme", "light")

    st.markdown(f"""
    <style>
        html, body, [class*="css"], .stApp, button, input, textarea {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }}

        .stApp {{ background: {p['bg']}; }}

        h1, h2, h3, h4, p, span, div, label {{
            color: {p['text']} !important;
        }}

        [data-testid="stSidebar"] {{ display: none; }}
        [data-testid="stHeader"] {{ background: {p['bg']}; }}
        [data-testid="stToolbar"] {{ display: none; }}
        #MainMenu {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}

        .block-container {{
            padding-top: 2.5rem;
            padding-bottom: 4rem;
            max-width: 1280px;
        }}

        /* ---------- Header ---------- */
        .logo-title {{
            font-size: 1.65rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            color: {p['text']} !important;
            margin: 0;
            line-height: 1;
        }}
        .logo-tagline {{
            font-size: 0.68rem;
            color: {p['text_muted']};
            margin-top: 8px;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            font-weight: 500;
        }}

        /* ---------- Panel wrapper (for grouped sections) ---------- */
        .panel {{
            background: {p['card_bg']};
            border: 1px solid {p['card_border']};
            border-radius: 6px;
            padding: 24px 26px;
            box-shadow: {p['card_shadow']};
            animation: fadeIn 0.35s ease both;
        }}

        /* ---------- Metric cards ---------- */
        .metric-card {{
            background: {p['card_bg']};
            border: 1px solid {p['card_border']};
            border-radius: 6px;
            padding: 24px;
            box-shadow: {p['card_shadow']};
            transition: all 0.2s ease;
            animation: fadeIn 0.35s ease both;
            height: 100%;
        }}
        .metric-card:hover {{
            border-color: {p['text_muted']};
            transform: translateY(-1px);
        }}
        .metric-label {{
            font-size: 0.62rem;
            color: {p['text_muted']};
            text-transform: uppercase;
            letter-spacing: 0.22em;
            font-weight: 600;
            margin-bottom: 16px;
        }}
        .metric-value {{
            font-size: 2.6rem;
            font-weight: 300;
            letter-spacing: -0.045em;
            line-height: 1;
            font-variant-numeric: tabular-nums;
        }}
        .metric-card.emphasize {{
            border: 1.5px solid {p['text']};
            padding: 30px 26px;
        }}
        .metric-card.emphasize .metric-value {{
            font-size: 3.2rem;
            font-weight: 300;
        }}
        .metric-sub {{
            font-size: 0.72rem;
            color: {p['text_muted']};
            margin-top: 10px;
            font-weight: 400;
        }}

        /* ---------- Status banners ---------- */
        .status-ok, .status-alert, .status-warn, .status-success {{
            border-radius: 4px;
            padding: 14px 20px;
            font-weight: 500;
            font-size: 0.82rem;
            letter-spacing: 0.01em;
            display: flex;
            align-items: center;
            gap: 12px;
            animation: fadeIn 0.35s ease both;
            border: 1px solid;
        }}
        .status-ok {{
            background: {p['card_bg']};
            border-color: {p['card_border']};
            color: {p['text']};
        }}
        .status-alert {{
            background: rgba(213,0,28,0.06);
            border-color: {p['accent']};
            color: {"#d5001c" if theme == "light" else "#ff2d3f"};
            font-weight: 600;
        }}
        .status-warn {{
            background: {p['card_bg']};
            border-color: {p['card_border']};
            color: {"#92400e" if theme == "light" else "#fcd34d"};
            margin-top: 10px;
        }}
        .status-success {{
            background: {p['card_bg']};
            border-color: {p['text']};
            color: {p['text']};
            margin-top: 12px;
            font-weight: 600;
        }}

        /* ---------- Facility cards ---------- */
        .facility-card {{
            background: {p['card_bg']};
            border: 1px solid {p['card_border']};
            border-radius: 6px;
            padding: 20px;
            box-shadow: {p['card_shadow']};
            transition: all 0.2s ease;
            animation: fadeIn 0.35s ease both;
            height: 100%;
        }}
        .facility-card:hover {{
            border-color: {p['text_muted']};
            transform: translateY(-1px);
        }}
        .facility-name {{
            font-weight: 600;
            font-size: 0.92rem;
            letter-spacing: -0.01em;
        }}
        .facility-type {{
            font-size: 0.6rem;
            color: {p['text_muted']};
            text-transform: uppercase;
            letter-spacing: 0.18em;
            font-weight: 500;
            margin-top: 4px;
        }}
        .util-bar {{
            height: 6px;
            background: {p['divider']};
            border-radius: 3px;
            overflow: hidden;
            margin-top: 16px;
        }}
        .util-fill {{
            height: 100%;
            border-radius: 3px;
            transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
            animation: growBar 0.8s ease-out;
        }}

        /* ---------- Buttons ---------- */
        .stButton > button {{
            background: {p['card_bg']};
            color: {p['text']};
            font-weight: 600;
            font-size: 0.7rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            border: 1px solid {p['card_border']};
            border-radius: 4px;
            padding: 14px 20px;
            transition: all 0.15s ease;
            box-shadow: {p['card_shadow']};
            width: 100%;
        }}
        .stButton > button:hover {{
            border-color: {p['accent']};
            color: {p['accent']} !important;
            background: {p['bg_soft']};
            transform: translateY(-1px);
        }}
        .stButton > button:active {{
            transform: translateY(0);
        }}

        /* ---------- Expander ---------- */
        [data-testid="stExpander"] {{
            background: {p['card_bg']};
            border: 1px solid {p['card_border']};
            border-radius: 6px;
            overflow: hidden;
            box-shadow: {p['card_shadow']};
        }}
        [data-testid="stExpander"] summary {{
            font-weight: 600;
            font-size: 0.72rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            padding: 18px 22px;
            color: {p['text_muted']};
        }}

        /* ---------- Section titles ---------- */
        .section-title {{
            font-size: 0.68rem;
            font-weight: 700;
            color: {p['text_muted']};
            letter-spacing: 0.24em;
            text-transform: uppercase;
            margin: 4px 0 18px 0;
            display: block;
        }}

        /* ---------- Dataframe ---------- */
        [data-testid="stDataFrame"] {{
            border: 1px solid {p['card_border']} !important;
            border-radius: 6px !important;
            box-shadow: {p['card_shadow']} !important;
        }}

        /* ---------- Animations ---------- */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(4px); }}
            to   {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes growBar {{
            from {{ width: 0%; }}
        }}
    </style>
    """, unsafe_allow_html=True)