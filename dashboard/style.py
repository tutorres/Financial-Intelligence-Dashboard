# dashboard/style.py

def inject_global_css() -> str:
    return """\
<style>
.stApp,[data-testid="stAppViewContainer"]{background-color:#0d0d0d!important}
.main,.main .block-container,[data-testid="stMainBlockContainer"],[data-testid="block-container"]{background-color:#0d0d0d!important;padding:0!important;max-width:100%!important}
section[data-testid="stMain"]>div:first-child{padding:0!important}
[data-testid="stVerticalBlock"],[data-testid="stVerticalBlockBorderWrapper"]{gap:0!important;padding:0!important}
[data-testid="stMarkdownContainer"]>div{width:100%!important}
#MainMenu,footer,header{visibility:hidden}
[data-testid="stSidebar"]{background-color:#141414!important;border-right:1px solid #252525!important}
[data-testid="stSidebar"] *{font-family:'Courier New',monospace!important;color:#94a3b8!important}
[data-testid="stSidebarNavLink"]{color:#94a3b8!important}
[data-testid="stSidebarNavLink"][aria-current="page"]{color:#00ff88!important;border-left:2px solid #00ff88!important}
body,p,span{font-family:'Courier New',monospace!important}
</style>"""


def inject_dashboard_css() -> str:
    return """\
<style>
[data-testid="metric-container"]{background-color:#141414!important;border:1px solid #252525!important;border-radius:2px!important;padding:1rem!important}
[data-testid="stMetricLabel"]{color:#94a3b8!important;font-size:10px!important;letter-spacing:1px!important;text-transform:uppercase!important;font-family:'Courier New',monospace!important}
[data-testid="stMetricValue"]{color:#f8fafc!important;font-size:24px!important;font-weight:700!important;font-family:'Courier New',monospace!important}
[data-testid="stMetricDelta"]{font-family:'Courier New',monospace!important}
.stTabs [data-baseweb="tab-list"]{background-color:#141414!important;border-bottom:1px solid #252525!important;gap:0!important}
.stTabs [data-baseweb="tab"]{color:#94a3b8!important;font-family:'Courier New',monospace!important;font-size:12px!important;letter-spacing:1px!important;padding:12px 24px!important}
.stTabs [aria-selected="true"]{color:#00ff88!important;border-bottom:2px solid #00ff88!important;background:transparent!important}
.stTabs [data-baseweb="tab-panel"]{background-color:#0d0d0d!important;padding-top:1.5rem!important}
[data-testid="stSelectbox"]>div>div{background-color:#141414!important;border:1px solid #252525!important;border-radius:2px!important;color:#f8fafc!important;font-family:'Courier New',monospace!important}
.stRadio>label,.stSelectbox>label{color:#94a3b8!important;font-family:'Courier New',monospace!important;font-size:12px!important;letter-spacing:1px!important}
.stRadio [data-testid="stMarkdownContainer"] p{color:#94a3b8!important;font-size:12px!important}
.stCaption{color:#94a3b8!important;font-family:'Courier New',monospace!important;font-size:12px!important}
[data-testid="stAlert"]{background-color:#141414!important;border:1px solid #252525!important;color:#94a3b8!important}
h1,h2,h3{color:#f8fafc!important;font-family:'Courier New',monospace!important}
.stMarkdown p{color:#f8fafc!important;font-family:'Courier New',monospace!important}
</style>"""
