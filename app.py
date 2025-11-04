import re
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path

# App configuration and data imports
# from config import SECRET_ACC, APP_TEXTS, SIDE_TEXTS, COL_NAMES
from config import APP_TEXTS, SIDE_TEXTS, COL_NAMES
from utils.drive_handler import DriveManager
from data import combined_data_retrieve, thingspeak_retrieve

# Component modules
from ui_components import data_uri, load_styles, render_header, render_footer
from station_data import BASWAP_STATIONS, OTHER_STATIONS, get_station_lookup
from map_handler import add_layers, create_map, render_map
from pages import overview_page, about_page, settings_panel

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

# ================== CONSTANTS & SETTINGS ==================
MAP_HEIGHT = 600
TABLE_HEIGHT = MAP_HEIGHT - 90

# ================== TEXTS / LANG ==================
texts = APP_TEXTS[lang]
side_texts = SIDE_TEXTS[lang]
st.session_state["texts"] = texts

# ================== SESSION DEFAULTS ==================
for k, v in {
    "target_col": COL_NAMES[0],
    "date_from": None,
    "date_to": None,
    "agg_stats": ["Median"],
    "table_cols": [COL_NAMES[0]],
    "selected_station": None,
}.items():
    st.session_state.setdefault(k, v)

# ================== STYLES ==================
load_styles(MAP_HEIGHT, TABLE_HEIGHT)


# ================== HEADER ==================
logo_src = data_uri("img/VGU RANGERS.png")
render_header(texts, page, lang, logo_src)

# ================== DATA BACKENDS ==================
# dm = DriveManager(SECRET_ACC)
dm = None

# ================== STATIONS ==================
STATION_LOOKUP = get_station_lookup(texts)

# ================== PAGE RENDERING ==================
if page == "Overview":
    # Get data once for the entire page
    df = thingspeak_retrieve(combined_data_retrieve())
    # df = combined_data_retrieve()
    
    # Render the overview page with all components
    overview_page(
        texts, side_texts, COL_NAMES, df, dm,
        STATION_LOOKUP, BASWAP_STATIONS, OTHER_STATIONS,
        MAP_HEIGHT, TABLE_HEIGHT,
        lang
    )
    
elif page == "About":
    about_page(lang)

# ================== FOOTER ==================
render_footer()
