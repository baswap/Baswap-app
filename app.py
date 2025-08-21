import re
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, FeatureGroupSubGroup
from datetime import datetime, timedelta
import streamlit.components.v1 as components
from config import SECRET_ACC, APP_TEXTS, SIDE_TEXTS, COL_NAMES
from utils.drive_handler import DriveManager
from data import combined_data_retrieve, thingspeak_retrieve
from aggregation import filter_data, apply_aggregation
from plotting import plot_line_chart, display_statistics
from pathlib import Path
import base64, mimetypes
from config import get_about_html
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
  .custom-header .logo{{ display:flex; align-items:center; gap:.5rem; color:#fff; }}
  .custom-header .logo img{{ height:39px; width:auto; border-radius:4px; }}



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
</style>
""", unsafe_allow_html=True)

# --- app layout glue / margins ---
st.markdown("""
<style>
  html, body, [data-testid="stApp"]{ height:100%; }
  [data-testid="stApp"]{ display:flex; flex-direction:column; }

  [data-testid="stAppViewContainer"] > .main{
    margin-top:4.5rem !important;
    display:flex; flex-direction:column;
    flex:1 0 auto;
  }

  .block-container, [data-testid="block-container"]{
    display:flex !important; flex-direction:column !important;
    min-height: calc(100vh - 4.5rem) !important;
    padding-top: 2.5rem;
    overflow: visible !important;
  }

  .custom-header{ transition: transform .25s ease; will-change: transform; }
  .custom-header.hide{ transform: translateY(-100%); }

  .refresh-holder .stButton > button{ transform: translateY(2px); }
</style>
""", unsafe_allow_html=True)

# --- Top bar with brand icon ---
active_overview = "active" if page == "Overview" else ""
active_about = "active" if page == "About" else ""
logo_src = data_uri("img/VGU RANGERS.png")  # <- your repo icon path

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

    # ---------- RIGHT: Picker + table (scrollable) ----------
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

        # --- Build "Current Measurement" from latest station rows in Drive CSV ---
        # Expect a CSV with columns equivalent to: station_name, Measdate, EC(g/l)
        def _norm_name(name: str) -> str:
            import unicodedata, re
            s = unicodedata.normalize("NFKD", str(name or ""))
            s = "".join(c for c in s if unicodedata.category(c) != "Mn")  # strip accents
            s = re.sub(r"[\W_]+", "", s)  # remove spaces/punct
            return s.lower()

        def _norm_col(col: str) -> str:
            import re
            return re.sub(r"[^a-z0-9]", "", str(col).lower())

        def _resolve_cols(df_cols) -> tuple[str, str, str]:
            # Return (station_col, time_col, ec_col) by flexible matching
            norm_map = {_norm_col(c): c for c in df_cols}
            stn_candidates = ["stationname", "station", "stationid", "name"]
            time_candidates = ["measdate", "datetime", "timestamp", "time", "date"]
            ec_candidates = ["ecgl", "ec", "ecvalue"]  # matches EC(g/l) or EC[g/l]

            def pick(cands):
                for k in cands:
                    if k in norm_map:
                        return norm_map[k]
                return None

            stn = pick(stn_candidates)
            tcol = pick(time_candidates)
            ecol = pick(ec_candidates)
            if not (stn and tcol and ecol):
                raise ValueError("Required columns not found.")
            return stn, tcol, ecol

        latest_values = {}  # normalized station_name -> EC*2000
        try:
            file_id = st.secrets.get("STATIONS_FILE_ID")
            if file_id:
                df_all = dm.read_csv_file(file_id)
                stn_col, time_col, ec_col = _resolve_cols(df_all.columns)

                d = df_all.copy()
                d[time_col] = pd.to_datetime(d[time_col], errors="coerce")
                d = d.dropna(subset=[time_col])
                idx = d.groupby(stn_col)[time_col].idxmax()   # latest row per station
                latest = d.loc[idx, [stn_col, ec_col]].copy()
                latest["key"] = latest[stn_col].map(_norm_name)
                latest["val"] = pd.to_numeric(latest[ec_col], errors="coerce") * 2000.0
                latest_values = dict(zip(latest["key"], latest["val"]))
        except Exception:
            latest_values = {}

        station_names = [s["name"] for s in OTHER_STATIONS]
        rows = []
        for name in station_names:
            key = _norm_name(name)
            val = latest_values.get(key)
            display_val = "-" if val is None or pd.isna(val) else f"{val:.1f}"
            rows.append({
                texts["table_station"]: name,
                texts["current_measurement"]: display_val,
                texts["table_warning"]: "-",
            })
        table_df = pd.DataFrame(rows)
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

        # render map and capture clicks (keep inside col_left so layout stays 7/3)
        map_out = st_folium(m, width="100%", height=MAP_HEIGHT, key="baswap_map")

    # --- Sync marker click -> global selection (selectbox + stats badge) ---
    clicked_label = map_out.get("last_object_clicked_tooltip") if isinstance(map_out, dict) else None
    if clicked_label and clicked_label in STATION_LOOKUP and st.session_state.get("selected_station") != clicked_label:
        st.session_state.selected_station = clicked_label
        st.rerun()

    # ---------- BELOW COLUMNS (full page width) ----------
    df = thingspeak_retrieve(combined_data_retrieve())
    first_date = df["Timestamp (GMT+7)"].min().date()
    last_date = df["Timestamp (GMT+7)"].max().date()
    one_month_ago = max(first_date, last_date - timedelta(days=30))

    if st.session_state.get("date_from") is None:
        st.session_state.date_from = one_month_ago
    if st.session_state.get("date_to") is None:
        st.session_state.date_to = last_date

    # --- Overall Statistics header (title only) ---
    sh_left, sh_right = st.columns([8, 1], gap="small")
    with sh_left:
        st.markdown(f"### 📊 {texts['overall_stats_title']}")
    with sh_right:
        st.empty()

    # ---- Scope label + REFRESH button on the same row ----
    scope_label = texts.get("scope_label") or ("Station" if lang == "en" else "Trạm")
    none_label = "None" if lang == "en" else "Chưa chọn trạm"
    selected_station = st.session_state.get("selected_station")
    station_name_label = selected_station if selected_station else none_label

    c_label, c_btn = st.columns([8, 1], gap="small")
    with c_label:
        st.markdown(
            f'<div class="stats-scope"><span class="k">{scope_label}:</span> '
            f'<span class="v">{station_name_label}</span></div>',
            unsafe_allow_html=True,
        )
    with c_btn:
        if st.button(
            texts["clear_cache"],
            key="clear_cache_btn",
            help=texts.get("clear_cache_tooltip", "Clear cached data and fetch the latest data."),
            type="primary",
            use_container_width=True,
        ):
            st.cache_data.clear()
            st.rerun()

    # --- Overall Statistics logic ---
    t_max = texts.get("stats_max", "Maximum")
    t_min = texts.get("stats_min", "Minimum")
    t_avg = texts.get("stats_avg", "Average")
    t_std = texts.get("stats_std", "Std Dev")

    def _show_dash_metrics():
        c1, c2, c3, c4 = st.columns(4)
        for c, lab in zip((c1, c2, c3, c4), (t_max, t_min, t_avg, t_std)):
            c.metric(label=lab, value="-")

    def _norm_name_local(name: str) -> str:
        import unicodedata, re
        s = unicodedata.normalize("NFKD", str(name or ""))
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        s = re.sub(r"[\W_]+", "", s)
        return s.lower()

    def _pick_ec_col(cols) -> str | None:
        # Flexible EC(g/l) resolver for both datasets
        import re
        def norm(s): return re.sub(r"[^a-z0-9]", "", s.lower())
        norm_map = {norm(c): c for c in cols}
        for key in ["ecgl", "ecvaluegl", "ecgperl", "ecg_l", "ecglvalue", "ecg"]:
            if key in norm_map:
                return norm_map[key]
        if "EC Value (g/l)" in cols:  # exact known BASWAP column
            return "EC Value (g/l)"
        return None

    # Branch:
    # - None -> dashes
    # - BASWAP -> original behavior (date range + target col on df)
    # - Other station -> last 1000 rows from multi-station CSV, EC(g/l)*2000
    if not selected_station:
        _show_dash_metrics()
    elif selected_station == BASWAP_NAME:
        # ORIGINAL behavior
        stats_df = filter_data(df, st.session_state.date_from, st.session_state.date_to)
        display_statistics(stats_df, st.session_state.target_col)
    else:
        # Other station: compute from multi-station CSV, last 1000 rows of EC(g/l) × 2000
        try:
            file_id = st.secrets.get("STATIONS_FILE_ID")
            if not file_id:
                _show_dash_metrics()
            else:
                df_all = dm.read_csv_file(file_id)

                # Resolve columns
                def _norm_col2(col: str) -> str:
                    import re
                    return re.sub(r"[^a-z0-9]", "", str(col).lower())

                norm_map = {_norm_col2(c): c for c in df_all.columns}
                stn_col = next((norm_map[k] for k in ["stationname", "station", "stationid", "name"] if k in norm_map), None)
                time_col = next((norm_map[k] for k in ["measdate", "datetime", "timestamp", "time", "date"] if k in norm_map), None)
                ec_col = _pick_ec_col(df_all.columns)

                if not (stn_col and time_col and ec_col):
                    _show_dash_metrics()
                else:
                    d = df_all[[stn_col, time_col, ec_col]].copy()
                    d[time_col] = pd.to_datetime(d[time_col], errors="coerce")
                    d[ec_col] = pd.to_numeric(d[ec_col], errors="coerce")
                    d = d.dropna(subset=[time_col, ec_col])

                    sel_key = _norm_name_local(selected_station)
                    mask = d[stn_col].map(_norm_name_local) == sel_key
                    sd = d.loc[mask].sort_values(time_col, ascending=False).head(1000)

                    if sd.empty:
                        _show_dash_metrics()
                    else:
                        vals = sd[ec_col] * 2000.0
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric(label=t_max, value=f"{vals.max():.2f}")
                        c2.metric(label=t_min, value=f"{vals.min():.2f}")
                        c3.metric(label=t_avg, value=f"{vals.mean():.2f}")
                        c4.metric(label=t_std, value=f"{vals.std(ddof=1):.2f}")
        except Exception:
            _show_dash_metrics()

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



# --- About page ---
if page == "About":
    

    def _img_src(path: str) -> str:
        p = Path(path)
        if not p.exists():
            return ""  # no image; the alt text will show nothing
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        b64 = base64.b64encode(p.read_bytes()).decode()
        return f"data:{mime};base64,{b64}"

    html = get_about_html(lang)
    html = html.replace("__IMG1__", _img_src("img/1.jpg")).replace("__IMG2__", _img_src("img/2.jpg"))

    st.title(texts.get("app_title", "VGU Rangers"))
    st.markdown(html, unsafe_allow_html=True)

# === FOOTER (normal flow, full-bleed, black theme) ===

st.markdown("""
<style>
  /* wrapper: full-bleed without being fixed */
  .vgu-footer{
    margin-top:auto;                 /* push to bottom when page is short */
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





