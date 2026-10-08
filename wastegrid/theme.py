import streamlit as st


def get_palette(theme="light"):
    return {
        "bg": "#f4f4f5",
        "card_bg": "#ffffff",
        "border": "#e4e4e7",
        "text": "#0a0a0a",
        "muted": "#71717a",
        "accent": "#d5001c",
        "accent_bg": "rgba(213,0,28,0.06)",
        "success": "#16a34a",
        "warn": "#b45309",
        "shadow": "0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.06)",
    }


def inject_css(p):
    st.markdown(f"""
    <style>
        html, body, [class*="css"], .stApp, button, input, textarea {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }}

        .stApp {{ background: {p['bg']}; }}
        h1, h2, h3, h4, p, span, div, label {{ color: {p['text']} !important; }}

        [data-testid="stSidebar"] {{ display: none; }}
        [data-testid="stHeader"] {{ background: {p['bg']}; }}
        [data-testid="stToolbar"] {{ display: none; }}
        #MainMenu {{ visibility: hidden; }}
        footer {{ visibility: hidden; }}

        .block-container {{
            padding-top: 2rem;
            padding-bottom: 4rem;
            max-width: 1280px;
        }}

        /* Hide Streamlit's default button styling so our query-param buttons work */
        .stButton > button {{
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
            height: 0 !important;
            min-height: 0 !important;
            overflow: hidden !important;
            color: transparent !important;
        }}

        /* Header */
        .wg-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 20px;
            border-bottom: 1px solid {p['border']};
            margin-bottom: 28px;
        }}
        .wg-brand {{ display: flex; align-items: center; gap: 14px; }}
        .wg-brand img {{ width: 52px; height: 52px; }}
        .wg-title {{
            font-size: 1.6rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            line-height: 1;
            color: {p['text']};
        }}
        .wg-tagline {{
            font-size: 0.65rem;
            color: {p['muted']};
            margin-top: 6px;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            font-weight: 500;
        }}

        /* Metric row */
        .metric-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr 1.3fr 1fr;
            gap: 14px;
            margin-bottom: 20px;
        }}
        .m-card {{
            background: {p['card_bg']};
            border: 1px solid {p['border']};
            border-radius: 6px;
            padding: 22px 20px;
            box-shadow: {p['shadow']};
        }}
        .m-card.hero {{
            border: 1.5px solid {p['text']};
        }}
        .m-label {{
            font-size: 0.6rem;
            color: {p['muted']};
            text-transform: uppercase;
            letter-spacing: 0.2em;
            font-weight: 600;
            margin-bottom: 14px;
        }}
        .m-value {{
            font-size: 2.3rem;
            font-weight: 300;
            letter-spacing: -0.04em;
            line-height: 1;
            color: {p['text']};
            font-variant-numeric: tabular-nums;
        }}
        .m-card.hero .m-value {{ font-size: 2.9rem; }}
        .m-value.text {{ font-size: 1.4rem; font-weight: 400; }}
        .m-value.red {{ color: {p['accent']}; }}

        /* Status */
        .wg-status {{
            border: 1px solid {p['border']};
            background: {p['card_bg']};
            border-radius: 4px;
            padding: 14px 20px;
            font-size: 0.82rem;
            color: {p['text']};
            margin-bottom: 20px;
            box-shadow: {p['shadow']};
        }}
        .wg-status.red {{
            border-color: {p['accent']};
            background: {p['accent_bg']};
            color: {p['accent']};
            font-weight: 600;
        }}
        .wg-status.warn {{
            border-color: {p['warn']};
            color: {p['warn']};
            margin-top: -12px;
            margin-bottom: 20px;
        }}

        /* Action buttons row */
        .action-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 28px;
        }}
        .act-btn {{
            display: block;
            text-align: center;
            padding: 14px 12px;
            background: {p['card_bg']};
            border: 1px solid {p['border']};
            border-radius: 4px;
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: {p['text']} !important;
            text-decoration: none !important;
            box-shadow: {p['shadow']};
            transition: all 0.15s ease;
        }}
        .act-btn:hover {{
            border-color: {p['accent']};
            color: {p['accent']} !important;
            transform: translateY(-1px);
        }}
        .act-btn.primary {{
            background: {p['text']};
            color: {p['card_bg']} !important;
            border-color: {p['text']};
        }}
        .act-btn.primary:hover {{
            background: {p['accent']};
            border-color: {p['accent']};
            color: #ffffff !important;
        }}

        /* Section title */
        .sec-title {{
            font-size: 0.68rem;
            font-weight: 700;
            color: {p['muted']};
            letter-spacing: 0.24em;
            text-transform: uppercase;
            margin: 8px 0 16px 0;
        }}

        /* Facility cards */
        .fac-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
            margin-bottom: 32px;
        }}
        .fac-card {{
            background: {p['card_bg']};
            border: 1px solid {p['border']};
            border-radius: 6px;
            padding: 20px;
            box-shadow: {p['shadow']};
        }}
        .fac-name {{ font-weight: 600; font-size: 0.92rem; color: {p['text']}; }}
        .fac-type {{
            font-size: 0.58rem;
            color: {p['muted']};
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-weight: 500;
            margin-top: 4px;
        }}
        .fac-bar-wrap {{
            height: 6px;
            background: {p['border']};
            border-radius: 3px;
            overflow: hidden;
            margin-top: 16px;
        }}
        .fac-bar {{
            height: 100%;
            border-radius: 3px;
            transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .fac-stat {{
            margin-top: 10px;
            font-size: 0.78rem;
            color: {p['muted']};
            font-variant-numeric: tabular-nums;
        }}
        .fac-util {{
            margin-top: 6px;
            font-size: 0.66rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}

        /* Compare grid */
        .cmp-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px;
            margin-bottom: 20px;
        }}
        .cmp-card {{
            background: {p['card_bg']};
            border: 1px solid {p['border']};
            border-radius: 6px;
            padding: 22px;
            box-shadow: {p['shadow']};
        }}
        .cmp-label {{
            font-size: 0.6rem;
            color: {p['muted']};
            text-transform: uppercase;
            letter-spacing: 0.2em;
            font-weight: 600;
            margin-bottom: 12px;
        }}
        .cmp-value {{
            font-size: 2.2rem;
            font-weight: 300;
            letter-spacing: -0.04em;
            line-height: 1;
            font-variant-numeric: tabular-nums;
        }}
        .cmp-value.red {{ color: {p['accent']}; }}

        /* Success banner */
        .success-banner {{
            border: 1px solid {p['text']};
            background: {p['card_bg']};
            border-radius: 4px;
            padding: 14px 20px;
            font-size: 0.82rem;
            font-weight: 600;
            color: {p['text']};
            box-shadow: {p['shadow']};
            margin-top: 12px;
        }}
    </style>
    """, unsafe_allow_html=True)