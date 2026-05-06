# dashboard/style.py

def inject_global_css() -> str:
    return """\
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500&display=swap');

* { font-family: 'Geist', sans-serif; }
code, .mono { font-family: 'Geist Mono', monospace; }

.stApp { background-color: #0a0a0a; }

[data-testid="stSidebar"] {
    background-color: #111111;
    border-right: 1px solid #1a1a1a;
}

[data-testid="stExpander"],
[data-testid="stMetric"],
div.stMetric {
    background-color: #111111;
    border: 1px solid #1a1a1a;
    border-radius: 10px;
    padding: 1rem;
}

[data-testid="stMetricValue"] {
    color: #e5e5e5;
    font-size: 1.5rem;
    font-weight: 600;
}

[data-testid="stMetricLabel"] {
    color: #737373;
    font-size: 0.75rem;
    font-family: 'Geist Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

[data-testid="stMetricDelta"] { color: #737373 !important; }
[data-testid="stMetricDelta"] svg { display: none; }

[data-testid="stSelectbox"] select,
[data-testid="stTextInput"] input {
    background-color: #111111;
    border: 1px solid #1a1a1a;
    color: #e5e5e5;
    border-radius: 6px;
}

.stButton > button {
    background-color: #e5e5e5;
    color: #0a0a0a;
    border: none;
    border-radius: 6px;
    font-weight: 500;
    transition: opacity 0.2s;
}
.stButton > button:hover { opacity: 0.85; }

h1, h2, h3 { color: #e5e5e5; font-weight: 600; }
p, li { color: #737373; }
hr { border-color: #1a1a1a; }
.block-container { padding-top: 2rem; }

:root{color-scheme:dark}
.stApp,[data-testid="stAppViewContainer"]{background-color:#0a0a0a!important}
.main,.main .block-container,[data-testid="stMainBlockContainer"],[data-testid="block-container"]{background-color:#0a0a0a!important;padding:0!important;max-width:100%!important}
section[data-testid="stMain"]>div:first-child{padding:0!important}
[data-testid="stVerticalBlock"],[data-testid="stVerticalBlockBorderWrapper"]{gap:0!important;padding:0!important}
[data-testid="stMarkdownContainer"]>div{width:100%!important}
#MainMenu,footer,header{visibility:hidden}
[data-testid="stSidebar"]{background-color:#111111!important;border-right:1px solid #1a1a1a!important}
[data-testid="stSidebar"] *{font-family:'Geist Mono',monospace!important;color:#737373!important}
[data-testid="stSidebarNavLink"]{color:#737373!important}
[data-testid="stSidebarNavLink"][aria-current="page"]{color:#e5e5e5!important;border-left:2px solid #525252!important}
body,p,span{font-family:'Geist',sans-serif!important}
</style>"""


def inject_dashboard_css() -> str:
    return """\
<style>
.main .block-container,[data-testid="stMainBlockContainer"],[data-testid="block-container"]{padding:0!important}
[data-testid="stMainBlockContainer"]>[data-testid="stVerticalBlockBorderWrapper"]>[data-testid="stVerticalBlock"]{padding:0 6rem 3rem 6rem!important}
[data-testid="metric-container"]{background-color:#111111!important;border:1px solid #1a1a1a!important;border-radius:10px!important;padding:1rem!important;box-shadow:none!important}
[data-testid="stMetricLabel"]{color:#737373!important;font-size:10px!important;letter-spacing:1.5px!important;text-transform:uppercase!important;font-family:'Geist Mono',monospace!important}
[data-testid="stMetricValue"]{color:#e5e5e5!important;font-size:24px!important;font-weight:600!important;font-family:'Geist',sans-serif!important}
[data-testid="stMetricDelta"]{color:#737373!important;font-family:'Geist',sans-serif!important}
[data-testid="stMetricDelta"] svg{display:none!important}
.stTabs [data-baseweb="tab-list"]{background-color:#111111!important;border-bottom:1px solid #1a1a1a!important;gap:0!important}
.stTabs [data-baseweb="tab"]{color:#737373!important;font-family:'Geist',sans-serif!important;font-size:13px!important;padding:10px 22px!important}
.stTabs [aria-selected="true"]{color:#e5e5e5!important;border-bottom:2px solid #525252!important;background:transparent!important}
.stTabs [data-baseweb="tab-panel"]{background-color:#0a0a0a!important;padding-top:1.5rem!important}
[data-testid="stSelectbox"]>div>div{background-color:#111111!important;border:1px solid #1a1a1a!important;border-radius:6px!important;color:#e5e5e5!important;font-family:'Geist Mono',monospace!important}
.stRadio>label,.stSelectbox>label{color:#737373!important;font-family:'Geist Mono',monospace!important;font-size:10px!important;letter-spacing:1.5px!important;text-transform:uppercase!important}
.stRadio [data-testid="stMarkdownContainer"] p{color:#737373!important;font-size:12px!important;font-family:'Geist Mono',monospace!important}
.stCaption{color:#737373!important;font-family:'Geist',sans-serif!important;font-size:12px!important}
[data-testid="stAlert"]{background-color:#111111!important;border:1px solid #1a1a1a!important;border-radius:6px!important;color:#737373!important}
h1,h2,h3{color:#e5e5e5!important;font-family:'Geist',sans-serif!important}
.stMarkdown p{color:#737373!important;font-family:'Geist',sans-serif!important}
</style>"""
