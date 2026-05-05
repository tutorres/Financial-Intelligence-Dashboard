# dashboard/style.py

def inject_global_css() -> str:
    return """\
<style>
@import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500;600;700&display=swap');
:root{color-scheme:dark}
.stApp,[data-testid="stAppViewContainer"]{background-color:#0d0d0d!important}
.main,.main .block-container,[data-testid="stMainBlockContainer"],[data-testid="block-container"]{background-color:#0d0d0d!important;padding:0!important;max-width:100%!important}
section[data-testid="stMain"]>div:first-child{padding:0!important}
[data-testid="stVerticalBlock"],[data-testid="stVerticalBlockBorderWrapper"]{gap:0!important;padding:0!important}
[data-testid="stMarkdownContainer"]>div{width:100%!important}
#MainMenu,footer,header{visibility:hidden}
[data-testid="stSidebar"]{background-color:#141414!important;border-right:1px solid #252525!important}
[data-testid="stSidebar"] *{font-family:'Geist Mono',monospace!important;color:#8d8d8d!important}
[data-testid="stSidebarNavLink"]{color:#8d8d8d!important}
[data-testid="stSidebarNavLink"][aria-current="page"]{color:#00ff88!important;border-left:2px solid #00ff88!important}
body,p,span{font-family:'Geist',sans-serif!important}
</style>"""


def inject_dashboard_css() -> str:
    return """\
<style>
.main .block-container,[data-testid="stMainBlockContainer"],[data-testid="block-container"]{padding:0!important}
[data-testid="stMainBlockContainer"]>[data-testid="stVerticalBlockBorderWrapper"]>[data-testid="stVerticalBlock"]{padding:0 6rem 3rem 6rem!important}
[data-testid="metric-container"]{background-color:#141414!important;border:1px solid #252525!important;border-radius:6px!important;padding:1rem!important;box-shadow:0 1px 4px rgba(0,0,0,.35)!important}
[data-testid="stMetricLabel"]{color:#8d8d8d!important;font-size:10px!important;letter-spacing:1.5px!important;text-transform:uppercase!important;font-family:'Geist Mono',monospace!important}
[data-testid="stMetricValue"]{color:#fcfcfc!important;font-size:24px!important;font-weight:700!important;font-family:'Geist',sans-serif!important}
[data-testid="stMetricDelta"]{font-family:'Geist',sans-serif!important}
.stTabs [data-baseweb="tab-list"]{background-color:#141414!important;border-bottom:1px solid #252525!important;gap:0!important}
.stTabs [data-baseweb="tab"]{color:#8d8d8d!important;font-family:'Geist',sans-serif!important;font-size:13px!important;padding:10px 22px!important}
.stTabs [aria-selected="true"]{color:#00ff88!important;border-bottom:2px solid #00ff88!important;background:transparent!important}
.stTabs [data-baseweb="tab-panel"]{background-color:#0d0d0d!important;padding-top:1.5rem!important}
[data-testid="stSelectbox"]>div>div{background-color:#141414!important;border:1px solid #252525!important;border-radius:6px!important;color:#fcfcfc!important;font-family:'Geist Mono',monospace!important}
.stRadio>label,.stSelectbox>label{color:#8d8d8d!important;font-family:'Geist Mono',monospace!important;font-size:10px!important;letter-spacing:1.5px!important;text-transform:uppercase!important}
.stRadio [data-testid="stMarkdownContainer"] p{color:#8d8d8d!important;font-size:12px!important;font-family:'Geist Mono',monospace!important}
.stCaption{color:#8d8d8d!important;font-family:'Geist',sans-serif!important;font-size:12px!important}
[data-testid="stAlert"]{background-color:#141414!important;border:1px solid #252525!important;border-radius:6px!important;color:#8d8d8d!important}
h1,h2,h3{color:#fcfcfc!important;font-family:'Geist',sans-serif!important}
.stMarkdown p{color:#fcfcfc!important;font-family:'Geist',sans-serif!important}
</style>"""
