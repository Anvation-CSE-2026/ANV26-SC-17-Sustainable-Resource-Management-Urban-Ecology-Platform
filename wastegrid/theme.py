import streamlit as st


def get_palette(theme="light"):
    return {
        "bg": "#eef1f5",
        "card_bg": "#ffffff",
        "border": "#e2e8f0",
        "text": "#0f172a",
        "muted": "#64748b",
        "accent": "#d5001c",
        "accent_bg": "rgba(213,0,28,0.08)",
        "success": "#16a34a",
        "warn": "#f59e0b",
        "blue": "#0891b2",
        "purple": "#7c3aed",
        "shadow": "0 1px 3px rgba(15,23,42,0.08), 0 4px 12px rgba(15,23,42,0.06)",
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
            padding-bottom: 22px;
            border-bottom: 2px solid {p['text']};
            margin-bottom: 28px;
        }}
        .wg-brand {{ display: flex; align-items: center; gap: 14px; }}
        .wg-brand img {{ width: 52px; height: 52px; }}
        .wg-title {{
            font-size: 1.7rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            line-height: 1;
            color: {p['text']};
        }}
        .wg-tagline {{
            font-size: 0.68rem;
            color: {p['muted']};
            margin-top: 6px;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            font-weight: 600;
        }}

        /* Metric row */
        .metric-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr 1.3fr 1fr;
            gap: 16px;
            margin-bottom: 22px;
        }}
        .m-card {{
            background: {p['card_bg']};
            border: 1px solid {p['border']};
            border-top: 3px solid {p['blue']};
            border-radius: 8px;
            padding: 22px 22px;
            box-shadow: {p['shadow']};
            transition: transform 0.2s ease;
        }}
        .m-card:hover {{ transform: translateY(-2px); }}
        .m-card.hero {{
            border-top: 3px solid {p['accent']};
        }}
        .m-card.green {{ border-top: 3px solid {p['success']}; }}
        .m-card.purple {{ border-top: 3px solid {p['purple']}; }}
        .m-label {{
            font-size: 0.62rem;
            color: {p['muted']};
            text-transform: uppercase;
            letter-spacing: 0.18em;
            font-weight: 700;
            margin-bottom: 14px;
        }}
        .m-value {{
            font-size: 2.4rem;
            font-weight: 600;
            letter-spacing: -0.03em;
            line-height: 1;
            color: {p['text']};
            font-variant-numeric: tabular-nums;
        }}
        .m-card.hero .m-value {{ font-size: 3rem; }}
        .m-value.text {{ font-size: 1.5rem; font-weight: 600; }}
        .m-value.red {{ color: {p['accent']}; }}
        .m-value.green {{ color: {p['success']}; }}

        /* Status */
        .wg-status {{
            background: {p['card_bg']};
            border: 1px solid {p['border']};
            border-left: 4px solid {p['success']};
            border-radius: 6px;
            padding: 16px 22px;
            font-size: 0.85rem;
            color: {p['text']};
            margin-bottom: 20px;
            box-shadow: {p['shadow']};
            font-weight: 500;
        }}
        .wg-status.red {{
            border-left-color: {p['accent']};
            background: {p['accent_bg']};
            color: {p['accent']};
            font-weight: 700;
        }}
        .wg-status.warn {{
            border-left-color: {p['warn']};
            background: rgba(245,158,11,0.06);
            color: {p['warn']};
            margin-top: -12px;
            margin-bottom: 20px;
            font-weight: 600;
        }}

        /* Action buttons */
        .action-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
            margin-bottom: 32px;
        }}
        .act-btn {{
            display: block;
            text-align: center;
            padding: 16px 12px;
            background: {p['card_bg']};
            border: 1px solid {p['border']};
            border-radius: 6px;
            font-size: 0.7rem;
            font-weight: 700;
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
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(213,0,28,0.18);
        }}
        .act-btn.primary {{
            background: {p['accent']};
            color: #ffffff !important;
            border-color: {p['accent']};
        }}
        .act-btn.primary:hover {{
            background: #b00018;
            border-color: #b00018;
            color: #ffffff !important;
            box-shadow: 0 6px 20px rgba(213,0,28,0.35);
        }}

        /* Section titles */
        .sec-title {{
            font-size: 0.72rem;
            font-weight: 800;
            color: {p['text']};
            letter-spacing: 0.22em;
            text-transform: uppercase;
            margin: 12px 0 18px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid {p['accent']};
            display: inline-block;
        }}

        /* Facility cards */
        .fac-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 36px;
        }}
        .fac-card {{
            background: {p['card_bg']};
            border: 1px solid {p['border']};
            border-radius: 8px;
            padding: 22px;
            box-shadow: {p['shadow']};
            transition: transform 0.2s ease;
        }}
        .fac-card:hover {{ transform: translateY(-2px); }}
        .fac-name {{
            font-weight: 700;
            font-size: 0.98rem;
            color: {p['text']};
        }}
        .fac-type {{
            font-size: 0.6rem;
            color: {p['muted']};
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-weight: 600;
            margin-top: 6px;
        }}
        .fac-bar-wrap {{
            height: 8px;
            background: {p['border']};
            border-radius: 4px;
            overflow: hidden;
            margin-top: 18px;
        }}
        .fac-bar {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .fac-stat {{
            margin-top: 12px;
            font-size: 0.82rem;
            color: {p['text']};
            font-weight: 500;
            font-variant-numeric: tabular-nums;
        }}
        .fac-util {{
            margin-top: 6px;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }}

        /* Comparison cards */
        .cmp-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 22px;
        }}
        .cmp-card {{
            background: {p['card_bg']};
            border: 1px solid {p['border']};
            border-top: 3px solid {p['muted']};
            border-radius: 8px;
            padding: 24px;
            box-shadow: {p['shadow']};
        }}
        .cmp-card.win {{
            border-top-color: {p['success']};
        }}
        .cmp-label {{
            font-size: 0.62rem;
            color: {p['muted']};
            text-transform: uppercase;
            letter-spacing: 0.18em;
            font-weight: 700;
            margin-bottom: 14px;
        }}
        .cmp-value {{
            font-size: 2.4rem;
            font-weight: 600;
            letter-spacing: -0.03em;
            line-height: 1;
            color: {p['text']};
            font-variant-numeric: tabular-nums;
        }}
        .cmp-value.red {{ color: {p['accent']}; }}
        .cmp-value.green {{ color: {p['success']}; }}

        /* Success banner */
        .success-banner {{
            border-left: 4px solid {p['success']};
            background: rgba(22,163,74,0.06);
            border-radius: 6px;
            padding: 16px 22px;
            font-size: 0.85rem;
            font-weight: 700;
            color: {p['success']};
            box-shadow: {p['shadow']};
            margin-top: 14px;
        }}

        /* Streamlit widgets */
        [data-testid="stExpander"] {{
            background: {p['card_bg']};
            border: 1px solid {p['border']};
            border-radius: 8px;
            overflow: hidden;
            box-shadow: {p['shadow']};
        }}
        [data-testid="stExpander"] summary {{
            font-weight: 700;
            font-size: 0.72rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            padding: 18px 22px;
            color: {p['text']};
        }}
        [data-testid="stDataFrame"] {{
            border: 1px solid {p['border']} !important;
            border-radius: 8px !important;
            overflow: hidden;
            box-shadow: {p['shadow']} !important;
        }}
        .stDownloadButton > button {{
            background: {p['text']} !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            font-size: 0.7rem !important;
            letter-spacing: 0.12em !important;
            text-transform: uppercase !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 14px 22px !important;
            transition: all 0.15s ease !important;
        }}
        .stDownloadButton > button:hover {{
            background: {p['accent']} !important;
            transform: translateY(-1px);
        }}
    </style>
    """, unsafe_allow_html=True)