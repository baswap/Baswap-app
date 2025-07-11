import streamlit as st
import folium
from streamlit_folium import st_folium
from datetime import datetime

from config import SECRET_ACC, APP_TEXTS, COL_NAMES
from utils.drive_handler import DriveManager
from data import combined_data_retrieve, thingspeak_retrieve
from aggregation import filter_data, apply_aggregation
from plotting import plot_line_chart, display_statistics

st.set_page_config(page_title="BASWAP", page_icon="💧", layout="wide")
dm = DriveManager(SECRET_ACC)

st.markdown("""
<style>
header {visibility:hidden;}
.custom-header{position:fixed;top:0;left:0;right:0;height:4.5rem;display:flex;align-items:center;gap:2rem;padding:0 1rem;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.1);z-index:1000;}
.custom-header .logo{font-size:1.65rem;font-weight:600;color:#000;}
.custom-header .nav{display:flex;gap:1rem;}
.custom-header .nav a{font-size:.9rem;color:#262730;text-decoration:none;padding-bottom:.25rem;border-bottom:2px solid transparent;}
.custom-header .nav a.active{color:#09c;border-bottom-color:#09c;}
body > .main{margin-top:4.5rem;}
</style>
""", unsafe_allow_html=True)

qs = st.query_params
page = qs.get("page", "Overview")
lang = qs.get("lang", "vi")
page = page if page in ("Overview", "About") else "Overview"
lang = lang if lang in ("vi", "en") else "vi"
texts = APP_TEXTS[lang]
toggle_l = "en" if lang == "vi" else "vi"

st.markdown(f"""
<div class="custom-header">
  <div class="logo">BASWAP</div>
  <div class="nav">
    <a href="?page=Overview&lang={lang}" class="{'active' if page=='Overview' else ''}" target="_self">{texts.get('nav_overview','Overview')}</a>
    <a href="?page=About&lang={lang}" class="{'active' if page=='About' else ''}" target="_self">{texts.get('nav_about','About')}</a>
  </div>
  <div class="nav" style="margin-left:auto;">
    <a href="?page={page}&lang={toggle_l}" target="_self">{texts['toggle_button']}</a>
  </div>
</div>
""", unsafe_allow_html=True)

if page == "Overview":
    m = folium.Map(location=[10.231140, 105.980999], zoom_start=8)
    st_folium(m, width="100%", height=400)

    st.title(texts["app_title"])
    st.markdown(texts["description"])

    df = thingspeak_retrieve(combined_data_retrieve())
    first_date = datetime(2025, 1, 17).date()
    last_date = df["Timestamp (GMT+7)"].max().date()

    defaults = {
        "date_from": first_date,
        "date_to": last_date,
        "target_col": COL_NAMES[0],
        "agg_functions": [],
        "show_settings": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    filtered_df = filter_data(df, st.session_state.date_from, st.session_state.date_to)
    display_statistics(filtered_df, st.session_state.target_col)

    label = texts.get("hide_settings", "Hide settings") if st.session_state.show_settings else texts.get("show_settings", "Show settings")
    if st.button(f"⚙️ {label}", key="toggle_settings"):
        st.session_state.show_settings = not st.session_state.show_settings
        st.experimental_rerun()

    if st.session_state.show_settings:
        st.subheader(texts.get("graph_settings", "Graph Settings"), anchor=False)

        st.session_state.target_col = st.selectbox(
            texts.get("measurement", "Measurement"),
            options=COL_NAMES,
            index=COL_NAMES.index(st.session_state.target_col),
            key="measurement_select",
        )

        c1, c2 = st.columns(2)
        with c1:
            st.session_state.date_from = st.date_input(
                texts.get("start_date", "Start Date"),
                value=st.session_state.date_from,
                min_value=first_date,
                max_value=last_date,
                key="date_from_picker",
            )
        with c2:
            st.session_state.date_to = st.date_input(
                texts.get("end_date", "End Date"),
                value=st.session_state.date_to,
                min_value=first_date,
                max_value=last_date,
                key="date_to_picker",
            )

        b1, b2 = st.columns(2)
        with b1:
            if st.button(texts.get("first_recorded_day", "First Recorded Day"), key="first_day_btn"):
                st.session_state.date_from = first_date
        with b2:
            if st.button(texts.get("last_recorded_day", "Last Recorded Day"), key="last_day_btn"):
                st.session_state.date_from = last_date
                st.session_state.date_to = last_date

        st.session_state.agg_functions = st.multiselect(
            texts.get("aggregation", "Summary Statistics"),
            options=["Min", "Max", "Median"],
            default=st.session_state.agg_functions,
            key="agg_multiselect",
        )

        st.markdown("---")

        filtered_df = filter_data(df, st.session_state.date_from, st.session_state.date_to)

    def _view(df_, title_, freq_):
        st.subheader(title_)
        plot_df = (
            df_.copy()
            if freq_ == "None"
            else apply_aggregation(
                df_,
                COL_NAMES,
                st.session_state.target_col,
                freq_,
                st.session_state.agg_functions,
            )
        )
        plot_line_chart(plot_df, st.session_state.target_col, freq_)

    _view(filtered_df, f"{texts['raw_view']} {st.session_state.target_col}", "None")
    _view(filtered_df, f"{texts['hourly_view']} {st.session_state.target_col}", "Hour")
    _view(filtered_df, f"{texts['daily_view']} {st.session_state.target_col}", "Day")

    st.subheader(texts["data_table"])
    cols_to_show = st.multiselect(texts["columns_select"], options=COL_NAMES, default=COL_NAMES)
    cols_to_show.insert(0, "Timestamp (GMT+7)")
    st.write(f"{texts['data_dimensions']} ({filtered_df.shape[0]}, {len(cols_to_show)}).")
    st.dataframe(filtered_df[cols_to_show], use_container_width=True)

    st.button(texts["clear_cache"], help="Clears cached data for fresh fetch.", on_click=st.cache_data.clear)

else:
    st.title("About")
    st.markdown(
        """
        **BASWAP** is a buoy-based water-quality monitoring dashboard for Vĩnh Long,
        Việt Nam, providing near-real-time insights into electrical conductivity,
        temperature and battery status across multiple measurement stations.
        """
    )
