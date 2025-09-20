import streamlit as st

def setup_styles(MAP_HEIGHT):
    st.markdown(f"""
    <style>
      /* Hide Streamlit default header */
      header{{visibility:hidden;}}

      /* Header height variable */
      :root {{ --header-h: 5rem; }}                         /* desktop/tablet */
      @media (max-width: 768px) {{ :root {{ --header-h: 2.8rem; }} }}  /* phones */

      /* Fixed custom header */
      .custom-header{{
        position:fixed; top:0; left:0; right:0; height:var(--header-h);
        display:flex; align-items:center; gap:1rem; padding:0 .75rem;
        background:#09c; box-shadow:0 1px 2px rgba(0,0,0,.1); z-index:1000;
      }}

      /* Brand with icon + text — responsive sizes */
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

      /* Mobile overrides (≤768px) */
      @media (max-width: 768px){{
        .custom-header{{ gap:.5rem; padding:0 .5rem; }}

        /* BASWAP wordmark: +10% (from ~1.05rem → ~1.155rem) */
        .custom-header .logo .text{{ font-size:1.155rem; }}

        /* Overview/About nav: −10% (from .85rem → .765rem) */
        .custom-header .nav a{{ font-size:.765rem; }}

        /* Language control: −30% size */
        .lang-dd summary{{ 
          font-size:0.7em;                 /* 70% of parent */
          padding:.14rem .315rem;          /* 30% less than .2/.45 */
        }}
      }}
    </style>
    """, unsafe_allow_html=True)
    
    # --- app layout glue / margins ---
    st.markdown("""
    <style>
      html, body, [data-testid="stApp"]{ height:100%; }
      [data-testid="stApp"]{ display:flex; flex-direction:column; }

      [data-testid="stAppViewContainer"] > .main{
        margin-top:var(--header-h) !important;
        display:flex; flex-direction:column;
        flex:1 0 auto;
      }

      .block-container, [data-testid="block-container"]{
        display:flex !important; flex-direction:column !important;
        min-height: calc(100vh - var(--header-h)) !important;
        padding-top: 2.5rem;
        overflow: visible !important;
      }

      .custom-header{ transition: transform .25s ease; will-change: transform; }
      .custom-header.hide{ transform: translateY(-100%); }

      .refresh-holder .stButton > button{ transform: translateY(2px); }
    </style>
    """, unsafe_allow_html=True)

def create_header(logo_src, texts, lang, active_overview, active_about, current_lang_label, toggle_tooltip, page):
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
