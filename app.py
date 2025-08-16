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
# --- refresh via query param ---
if _as_scalar(params.get("refresh"), "0") == "1":
    st.cache_data.clear()
    # remove the flag from the URL, then rerun
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
MAP_HEIGHT = 720            # tall map
TABLE_HEIGHT = MAP_HEIGHT - 80  # adjust to align visually with map

st.markdown(f"""
<style>
  /* Hide Streamlit default header */
  header{{visibility:hidden;}}

  /* Fixed custom header */
  .custom-header{{
    position:fixed; top:0; left:0; right:0; height:4.5rem;
    display:flex; align-items:center; gap:2rem; padding:0 1rem;
    background:#09c; box-shadow:0 1px 2px rgba(0,0,0,.1); z-index:1000;
  }}
  .custom-header .logo{{font-size:2.1rem; font-weight:600; color:#fff;}}
  .custom-header .nav{{display:flex; gap:1rem; align-items:center;}}
  .custom-header .nav a{{
    text-decoration:none; font-size:1.2rem; color:#fff; padding-bottom:.25rem;
    border-bottom:2px solid transparent;
  }}
  .custom-header .nav a.active{{border-bottom-color:#fff; font-weight:600;}}

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
  body>.main{{ margin-top:4.5rem; }}

  /* Ensure folium map height */
  iframe[title="streamlit_folium.st_folium"]{{ height:{MAP_HEIGHT}px!important; }}

  /* Map title */
  .map-title{{
    margin:.75rem 0 .35rem; font-size:1.7rem; font-weight:600; line-height:1.2;
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
  border-radius:4px;         /* small, not a rounded pill */
  background:#fff;           /* looks non-clickable */
}}
.stats-scope .k{{ color:#111; font-weight:600; }}   /* label: Station/Trạm */
.stats-scope .v{{ color:#111; font-weight:500; }}   /* value: name/Overall */


.info-title{{
  font-size: 1.7rem;   /* tweak size here */
  font-weight: 600;
  line-height: 1.2;
  margin: .25rem 0 .6rem;
}}

</style>
""", unsafe_allow_html=True)


active_overview = "active" if page == "Overview" else ""
# === FOOTER THEME (black bg, thin gray text, near divider) ===
st.markdown("""
<style>
  /* Full-bleed footer in normal flow (not fixed) */
  .vgu-footer{
    margin-top:auto;                           /* pushes footer to page bottom when content is short */
    position:relative; left:50%; right:50%;
    margin-left:-50vw; margin-right:-50vw;     /* edge-to-edge */
    width:100vw; box-sizing:border-box;
    background:#000;                           /* unify background across sections */
  }

  /* Top placeholder band: keep small but present for future content */
  .vgu-footer .vgu-hero{
    width:100%;
    min-height:64px;                           /* was 160px — reduced so footer content isn’t “mid-bottom” */
    background:#000;
  }

  /* Bottom bar (divider + copy/social) */
  .vgu-footer .vgu-meta{
    width:100%;
    background:#000;
    border-top:1px solid rgba(255,255,255,.08);/* subtle divider on black */
  }

  /* Constrain inner content while background stays full-bleed */
  .vgu-footer .inner{
    max-width:1200px; margin:0 auto;
    padding:6px 16px 10px;                     /* place content close to the divider line */
    box-sizing:border-box;
  }

  .vgu-footer .meta-row{
    display:flex; align-items:center; justify-content:space-between; gap:1rem;
  }

  /* Thin gray text on black */
  .vgu-footer .brand{ color:#9ca3af; font-weight:300; letter-spacing:.2px; }
  .vgu-footer .social{ display:flex; align-items:center; gap:.5rem; }
  .vgu-footer .social a{ color:#9ca3af; }

  /* Icon button tuned for dark theme */
  .vgu-footer .icon-btn{
    display:inline-flex; width:36px; height:36px; border-radius:999px;
    border:1px solid #2a2a2a; background:#0a0a0a;
    align-items:center; justify-content:center; text-decoration:none;
  }
  .vgu-footer .icon-btn:hover{ background:#111; border-color:#333; }
  .vgu-footer .icon-btn svg{ width:18px; height:18px; }
  .vgu-footer .icon-btn svg path{ fill: currentColor; }

  /* Mobile stacking */
  @media (max-width:640px){
    .vgu-footer .meta-row{ flex-direction:column; align-items:flex-start; gap:.5rem; }
  }
</style>
""", unsafe_allow_html=True)

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

# BASWAP buoy name comes from translations
BASWAP_NAME = texts["baswap_name"]
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

    # Two togglable sub-groups that share the clusterer — names are localized
    baswap_sub = FeatureGroupSubGroup(shared_cluster, name=texts["layer_baswap"], show=True)
    other_sub  = FeatureGroupSubGroup(shared_cluster, name=texts["layer_other"],  show=True)
    m.add_child(baswap_sub)
    m.add_child(other_sub)

    # BASWAP marker — identical behavior, only icon differs; tooltip localized
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

    # Exactly two checkboxes (localized group names)
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
    if st.session_state.get("date_from") is None:
        st.session_state.date_from = default_from
    if st.session_state.get("date_to") is None:
        st.session_state.date_to = last_date

    st.date_input(
        side_texts["sidebar_start_date"],
        min_value=first_date, max_value=last_date, key="date_from"
    )
    st.date_input(
        side_texts["sidebar_end_date"],
        min_value=first_date, max_value=last_date, key="date_to"
    )

    # --- LOCK the stats selector to Max and disable the widget ---
    # Ensure session value is Max
    st.session_state.agg_stats = ["Max"]

# ================== PAGES ==================
if page == "Overview":
    # --- Layout: Map (70%) + Right box (30%) ---
    col_left, col_right = st.columns([7, 3], gap="small")

    # ---------- RIGHT: Picker + 3×42 table (scrollable) ----------
    with col_right:
        st.markdown(f'<div class="info-title">{texts["info_panel_title"]}</div>', unsafe_allow_html=True)

        station_options_display = [texts["picker_none"], BASWAP_NAME] + [s["name"] for s in OTHER_STATIONS]
        current_sel = st.session_state.get("selected_station")
        default_label = current_sel if current_sel in station_options_display else texts["picker_none"]

        picked_label = st.selectbox(
            label=texts["picker_label"],
            options=station_options_display,
            index=station_options_display.index(default_label),
        )
        st.session_state.selected_station = None if picked_label == texts["picker_none"] else picked_label

        station_names = [s["name"] for s in OTHER_STATIONS]
        n = len(station_names)
        table_df = pd.DataFrame({
            texts["table_station"]: station_names,
            texts["current_measurement"]: ["-"] * n,
            texts["table_warning"]: ["-"] * n,
        })
        st.dataframe(table_df, use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

    # ---------- LEFT: Map (tall) with zoom-to-station ----------
    with col_left:
        map_title = texts.get("map_title", "🗺️ Station Map")
        st.markdown(f"""<div class="map-title">{map_title}</div>""", unsafe_allow_html=True)

        center = [10.2, 106.0]; zoom = 8; highlight_location = None
        sel = st.session_state.get("selected_station")
        if sel and sel in STATION_LOOKUP:
            lat, lon = STATION_LOOKUP[sel]
            center = [lat, lon]; zoom = 12; highlight_location = (lat, lon)

        m = folium.Map(location=center, zoom_start=zoom, tiles=None)
        folium.TileLayer("OpenStreetMap", name="Basemap", control=False).add_to(m)
        add_layers(m)

        if highlight_location:
            folium.CircleMarker(
                location=highlight_location, radius=10, weight=3, fill=True, fill_opacity=0.2,
                color="#0077ff", tooltip=sel,
            ).add_to(m)

        st_folium(m, width="100%", height=MAP_HEIGHT, key="baswap_map")

    # ---------- BELOW COLUMNS (full page width) ----------
    df = thingspeak_retrieve(combined_data_retrieve())
    first_date = df["Timestamp (GMT+7)"].min().date()
    last_date = df["Timestamp (GMT+7)"].max().date()
    one_month_ago = max(first_date, last_date - timedelta(days=30))

    if st.session_state.get("date_from") is None:
        st.session_state.date_from = one_month_ago
    if st.session_state.get("date_to") is None:
        st.session_state.date_to = last_date

    # --- Overall Statistics header + REFRESH button on the same row ---
    sh_left, sh_right = st.columns([8, 1], gap="small")
    with sh_left:
        st.markdown(f"### 📊 {texts['overall_stats_title']}")
    with sh_right:
        if st.button(
            texts["clear_cache"],
            key="clear_cache_btn",
            help=texts.get("clear_cache_tooltip", "Clear cached data and fetch the latest data."),
            type="primary",
            use_container_width=True,   # stays on one line if you added the CSS: .stButton > button { white-space: nowrap; }
        ):
            st.cache_data.clear()
            st.rerun()

    # ---- Scope label (language-aware): "Trạm: <name>" or "Station: <name>" ----
    scope_label = texts.get("scope_label") or ("Station" if lang == "en" else "Trạm")
    overall_text = texts.get("scope_overall") or ("Overall" if lang == "en" else "Chung")
    station_name = st.session_state.get("selected_station") or overall_text
    st.markdown(
        f'<div class="stats-scope"><span class="k">{scope_label}:</span> <span class="v">{station_name}</span></div>',
        unsafe_allow_html=True,
    )

    # Show the metrics
    stats_df = filter_data(df, st.session_state.date_from, st.session_state.date_to)
    display_statistics(stats_df, st.session_state.target_col)

    st.divider()

    # --- Settings (in expander) ---
    chart_container = st.container()
    settings_label = side_texts["sidebar_header"].lstrip("# ").strip()
    with st.expander(settings_label, expanded=False):
        settings_panel(first_date, last_date, one_month_ago, last_date)

    date_from = st.session_state.date_from
    date_to = st.session_state.date_to
    target_col = st.session_state.target_col
    agg_funcs = st.session_state.agg_stats
    filtered_df = filter_data(df, date_from, date_to)

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

    # Data table header
    st.subheader(texts["data_table"])

    # Column picker + table (separate widget key to avoid state conflicts)
    table_cols_sel = st.multiselect(
        texts["columns_select"],
        options=COL_NAMES,
        default=st.session_state.get("table_cols", [COL_NAMES[0]]),
        key="table_cols_picker",
    )
    st.session_state.table_cols = list(table_cols_sel)

    show_cols = ["Timestamp (GMT+7)"] + st.session_state.table_cols
    existing = [c for c in show_cols if c in filtered_df.columns]
    st.write(f"{texts['data_dimensions']} ({filtered_df.shape[0]}, {len(existing)}).")
    st.dataframe(filtered_df[existing], use_container_width=True)

elif page == "About":
    st.title(texts["app_title"])
    st.markdown(texts["description"])

# === NON-FIXED FOOTER (render once, OUTSIDE the page branches) ===
st.markdown("""
<footer class="vgu-footer" role="contentinfo" aria-label="App footer">
  <div class="vgu-hero"><!-- placeholder --></div>
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






