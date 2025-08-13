import re
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, FeatureGroupSubGroup
from datetime import datetime, timedelta

from config import SECRET_ACC, APP_TEXTS, SIDE_TEXTS, COL_NAMES
from utils.drive_handler import DriveManager
from data import combined_data_retrieve, thingspeak_retrieve
from aggregation import filter_data, apply_aggregation
from plotting import plot_line_chart, display_statistics

# ================== PAGE CONFIG ==================
st.set_page_config(page_title="BASWAP", page_icon="💧", layout="wide")

params = st.query_params
page = params.get("page", "Overview")
lang = params.get("lang", "vi")
if page not in ("Overview", "About"):
    page = "Overview"
if lang not in ("en", "vi"):
    lang = "vi"

texts = APP_TEXTS[lang]
side_texts = SIDE_TEXTS[lang]

LANG_LABEL = {"en": "English", "vi": "Tiếng Việt"}
current_lang_label = LANG_LABEL.get(lang, "English")
toggle_tooltip = texts.get("toggle_tooltip", "")

# ================== SESSION DEFAULTS ==================
for k, v in {
    "target_col": COL_NAMES[0],
    "date_from": None,      # set after data loads
    "date_to": None,        # set after data loads
    "agg_stats": ["Min", "Max", "Median"],
    "table_cols": COL_NAMES,
    "selected_station": None,  # for map zooming
}.items():
    st.session_state.setdefault(k, v)

# ================== STYLES / HEIGHTS ==================
MAP_HEIGHT = 720            # tall map
TABLE_HEIGHT = MAP_HEIGHT - 130  # reduce table height to visually align with map
st.markdown(f"""
<style>
  header{{visibility:hidden;}}
  .custom-header{{
    position:fixed;top:0;left:0;right:0;height:4.5rem;display:flex;align-items:center;
    gap:2rem;padding:0 1rem;background:#09c;box-shadow:0 1px 2px rgba(0,0,0,.1);z-index:1000;
  }}
  .custom-header .logo{{font-size:1.65rem;font-weight:600;color:#fff;}}
  .custom-header .nav{{display:flex;gap:1rem;align-items:center;}}
  .custom-header .nav a{{
    text-decoration:none;font-size:0.9rem;color:#fff;padding-bottom:0.25rem;
    border-bottom:2px solid transparent;
  }}
  .custom-header .nav a.active{{border-bottom-color:#fff;font-weight:600;}}

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

  body>.main{{margin-top:4.5rem;}}

  /* Ensure folium map height */
  iframe[title="streamlit_folium.st_folium"]{{height:{MAP_HEIGHT}px!important;}}
</style>
""", unsafe_allow_html=True)

# ================== HEADER ==================
active_overview = "active" if page == "Overview" else ""
active_about = "active" if page == "About" else ""
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
        <a href="?page={page}&lang=en" target="_self" class="item {'is-current' if lang=='en' else ''}" role="menuitem">English</a>
        <a href="?page={page}&lang=vi" target="_self" class="item {'is-current' if lang=='vi' else ''}" role="menuitem">Tiếng Việt</a>
      </div>
    </details>
  </div>
</div>
""", unsafe_allow_html=True)

# ================== DATA BACKENDS ==================
dm = DriveManager(SECRET_ACC)

# ================== STATIONS ==================
OTHER_STATIONS = [
    {"name":"An Thuận","lon":106.6050222,"lat":9.976388889},
    {"name":"Trà Kha","lon":106.2498341,"lat":9.623059755},
    {"name":"Cầu Quan","lon":106.1139858,"lat":9.755832963},
    {"name":"Trà Vinh","lon":106.3554593,"lat":9.976579766},
    {"name":"Hưng Mỹ","lon":106.4509515,"lat":9.885625852},
    {"name":"Bến Trại","lon":106.5241047,"lat":9.883471894},
    {"name":"Lộc Thuận","lon":106.6030561,"lat":10.24436142},
    {"name":"Sơn Đốc","lon":106.4638095,"lat":10.05325888},
    {"name":"Bình Đại","lon":106.7077466,"lat":10.20537343},
    {"name":"An Định","lon":106.4292222,"lat":10.3122585},
    {"name":"Hòa Bình","lon":106.5923811,"lat":10.28936244},
    {"name":"Vàm Kênh","lon":106.7367911,"lat":10.27264736},
    {"name":"Đồng Tâm","lon":106.334365,"lat":10.329834},
    {"name":"Hương Mỹ","lon":106.383335,"lat":9.983307},
    {"name":"Tân An","lon":106.4157942,"lat":10.54178782},
    {"name":"Tuyên Nhơn","lon":106.1937576,"lat":10.65884433},
    {"name":"Bến Lức","lon":106.4744215,"lat":10.63677295},
    {"name":"Cầu Nối","lon":106.5723735,"lat":10.41872922},
    {"name":"Xuân Khánh","lon":106.3507418,"lat":10.8419521},
    {"name":"Mỹ Tho","lon":106.3469893,"lat":10.34689161},
    {"name":"Thạnh Phú","lon":105.857877,"lat":9.498933823},
    {"name":"Đại Ngãi","lon":106.0779384,"lat":9.733924226},
    {"name":"Trần Đề","lon":106.2048576,"lat":9.528517406},
    {"name":"Sóc Trăng","lon":105.9683935,"lat":9.60610964},
    {"name":"Long Phú","lon":106.1514227,"lat":9.61341221},
    {"name":"An Lạc Tây","lon":105.9790505,"lat":9.853617387},
    {"name":"Mỹ Hòa","lon":106.3454055,"lat":10.22267205},
    {"name":"Rạch Giá","lon":105.0840604,"lat":10.01215053},
    {"name":"Xẻo Rô","lon":105.1129466,"lat":9.86417299},
    {"name":"Gò Quao","lon":105.2774089,"lat":9.722549732},
    {"name":"An Ninh","lon":105.1245146,"lat":9.87196146},
    {"name":"Phước Long","lon":105.4609733,"lat":9.43721774},
    {"name":"Gành Hào","lon":105.4183437,"lat":9.032165591},
    {"name":"Cà Mau","lon":105.1497391,"lat":9.171865534},
    {"name":"Sông Đốc","lon":104.8336191,"lat":9.040111339},
    {"name":"Vũng Liêm","lon":106.2329204,"lat":10.08355046},
    {"name":"Chù Chí","lon":105.318965,"lat":9.303196225},
    {"name":"Bạc Liêu","lon":105.7212312,"lat":9.281556339},
    {"name":"Thới Bình","lon":105.0868866,"lat":9.3479814},
    {"name":"Luyến Quỳnh","lon":104.9466043,"lat":10.16807224},
    {"name":"Măng Thít","lon":106.1562281,"lat":10.16149561},
    {"name":"Tám Ngàn","lon":104.8420667,"lat":10.32105},
]

# BASWAP buoy constant
BASWAP_NAME = "BASWAP Buoy"
BASWAP_LATLON = (10.099833, 106.208306)

# Fast lookup for zooming (includes BASWAP + others)
STATION_LOOKUP = {s["name"]: (float(s["lat"]), float(s["lon"])) for s in OTHER_STATIONS}
STATION_LOOKUP[BASWAP_NAME] = BASWAP_LATLON

# ================== MAP HELPERS ==================
def add_layers(m: folium.Map):
    """
    Shared clustering across BASWAP + Other, with separate toggles.
    When zoomed out, markers from both layers merge into one cluster count.
    """
    # One shared clusterer (hidden from LayerControl)
    shared_cluster = MarkerCluster(name="All stations (clusterer)", control=False)
    shared_cluster.add_to(m)

    # Two togglable sub-groups that share the clusterer
    baswap_sub = FeatureGroupSubGroup(shared_cluster, name="BASWAP stations", show=True)
    other_sub  = FeatureGroupSubGroup(shared_cluster, name="Other stations",  show=True)
    m.add_child(baswap_sub)
    m.add_child(other_sub)

    # BASWAP marker — identical behavior, only icon differs
    folium.Marker(
        BASWAP_LATLON,
        tooltip=BASWAP_NAME,
        icon=folium.Icon(icon="tint", prefix="fa", color="blue"),
    ).add_to(baswap_sub)

    # Other stations
    for s in OTHER_STATIONS:
        folium.Marker(
            [float(s["lat"]), float(s["lon"])],
            tooltip=s["name"],
            icon=folium.Icon(icon="life-ring", prefix="fa", color="gray"),
        ).add_to(other_sub)

    # Exactly two checkboxes
    folium.LayerControl(collapsed=False).add_to(m)

# ================== SIDEBAR SETTINGS ==================
def settings_panel(first_date, last_date, default_from, default_to):
    st.markdown(side_texts["sidebar_header"])
    st.markdown(side_texts["sidebar_description"])
    st.selectbox(side_texts["sidebar_choose_column"], COL_NAMES, key="target_col")

    c1, c2 = st.columns(2)
    if c1.button(side_texts["sidebar_first_day"]):
        st.session_state.date_from = first_date
    if c2.button(side_texts["sidebar_today"]):
        st.session_state.date_from = default_to
        st.session_state.date_to = default_to

    # Set defaults if not chosen yet
    if st.session_state.date_from is None:
        st.session_state.date_from = default_from
    if st.session_state.date_to is None:
        st.session_state.date_to = default_to

    st.date_input(
        side_texts["sidebar_start_date"],
        min_value=first_date, max_value=last_date, key="date_from"
    )
    st.date_input(
        side_texts["sidebar_end_date"],
        min_value=first_date, max_value=last_date, key="date_to"
    )

    st.multiselect(
        side_texts["sidebar_summary_stats"],
        ["Min", "Max", "Median"],
        default=["Min", "Max", "Median"],
        key="agg_stats"
    )
    if not st.session_state.agg_stats:
        st.warning(texts["data_dimensions"])
        st.stop()

# ================== PAGES ==================
if page == "Overview":
    # --- Layout: Map (70%) + Right box (30%) ---
    col_left, col_right = st.columns([7, 3], gap="small")

    # ---------- RIGHT: Picker + 2×42 table (scrollable) ----------
    with col_right:
        st.markdown("#### Information ")

        # Picker with None + BASWAP + others
        station_options = ["None", BASWAP_NAME] + [s["name"] for s in OTHER_STATIONS]
        default_sel = st.session_state.get("selected_station", "None")
        if default_sel not in station_options:
            default_sel = "None"

        picked = st.selectbox(
            label="Pick a station",
            options=station_options,
            index=station_options.index(default_sel),
        )
        st.session_state.selected_station = None if picked == "None" else picked

        # 2×42 table: Station | Warning("-")  (keeps ONLY the 42 'Other' stations)
        station_names = [s["name"] for s in OTHER_STATIONS]
        warnings_col = ["-"] * len(station_names)
        table_df = pd.DataFrame({"Station": station_names, "Warning": warnings_col})
        st.dataframe(
            table_df,
            use_container_width=True,
            hide_index=True,
            height=TABLE_HEIGHT,
        )

    # ---------- LEFT: Map (tall) with zoom-to-station ----------
    with col_left:
        # Default view
        center = [10.2, 106.0]
        zoom = 8
        highlight_location = None

        sel = st.session_state.selected_station
        if sel and sel in STATION_LOOKUP:
            lat, lon = STATION_LOOKUP[sel]
            center = [lat, lon]
            zoom = 12   # tweak (12–14) for tighter focus
            highlight_location = (lat, lon)

        m = folium.Map(location=center, zoom_start=zoom, tiles=None)
        folium.TileLayer("OpenStreetMap", name="Basemap", control=False).add_to(m)
        add_layers(m)

        if highlight_location:
            folium.CircleMarker(
                location=highlight_location,
                radius=10,
                weight=3,
                fill=True,
                fill_opacity=0.2,
                color="#0077ff",
                tooltip=sel,
            ).add_to(m)

        st_folium(m, width="100%", height=MAP_HEIGHT, key="baswap_map")

    # --- Load data & set default date window = last 1 month ---
    df = thingspeak_retrieve(combined_data_retrieve())
    first_date = df["Timestamp (GMT+7)"].min().date()
    last_date = df["Timestamp (GMT+7)"].max().date()
    one_month_ago = max(first_date, last_date - timedelta(days=30))

    # --- Overall stats defaults ---
    if st.session_state.date_from is None:
        st.session_state.date_from = one_month_ago
    if st.session_state.date_to is None:
        st.session_state.date_to = last_date

    stats_df = filter_data(df, st.session_state.date_from, st.session_state.date_to)
    st.markdown(f"### 📊 {texts['overall_stats_title']}")
    display_statistics(stats_df, st.session_state.target_col)

    st.divider()

    # --- Settings (in expander) ---
    chart_container = st.container()
    settings_label = side_texts["sidebar_header"].lstrip("# ").strip()
    with st.expander(settings_label, expanded=False):
        settings_panel(first_date, last_date, one_month_ago, last_date)

    # Use (possibly updated) dates
    date_from = st.session_state.date_from
    date_to = st.session_state.date_to
    target_col = st.session_state.target_col
    agg_funcs = st.session_state.agg_stats
    filtered_df = filter_data(df, date_from, date_to)

    # --- Charts: Hourly & Daily ---
    with chart_container:
        st.subheader(f"📈 {target_col}")
        tabs = st.tabs([texts["hourly_view"], texts["daily_view"]])

        with tabs[0]:
            hourly = apply_aggregation(filtered_df, COL_NAMES, target_col, "Hour", agg_funcs)
            plot_line_chart(hourly, target_col, "Hour")

        with tabs[1]:
            daily = apply_aggregation(filtered_df, COL_NAMES, target_col, "Day", agg_funcs)
            plot_line_chart(daily, target_col, "Day")

    st.divider()
    st.subheader(texts["data_table"])
    st.multiselect(texts["columns_select"], options=COL_NAMES,
                   default=st.session_state.table_cols, key="table_cols")
    table_cols = ["Timestamp (GMT+7)"] + st.session_state.table_cols
    st.write(f"{texts['data_dimensions']} ({filtered_df.shape[0]}, {len(table_cols)}).")
    st.dataframe(filtered_df[table_cols], use_container_width=True)
    st.button(texts["clear_cache"], help=texts["toggle_tooltip"], on_click=st.cache_data.clear)

else:
    st.title(texts["app_title"])
    st.markdown(texts["description"])
