import re
import pandas as pd
import streamlit as st
from pathlib import Path
import base64, mimetypes

from config import SECRET_ACC, APP_TEXTS, SIDE_TEXTS, COL_NAMES
from utils.drive_handler import DriveManager
from data import combined_data_retrieve, thingspeak_retrieve
from ui_components import setup_styles, create_header
from map_components import setup_stations, OTHER_STATIONS
from pages import overview_page, about_page

# ================== PAGE CONFIG ==================
st.set_page_config(page_title="BASWAP", page_icon="💧", layout="wide")

# --- read query params + optional refresh ---
try:
    params = st.query_params
except Exception:
    params = st.experimental_get_query_params()

def _as_scalar(v, default):
    if isinstance(v, (list, tuple)):
        return v[0] if v else default
    return v if v is not None else default

page = _as_scalar(params.get("page"), "Overview")
lang = _as_scalar(params.get("lang"), "vi")

if _as_scalar(params.get("refresh"), "0") == "1":
    st.cache_data.clear()
    try:
        if hasattr(st, "query_params"):
            qp = dict(st.query_params)
            qp.pop("refresh", None)
            st.query_params.clear()
            for k, v in qp.items():
                st.query_params[k] = v
        else:
            cleaned = {k: v for k, v in params.items() if k != "refresh"}
            st.experimental_set_query_params(**cleaned)
    except Exception:
        pass
    st.rerun()

if page not in ("Overview", "About"):
    page = "Overview"
if lang not in ("en", "vi"):
    lang = "vi"

# --- helper to embed repo images inside HTML safely ---
def data_uri(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"

# ================== TEXTS / LANG ==================
texts = APP_TEXTS[lang]
side_texts = SIDE_TEXTS[lang]
st.session_state["texts"] = texts

LANG_LABEL = {"en": "English", "vi": "Tiếng Việt"}
current_lang_label = LANG_LABEL.get(lang, "English")
toggle_tooltip = texts.get("toggle_tooltip", "")

# ================== SESSION DEFAULTS ==================
for k, v in {
    "target_col": COL_NAMES[0],
    "date_from": None,
    "date_to": None,
    "agg_stats": ["Min", "Max", "Median"],
    "table_cols": [COL_NAMES[0]],
    "selected_station": None,
}.items():
    st.session_state.setdefault(k, v)

# ================== STYLES / HEIGHTS ==================
MAP_HEIGHT = 600
TABLE_HEIGHT = MAP_HEIGHT - 90

# Setup UI styles
setup_styles(MAP_HEIGHT)

# Setup stations
BASWAP_NAME, STATION_LOOKUP = setup_stations(texts, OTHER_STATIONS)

# ================== DATA BACKENDS ==================
dm = DriveManager(SECRET_ACC)

# --- Top bar with brand icon ---
active_overview = "active" if page == "Overview" else ""
active_about = "active" if page == "About" else ""
logo_src = data_uri("img/VGU RANGERS.png")  

create_header(logo_src, texts, lang, active_overview, active_about, current_lang_label, toggle_tooltip, page)

# ================== PAGES ==================
if page == "Overview":
    df = thingspeak_retrieve(combined_data_retrieve())
    overview_page(
        texts, side_texts, COL_NAMES, df, dm, 
        BASWAP_NAME, STATION_LOOKUP, OTHER_STATIONS,
        MAP_HEIGHT, TABLE_HEIGHT, lang
    )

# --- About page ---
if page == "About":
    about_page(lang)

# === FOOTER ===
st.markdown("""
<style>
  /* wrapper: full-bleed without being fixed */
  .vgu-footer{
    margin-top:auto;              
    position:relative;
    left:50%; right:50%;
    margin-left:-50vw; margin-right:-50vw;
    width:100vw; box-sizing:border-box;
    background:#000;
  }

  /* small top placeholder so content sits near the divider */
  .vgu-footer .vgu-hero{
    width:100%; min-height:20px; background:#000;
  }

  /* thin divider + meta row */
  .vgu-footer .vgu-meta{
    width:100%; background:#000;
    border-top:1px solid rgba(255,255,255,.08);
  }

  /* constrained inner width; keep text near the divider */
  .vgu-footer .inner{
    max-width:1200px; margin:0 auto;
    padding:6px 16px 10px; box-sizing:border-box;
  }

  .vgu-footer .meta-row{
    display:flex; align-items:center; justify-content:space-between; gap:1rem;
  }

  /* thin gray typography on black */
  .vgu-footer .brand{ color:#9ca3af; font-weight:300; letter-spacing:.2px; }
  .vgu-footer .social{ display:flex; align-items:center; gap:.5rem; }
  .vgu-footer .social a{ color:#9ca3af; }

  /* dark theme icon button */
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
