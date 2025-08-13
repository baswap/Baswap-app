import streamlit as st
import folium
from streamlit_folium import st_folium
from datetime import datetime

from config import SECRET_ACC, APP_TEXTS, SIDE_TEXTS, COL_NAMES
from utils.drive_handler import DriveManager
from data import combined_data_retrieve, thingspeak_retrieve
from aggregation import filter_data, apply_aggregation
from plotting import plot_line_chart, display_statistics

st.set_page_config(page_title="BASWAP", page_icon="💧", layout="wide")

# --- Query params & language/page guards ---
params = st.query_params
page = params.get("page", "Overview")
lang = params.get("lang", "vi")
if page not in ("Overview", "About"):
    page = "Overview"
if lang not in ("en", "vi"):
    lang = "vi"

texts = APP_TEXTS[lang]
side_texts = SIDE_TEXTS[lang]

# Labels for current language display in the dropdown summary
LANG_LABEL = {"en": "English", "vi": "Tiếng Việt"}
current_lang_label = LANG_LABEL.get(lang, "English")
toggle_tooltip = texts.get("toggle_tooltip", "")

# Active nav classes
active_overview = "active" if page == "Overview" else ""
active_about = "active" if page == "About" else ""

# --- Session defaults ---
for k, v in {
    "target_col": COL_NAMES[0],
    "date_from": None,
    "date_to": None,
    "agg_stats": ["Min", "Max", "Median"],
    "table_cols": COL_NAMES,
}.items():
    st.session_state.setdefault(k, v)

# --- Styles ---
st.markdown("""
<style>
  header{visibility:hidden;}
  .custom-header{
    position:fixed;top:0;left:0;right:0;height:4.5rem;display:flex;align-items:center;
    gap:2rem;padding:0 1rem;background:#09c;box-shadow:0 1px 2px rgba(0,0,0,0.1);z-index:1000;
  }
  .custom-header .logo{font-size:1.65rem;font-weight:600;color:#fff;}
  .custom-header .nav{display:flex;gap:1rem;align-items:center;}
  .custom-header .nav a{
    text-decoration:none;font-size:0.9rem;color:#fff;padding-bottom:0.25rem;
    border-bottom:2px solid transparent;
  }
  .custom-header .nav a.active{border-bottom-color:#fff;font-weight:600;}

  /* Language dropdown */
  .lang-dd { position: relative; }
  .lang-dd summary {
    list-style: none; cursor: pointer; outline: none;
    display:inline-flex; align-items:center; gap:.35rem;
    padding:.35rem .6rem; border-radius:999px;
    border:1px solid rgba(255,255,255,.35);
    background: rgba(255,255,255,.12); color:#fff; font-weight:600;
  }
  .lang-dd summary::-webkit-details-marker { display: none; }
  .lang-dd summary .chev { margin-left:2px; opacity:.9; }
  .lang-dd[open] summary { background: rgba(255,255,255,.18); }

  .lang-menu {
    position:absolute; right:0; margin-top:.4rem; min-width:160px;
    background:#fff; color:#111; border-radius:.5rem;
    box-shadow:0 8px 24px rgba(0,0,0,.15); padding:.4rem; z-index:1200;
    border:1px solid rgba(0,0,0,.06);
  }
  .lang-menu .item {
    display:block; padding:.5rem .65rem; border-radius:.4rem;
    text-decoration:none; color:#111; font-weight:500;
  }
  .lang-menu .item:hover { background:#f2f6ff; }
  .lang-menu .item.is-current { background:#eef6ff; font-weight:700; }

  body>.main{margin-top:4.5rem;}
  iframe[title="streamlit_folium.st_folium"]{height:400px!important;}
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown(f"""
<div class="custom-header">
  <div class="logo">BASWAP</div>
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
        <a href="?page={page}&lang=en" class="item {'is-current' if lang=='en' else ''}" role="menuitem">English</a>
        <a href="?page={page}&lang=vi" class="item {'is-current' if lang=='vi' else ''}" role="menuitem">Tiếng Việt</a>
      </div>
    </details>
  </div>
</div>
""", unsafe_allow_html=True)

# --- Drive manager ---
dm = DriveManager(SECRET_ACC)

# --- Sidebar / settings panel ---
def settings_panel(first_date, last_date):
    st.markdown(side_texts["sidebar_header"])
    st.markdown(side_texts["sidebar_description"])
    st.selectbox(side_texts["sidebar_choose_column"], COL_NAMES, key="target_col")
    c1, c2 = st.columns(2)
    if c1.button(side_texts["sidebar_first_day"]):
        st.session_state.date_from = first_date
    if c2.button(side_texts["sidebar_today"]):
        st.session_state.date_from = st.session_state.date_to = last_date
    if st.session_state.date_from is None:
        st.session_state.date_from = first_date
    if st.session_state.date_to is None:
        st.session_state.date_to = last_date
    st.date_input(side_texts["sidebar_start_date"], min_value=first_date, max_value=last_date, key="date_from")
    st.date_input(side_texts["sidebar_end_date"], min_value=first_date, max_value=last_date, key="date_to")
    st.multiselect(side_texts["sidebar_summary_stats"], ["Min", "Max", "Median"],
                   default=["Min", "Max", "Median"], key="agg_stats")
    if not st.session_state.agg_stats:
        st.warning(texts["data_dimensions"])
        st.stop()

# --- Pages ---
if page == "Overview":
    m = folium.Map(location=[10.231140, 105.980999], zoom_start=10)
    folium.Marker([10.099833, 106.208306], tooltip="BASWAP Buoy",
                  icon=folium.Icon(icon="tint", prefix="fa", color="blue")).add_to(m)
    st_folium(m, width="100%", height=400)

    df = thingspeak_retrieve(combined_data_retrieve())
    first_date = datetime(2025, 1, 17).date()
    last_date = df["Timestamp (GMT+7)"].max().date()

    stats_df = filter_data(df, st.session_state.date_from or first_date, st.session_state.date_to or last_date)
    st.markdown(f"### 📊 {texts['overall_stats_title']}")
    display_statistics(stats_df, st.session_state.target_col)

    st.divider()
    chart_container = st.container()
    settings_label = side_texts["sidebar_header"].lstrip("# ").strip()
    with st.expander(settings_label, expanded=False):
        settings_panel(first_date, last_date)

    date_from = st.session_state.date_from or first_date
    date_to = st.session_state.date_to or last_date
    target_col = st.session_state.target_col
    agg_funcs = st.session_state.agg_stats
    filtered_df = filter_data(df, date_from, date_to)

    with chart_container:
        st.subheader(f"📈 {target_col}")
        tabs = st.tabs([texts["raw_view"], texts["hourly_view"], texts["daily_view"]])
        with tabs[0]:
            plot_line_chart(filtered_df, target_col, "None")
        with tabs[1]:
            plot_line_chart(apply_aggregation(filtered_df, COL_NAMES, target_col, "Hour", agg_funcs), target_col, "Hour")
        with tabs[2]:
            plot_line_chart(apply_aggregation(filtered_df, COL_NAMES, target_col, "Day", agg_funcs), target_col, "Day")

    st.divider()
    st.subheader(texts["data_table"])
    st.multiselect(texts["columns_select"], options=COL_NAMES, default=st.session_state.table_cols, key="table_cols")
    table_cols = ["Timestamp (GMT+7)"] + st.session_state.table_cols
    st.write(f"{texts['data_dimensions']} ({filtered_df.shape[0]}, {len(table_cols)}).")
    st.dataframe(filtered_df[table_cols], use_container_width=True)
    st.button(texts["clear_cache"], help=texts["toggle_tooltip"], on_click=st.cache_data.clear)

else:
    st.title(texts["app_title"])
    st.markdown(texts["description"])
