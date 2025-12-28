import re
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path

# App texts/config (labels, sidebar text, and available data columns)
from config import APP_TEXTS, SIDE_TEXTS, COL_NAMES
from utils.drive_handler import DriveManager
from data import combined_data_retrieve, thingspeak_retrieve

# UI helpers and page modules
from ui_components import data_uri, load_styles, render_header, render_footer
from station_data import BASWAP_STATIONS, OTHER_STATIONS, get_station_lookup
from map_handler import add_layers, create_map, render_map
from pages import overview_page, about_page, settings_panel

# Streamlit page metadata
st.set_page_config(page_title="BASWAP", page_icon="💧", layout="wide")

# Read URL query params (Streamlit API differs across versions)
try:
    params = st.query_params
except Exception:
    params = st.experimental_get_query_params()

def _as_scalar(v, default):
    # Streamlit query params can be a list; take the first value.
    if isinstance(v, (list, tuple)):
        return v[0] if v else default
    return v if v is not None else default

# Current route + language from URL (with safe defaults)
page = _as_scalar(params.get("page"), "Overview")
lang = _as_scalar(params.get("lang"), "vi")

# Manual refresh: clear cached data, remove the refresh flag from the URL, then rerun
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

# Only allow known pages/languages
if page not in ("Overview", "About"):
    page = "Overview"
if lang not in ("en", "vi"):
    lang = "vi"

# Shared layout sizes
MAP_HEIGHT = 600
TABLE_HEIGHT = MAP_HEIGHT - 90

# Language-specific UI strings
texts = APP_TEXTS[lang]
side_texts = SIDE_TEXTS[lang]
st.session_state["texts"] = texts

# Default UI state (only set if missing)
for k, v in {
    "target_col": COL_NAMES[0],
    "date_from": None,
    "date_to": None,
    "agg_stats": ["Median"],
    "table_cols": [COL_NAMES[0]],
    "selected_station": None,
}.items():
    st.session_state.setdefault(k, v)

# Load CSS / styling tied to the chosen layout sizes
load_styles(MAP_HEIGHT, TABLE_HEIGHT)

# Header assets + render
logo_src = data_uri("img/VGU RANGERS.png")
render_header(texts, page, lang, logo_src)

# Placeholder for drive integration (currently unused here)
dm = None

# Map station codes/ids to display names for the current language
STATION_LOOKUP = get_station_lookup(texts)

# Route to the selected page
if page == "Overview":
    # Fetch the merged dataset once, then pass it to the page renderer
    df = thingspeak_retrieve(combined_data_retrieve())
    
    overview_page(
        texts, side_texts, COL_NAMES, df, dm,
        STATION_LOOKUP, BASWAP_STATIONS, OTHER_STATIONS,
        MAP_HEIGHT, TABLE_HEIGHT,
        lang
    )
    
elif page == "About":
    about_page(lang)

# Footer
render_footer()
