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

# ── Routing & language ───────────────────────────────────────────────────────────
qs   = st.query_params
page = qs.get("page", "Overview")
lang = qs.get("lang",  "vi")
page = page if page in ("Overview", "About") else "Overview"
lang = lang if lang in ("en", "vi") else "vi"

texts      = APP_TEXTS[lang]
side_texts = SIDE_TEXTS[lang]

toggle_lang  = "en" if lang == "vi" else "vi"
toggle_label = texts["toggle_button"]
toggle_tip   = texts["toggle_tooltip"]

# ── Session defaults ─────────────────────────────────────────────────────────────
for key, default in {
    "target_col": COL_NAMES[0],
    "date_from":  None,
    "date_to":    None,
    "agg_stats":  ["Min", "Max", "Median"],
    "table_cols": COL_NAMES,
}.items():
    st.session_state.setdefault(key, default)

# ── Global CSS ──────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <style>
      header {{ visibility: hidden; }}
      .custom-header {{
          position: fixed; top: 0; left: 0; right: 0; height: 4.5rem;
          display: flex; align-items: center; gap: 2rem;
          padding: 0 1rem; background: #09c;
          box-shadow: 0 1px 2px rgba(0,0,0,0.1); z-index: 1000;
      }}
      .custom-header .logo {{ font-size: 1.65rem; font-weight: 600; color: #fff; }}
      .custom-header .nav {{ display: flex; gap: 1rem; }}
      .custom-header .nav a {{
          text-decoration: none; font-size: 0.9rem; color: #fff;
          padding-bottom: 0.25rem; border-bottom: 2px solid transparent;
      }}
      .custom-header .nav a.active {{
          border-bottom-color: #fff; font-weight: 600;
      }}
      body > .main {{ margin-top: 4.5rem; }}

      /* fix initial map gap */
      iframe[title="streamlit_folium.st_folium"] {{
        height: 400px !important;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header bar ─────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="custom-header">
      <div class="logo">BASWAP</div>
      <div class="nav">
        <a href="?page=Overview&lang={lang}"      title="{toggle_tip}"
           class="{{'active' if '{page}'=='Overview' else ''}}">Overview</a>
        <a href="?page=About&lang={lang}"         title="{toggle_tip}"
           class="{{'active' if '{page}'=='About' else ''}}">About</a>
      </div>
      <div class="nav" style="margin-left:auto;">
        <a href="?page={page}&lang={toggle_lang}" title="{toggle_tip}">{toggle_label}</a>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

dm = DriveManager(SECRET_ACC)

# ── Sidebar-style settings form ─────────────────────────────────────────────────
def settings_panel(first_date, last_date):
    st.markdown(side_texts["sidebar_header"])
    st.markdown(side_texts["sidebar_description"])

    st.selectbox(
        side_texts["sidebar_choose_column"],
        COL_NAMES,
        key="target_col",
    )

    c1, c2 = st.columns(2)
    if c1.button(side_texts["sidebar_first_day"]):
        st.session_state.date_from = first_date
    if c2.button(side_texts["sidebar_today"]):
        st.session_state.date_from = st.session_state.date_to = last_date

    # initialize dates if empty
    if st.session_state.date_from is None:
        st.session_state.date_from = first_date
    if st.session_state.date_to is None:
        st.session_state.date_to = last_date

    st.date_input(
        side_texts["sidebar_start_date"],
        min_value=first_date,
        max_value= last_date,
        key="date_from",
    )
    st.date_input(
        side_texts["sidebar_end_date"],
        min_value=first_date,
        max_value= last_date,
        key="date_to",
    )

    st.multiselect(
        side_texts["sidebar_summary_stats"],
        ["Min", "Max", "Median"],
        default=["Min", "Max", "Median"],
        key="agg_stats",
    )
    if not st.session_state.agg_stats:
        st.warning(texts["clear_cache"])  # reuse clear_cache for warning if needed
        st.stop()

# ── Overview page ───────────────────────────────────────────────────────────────
if page == "Overview":
    # Map + marker
    m = folium.Map(location=[10.231140, 105.980999], zoom_start=10)
    folium.Marker(
        [10.099833, 106.208306],
        tooltip="BASWAP Buoy",
        icon=folium.Icon(icon="tint", prefix="fa", color="blue"),
    ).add_to(m)
    st_folium(m, width="100%", height=400)

    # Data preparation
    df         = thingspeak_retrieve(combined_data_retrieve())
    first_date = datetime(2025, 1, 17).date()
    last_date  = df["Timestamp (GMT+7)"].max().date()

    # apply filters
    date_from  = st.session_state.date_from
    date_to    = st.session_state.date_to
    target_col = st.session_state.target_col
    agg_funcs  = st.session_state.agg_stats

    filtered_df = filter_data(df, date_from, date_to)
    display_statistics(filtered_df, target_col)

    # separator → chart
    st.divider()
    st.markdown("&nbsp;")

    # chart tabs
    st.subheader(f"📈 {target_col}")
    tab_raw, tab_hr, tab_day = st.tabs([
        texts["raw_view"], 
        texts["hourly_view"], 
        texts["daily_view"]
    ])
    with tab_raw:
        plot_line_chart(filtered_df, target_col, "None")
    with tab_hr:
        hr = apply_aggregation(filtered_df, COL_NAMES, target_col, "Hour", agg_funcs)
        plot_line_chart(hr, target_col, "Hour")
    with tab_day:
        dy = apply_aggregation(filtered_df, COL_NAMES, target_col, "Day", agg_funcs)
        plot_line_chart(dy, target_col, "Day")

    # separator → settings
    st.divider()
    st.markdown("&nbsp;")

    with st.expander(side_texts["sidebar_header"], expanded=False):
        settings_panel(first_date, last_date)

    # separator → table
    st.divider()
    st.markdown("&nbsp;")

    st.subheader(texts["data_table"])
    st.multiselect(
        texts["columns_select"],
        options=COL_NAMES,
        default=st.session_state.table_cols,
        key="table_cols",
    )
    table_cols = ["Timestamp (GMT+7)"] + st.session_state.table_cols
    st.write(f"{texts['data_dimensions']} ({filtered_df.shape[0]}, {len(table_cols)}).")
    st.dataframe(filtered_df[table_cols], use_container_width=True)

    st.button(texts["clear_cache"], help=texts["toggle_tooltip"], on_click=st.cache_data.clear)

# ── About page ─────────────────────────────────────────────────────────────────
else:
    st.title(texts["app_title"])
    st.markdown(texts["description"])
