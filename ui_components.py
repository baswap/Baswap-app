import streamlit as st
from pathlib import Path
import base64, mimetypes

def data_uri(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"

def load_styles(MAP_HEIGHT, TABLE_HEIGHT):
    """Inject all app CSS."""
    st.markdown(f"""
    <style>
      /* Hide Streamlit default header */
      header{{visibility:hidden;}}

      /* Header height variable */
      :root {{ --header-h: 5rem; }}
      @media (max-width: 768px) {{ :root {{ --header-h: 2.8rem; }} }}

      /* Fixed custom header */
      .custom-header{{
        position:fixed; top:0; left:0; right:0; height:var(--header-h);
        display:flex; align-items:center; gap:1rem; padding:0 .75rem;
        background:#09c; box-shadow:0 1px 2px rgba(0,0,0,.1); z-index:1000;
      }}

      /* Brand with icon + text */
      .custom-header .logo{{ display:flex; align-items:center; gap:.5rem; color:#fff; }}
      .custom-header .logo img{{ height:calc(var(--header-h) - 1.2rem); width:auto; border-radius:4px; display:block; object-fit:contain; }}
      .custom-header .logo .text{{ font-size:clamp(1.25rem, 6vw, 2.2rem); font-weight:700; line-height:1; }}

      /* Nav links */
      .custom-header .nav{{ display:flex; gap:1rem; align-items:center; }}
      .custom-header .nav a{{
        display:inline-flex; align-items:center; line-height:1;
        text-decoration:none; font-size:clamp(.9rem, 3.5vw, 1.1rem); color:#fff; padding-bottom:.25rem;
        border-bottom:2px solid transparent;
      }}
      .custom-header .nav a.active{{ border-bottom-color:#fff; font-weight:600; }}

      /* Language dropdown */
      .lang-dd {{ position: relative; }}
      .lang-dd summary {{
        list-style:none; cursor:pointer; outline:none;
        display:inline-flex; align-items:center; gap:.35rem;
        padding:.35rem .6rem; border-radius:999px;
        border:1px solid rgba(255,255,255,.35);
        background:rgba(255,255,255,.12); color:#fff; font-weight:600;
      }}
      .lang-dd summary::-webkit-details-marker{{display:none;}}
      .lang-dd[open] summary{{background:rgba(255,255,255,.18);}}
      .lang-menu {{
        position:absolute; right:0; margin-top:.4rem; min-width:160px;
        background:#fff; color:#111; border-radius:.5rem;
        box-shadow:0 8px 24px rgba(0,0,0,.15); padding:.4rem; z-index:1200;
        border:1px solid rgba(0,0,0,.06);
      }}
      .lang-menu .item, .lang-menu .item:visited {{ color:#000 !important; }}
      .lang-menu .item {{ display:block; padding:.5rem .65rem; border-radius:.4rem; text-decoration:none; font-weight:500; }}
      .lang-menu .item:hover {{ background:#f2f6ff; }}

      /* Push content below fixed header */
      body>.main{{ margin-top:var(--header-h); }}

      /* Ensure folium map height */
      iframe[title="streamlit_folium.st_folium"]{{ height:{MAP_HEIGHT}px!important; }}

      /* Map title */
      .map-title{{
        margin:.2rem 0 .35rem; font-size:1.7rem; font-weight:600; line-height:1.2;
        display:flex; align-items:center; gap:.5rem;
      }}
      .map-title .sub{{ font-size:.95rem; font-weight:500; opacity:.8; }}

      .stButton > button{{ white-space: nowrap; }}
      .stats-title {{ font-weight: 600; }}

      .stats-scope{{
        display:inline-block;
        margin:.25rem 0 .8rem;
        padding:.4rem .6rem;
        border:1px solid rgba(0,0,0,.12);
        border-radius:4px;
        background:#fff;
      }}
      .stats-scope .k{{ color:#111; font-weight:600; }}
      .stats-scope .v{{ color:#111; font-weight:500; }}

      .info-title{{
        font-size: 1.7rem;
        font-weight: 600;
        line-height: 1.2;
        margin: .25rem 0 .6rem;
      }}

      /* Mobile overrides */
      @media (max-width: 768px){{
        .custom-header{{ gap:.5rem; padding:0 .5rem; }}
        .custom-header .logo .text{{ font-size:1.155rem; }}
        .custom-header .nav a{{ font-size:.765rem; }}
        .lang-dd summary{{
          font-size:0.7em;
          padding:.14rem .315rem;
        }}
      }}

      /* App layout glue / margins */
      html, body, [data-testid="stApp"]{{ height:100%; }}
      [data-testid="stApp"]{{ display:flex; flex-direction:column; }}

      [data-testid="stAppViewContainer"] > .main{{
        margin-top:var(--header-h) !important;
        display:flex; flex-direction:column;
        flex:1 0 auto;
      }}

      .block-container, [data-testid="block-container"]{{
        display:flex !important; flex-direction:column !important;
        min-height: calc(100vh - var(--header-h)) !important;
        padding-top: 2.5rem;
        overflow: visible !important;
      }}

      .custom-header{{ transition: transform .25s ease; will-change: transform; }}
      .custom-header.hide{{ transform: translateY(-100%); }}

      .refresh-holder .stButton > button{{ transform: translateY(2px); }}
    </style>
    """, unsafe_allow_html=True)

def render_header(texts, page, lang, logo_src):
    """Top header with nav + language picker."""
    active_overview = "active" if page == "Overview" else ""
    active_about = "active" if page == "About" else ""

    LANG_LABEL = {"en": "English", "vi": "Tiếng Việt"}
    current_lang_label = LANG_LABEL.get(lang, "English")
    toggle_tooltip = texts.get("toggle_tooltip", "")

    st.markdown(f"""
    <div class="custom-header">
      <div class="logo">
        <img src="{logo_src}" alt="BASWAP logo" />
        <span class="text">BASWAP</span>
      </div>
      <div class="nav">
        <a href="?page=Overview&lang={lang}" target="_self" class="{active_overview}">{texts['nav_overview']}</a>
        <a href="?page=About&lang={lang}" target="_self" class="{active_about}">{texts['nav_about']}</a>
      </div>
      <div class="nav" style="margin-left:auto;">
        <details class="lang-dd">
          <summary title="{toggle_tooltip}" aria-haspopup="menu" aria-expanded="false">
            <span class="label">{current_lang_label}</span>
            <span class="chev" aria-hidden="true">▾</span>
          </summary>
          <div class="lang-menu" role="menu">
            <a href="?page={page}&lang=en" target="_self" class="item {'is-current' if lang=='en' else ''}" role="menuitem">English</a>
            <a href="?page={page}&lang=vi" target="_self" class="item {'is-current' if lang=='vi' else ''}" role="menuitem">Tiếng Việt</a>
          </div>
        </details>
      </div>
    </div>
    """, unsafe_allow_html=True)

def render_footer():
    """Footer strip."""
    st.markdown("""
    <style>
      .vgu-footer{
        margin-top:auto;
        position:relative;
        left:50%; right:50%;
        margin-left:-50vw; margin-right:-50vw;
        width:100vw; box-sizing:border-box;
        background:#000;
      }

      .vgu-footer .vgu-hero{ width:100%; min-height:20px; background:#000; }

      .vgu-footer .vgu-meta{
        width:100%; background:#000;
        border-top:1px solid rgba(255,255,255,.08);
      }

      .vgu-footer .inner{
        max-width:1200px; margin:0 auto;
        padding:6px 16px 10px; box-sizing:border-box;
      }

      .vgu-footer .meta-row{
        display:flex; align-items:center; justify-content:space-between; gap:1rem;
      }

      .vgu-footer .brand{ color:#9ca3af; font-weight:300; letter-spacing:.2px; }
      .vgu-footer .social{ display:flex; align-items:center; gap:.5rem; }
      .vgu-footer .social a{ color:#9ca3af; }

      .vgu-footer .icon-btn{
        display:inline-flex; width:36px; height:36px; border-radius:999px;
        border:1px solid #2a2a2a; background:#0a0a0a;
        align-items:center; justify-content:center; text-decoration:none;
      }
      .vgu-footer .icon-btn:hover{ background:#111; border-color:#333; }
      .vgu-footer .icon-btn svg{ width:18px; height:18px; }
      .vgu-footer .icon-btn svg path{ fill: currentColor; }

      @media (max-width:640px){
        .vgu-footer .meta-row{ flex-direction:column; align-items:flex-start; gap:.5rem; }
      }
    </style>

    <footer class="vgu-footer" role="contentinfo" aria-label="App footer">
      <div class="vgu-hero"></div>
      <div class="vgu-meta">
        <div class="inner">
          <div class="meta-row">
            <div class="brand">VGU RANGERS</div>
            <div class="social">
              <a href="#" class="icon-btn" title="Facebook (coming soon)" aria-label="Facebook">
                <svg viewBox="0 0 24 24" role="img" aria-hidden="true">
                  <path d="M22 12.07C22 6.48 17.52 2 11.93 2 6.35 2 1.87 6.48 1.87 12.07c0 4.99 3.65 9.13 8.43 9.93v-7.02H7.9v-2.91h2.41V9.41c0-2.38 1.42-3.69 3.6-3.69 1.04 0 2.13.19 2.13.19v2.35h-1.2c-1.18 0-1.55.73-1.55 1.48v1.78h2.64l-.42 2.91h-2.22V22c4.78-.8 8.43-4.94 8.43-9.93z"></path>
                </svg>
              </a>
            </div>
          </div>
        </div>
      </div>
    </footer>
    """, unsafe_allow_html=True)
