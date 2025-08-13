import json
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

from config import SECRET_ACC, APP_TEXTS, SIDE_TEXTS, COL_NAMES
from utils.drive_handler import DriveManager
from data import combined_data_retrieve, thingspeak_retrieve
from aggregation import filter_data, apply_aggregation
from plotting import plot_line_chart, display_statistics

# -------------------- Page --------------------
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
LANG_LABEL = {"en": "English", "vi": "Tiếng Việt"}
current_lang_label = LANG_LABEL.get(lang, "English")
toggle_tooltip = texts.get("toggle_tooltip", "")

# --- Session defaults ---
for k, v in {
    "target_col": COL_NAMES[0],
    "date_from": None,
    "date_to": None,
    "agg_stats": ["Min", "Max", "Median"],
    "table_cols": COL_NAMES,
}.items():
    st.session_state.setdefault(k, v)

# -------------------- Styles & Header --------------------
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
  /* Make dropdown items black and stay in same tab */
  .lang-menu .item, .lang-menu .item:visited { color:#000 !important; }
  .lang-menu .item {
    display:block; padding:.5rem .65rem; border-radius:.4rem;
    text-decoration:none; font-weight:500;
  }
  .lang-menu .item:hover { background:#f2f6ff; }
  .lang-menu .item.is-current { background:#eef6ff; font-weight:700; }

  body>.main{margin-top:4.5rem;}
</style>
""", unsafe_allow_html=True)

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

# -------------------- Drive manager --------------------
dm = DriveManager(SECRET_ACC)

# -------------------- Hard-coded other stations --------------------
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

# -------------------- HTML/JS map + table component --------------------
def render_map_with_station_list(baswap_lat, baswap_lon, stations, height_px=520):
    """
    70/30 layout: Leaflet map (left) + scrollable table (right).
    Click a row to zoom & highlight marker (no page refresh).
    `stations` = list of dicts: {"name": str, "lat": float, "lon": float}
    """
    html = f"""
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"/>
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"/>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css"/>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.awesome-markers/2.0.4/leaflet.awesome-markers.css"/>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.awesome-markers/2.0.4/leaflet.awesome-markers.js"></script>

    <style>
      .mapwrap {{
        display: flex; gap: 12px;
        width: 100%;
        height: {height_px}px;
      }}
      .mapleft {{
        width: 70%;
        height: 100%;
        border-radius: 8px;
        overflow: hidden;
      }}
      .mapright {{
        width: 30%;
        height: 100%;
      }}
      .table-wrap {{
        height: 100%;
        overflow-y: auto;
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 8px;
        background: rgba(255,255,255,.03);
      }}

      /* Table look & feel */
      .station-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.95rem;
      }}
      .station-table thead th {{
        position: sticky; top: 0; z-index: 5;
        text-align: left;
        padding: 10px 12px;
        background: rgba(255,255,255,.10);
        backdrop-filter: saturate(140%) blur(2px);
        border-bottom: 1px solid rgba(255,255,255,.15);
      }}
      .station-table thead th.warn-col {{ text-align: center; width: 32%; }}
      .station-table tbody td {{
        padding: 10px 12px;
        border-bottom: 1px solid rgba(255,255,255,.06);
      }}
      .station-table tbody td.warn-col {{ text-align: center; opacity: .9; }}

      /* Row interactions */
      .station-table tbody tr {{ cursor: pointer; }}
      .station-table tbody tr:hover {{ background: rgba(255,255,255,.07); }}
      .station-table tbody tr.active {{
        outline: 2px solid #09c;
        background: rgba(0,153,204,.15);
      }}

      #map {{ width: 100%; height: 100%; }}
    </style>

    <div class="mapwrap">
      <div class="mapleft"><div id="map"></div></div>
      <div class="mapright">
        <div class="table-wrap">
          <table class="station-table">
            <thead>
              <tr>
                <th>Monitoring Station</th>
                <th class="warn-col">Warning</th>
              </tr>
            </thead>
            <tbody id="stationTbody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <script>
      // Init map
      const map = L.map('map', {{ zoomControl: true }}).setView([{baswap_lat}, {baswap_lon}], 8);
      L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
      }}).addTo(map);

      // Icons
      const blueDrop   = L.AwesomeMarkers.icon({{ icon: 'tint',      prefix: 'fa', markerColor: 'blue'   }});
      const grayRing   = L.AwesomeMarkers.icon({{ icon: 'life-ring', prefix: 'fa', markerColor: 'gray'   }});
      const orangeRing = L.AwesomeMarkers.icon({{ icon: 'life-ring', prefix: 'fa', markerColor: 'orange' }});

      // BASWAP marker
      L.marker([{baswap_lat}, {baswap_lon}], {{icon: blueDrop}}).addTo(map).bindTooltip('BASWAP Buoy');

      // Cluster + markers for other stations
      const stations = {json.dumps([{"name": s["name"], "lat": float(s["lat"]), "lon": float(s["lon"])} for s in OTHER_STATIONS])};
      const cluster = L.markerClusterGroup();
      const markers = [];

      stations.forEach((s, i) => {{
        const m = L.marker([s.lat, s.lon], {{icon: grayRing, title: s.name}}).bindTooltip(s.name);
        markers.push(m);
        cluster.addLayer(m);
      }});
      map.addLayer(cluster);

      // Build table rows
      const tbody = document.getElementById('stationTbody');
      stations.forEach((s, i) => {{
        const tr = document.createElement('tr');
        tr.setAttribute('data-idx', i);
        tr.innerHTML = `
          <td class="name-col">${{s.name}}</td>
          <td class="warn-col">-</td>
        `;
        tr.addEventListener('click', () => {{
          // highlight row
          document.querySelectorAll('.station-table tbody tr').forEach(el => el.classList.remove('active'));
          tr.classList.add('active');

          // color selected marker orange, others gray
          markers.forEach((m, idx) => m.setIcon(idx === i ? orangeRing : grayRing));

          // ensure marker is visible, then center & open tooltip
          cluster.zoomToShowLayer(markers[i], () => {{
            const ll = markers[i].getLatLng();
            map.setView(ll, Math.max(map.getZoom(), 11), {{animate: true, duration: 0.5}});
            markers[i].openTooltip();
          }});
        }});
        tbody.appendChild(tr);
      }});
    </script>
    """
    components.html(html, height=height_px + 10, scrolling=False)

# -------------------- Sidebar / settings panel --------------------
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

# -------------------- Pages --------------------
if page == "Overview":
    # Map area: ~30% taller than before, 70/30 split with a table on the right
    MAP_HEIGHT = 520
    render_map_with_station_list(
        baswap_lat=10.099833,
        baswap_lon=106.208306,
        stations=[{"name": s["name"], "lat": float(s["lat"]), "lon": float(s["lon"])} for s in OTHER_STATIONS],
        height_px=MAP_HEIGHT,
    )

    # Data + charts
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
