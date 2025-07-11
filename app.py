import streamlit as st
import folium
from streamlit_folium import st_folium
from datetime import datetime

from config import SECRET_ACC, COMBINED_ID, APP_TEXTS, COL_NAMES, SIDE_TEXTS
from utils.drive_handler import DriveManager
from data import combined_data_retrieve, thingspeak_retrieve
from aggregation import filter_data, apply_aggregation
from plotting import plot_line_chart, display_statistics

# Page configuration
st.set_page_config(page_title="BASWAP", page_icon="💧", layout="wide")

# Initialize DriveManager (if still needed elsewhere)
dm = DriveManager(SECRET_ACC)

# ── UI Header & Navigation ────────────────────────────────────────────────────
st.markdown("""
<style>
header { visibility: hidden; }
.custom-header {
    position: fixed; top: 0; left: 0; right: 0;
    height: 4.5rem; display: flex; align-items: center;
    padding: 0 1rem; background: #fff;
    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    z-index: 1000; gap: 2rem;
}
.custom-header .logo {
    font-size: 1.65rem; font-weight: 600; color: #000;
}
.custom-header .nav { display: flex; gap: 1rem; }
.custom-header .nav a {
    text-decoration: none; color: #262730;
    font-size: 0.9rem; padding-bottom: 0.25rem;
    border-bottom: 2px solid transparent;
}
.custom-header .nav a.active { color: #09c; border-bottom-color: #09c; }
body > .main { margin-top: 4.5rem; }
</style>
""", unsafe_allow_html=True)

# Read query params for page & language toggling
qs = st.experimental_get_query_params()
page = qs.get("page", ["Overview"])[0]
lang = qs.get("lang", ["vi"])[0]
if page not in ("Overview", "About"): page = "Overview"
if lang not in ("en", "vi"): lang = "vi"
toggle_lang = "en" if lang == "vi" else "vi"
toggle_label = APP_TEXTS[lang]["toggle_button"]

# Render custom header
st.markdown(f"""
<div class="custom-header">
  <div class="logo">BASWAP</div>
  <div class="nav">
    <a href="?page=Overview&lang={lang}" class="{'active' if page=='Overview' else ''}" target="_self">Overview</a>
    <a href="?page=About&lang={lang}" class="{'active' if page=='About' else ''}" target="_self">About</a>
  </div>
  <div class="nav" style="margin-left:auto;">
    <a href="?page={page}&lang={toggle_lang}" target="_self">{toggle_label}</a>
  </div>
</div>
""", unsafe_allow_html=True)

texts = APP_TEXTS[lang]

# Overview page
if page == "Overview":
    # Map
    m = folium.Map(location=[10.231140, 105.980999], zoom_start=8)
    st_folium(m, width="100%", height=400)

    # Title & description
    st.title(texts["app_title"])
    st.markdown(texts["description"])

    # Data retrieval
    df = combined_data_retrieve()
    df = thingspeak_retrieve(df)
    first_date = datetime(2025, 1, 17).date()
    last_date = df["Timestamp (GMT+7)"].max().date()

    # Session state defaults
    if "show_settings" not in st.session_state:
        st.session_state.show_settings = False
    if "date_from" not in st.session_state:
        st.session_state.date_from = first_date
    if "date_to" not in st.session_state:
        st.session_state.date_to = last_date
    if "target_col" not in st.session_state:
        st.session_state.target_col = COL_NAMES[0]
    if "agg_functions" not in st.session_state:
        st.session_state.agg_functions = ["Min", "Max", "Median"]

    # Preliminary filtered data for stats
    temp_df = filter_data(df, st.session_state.date_from, st.session_state.date_to)
    display_statistics(temp_df, st.session_state.target_col)

    # Settings toggle button
    if st.button("⚙️ Settings"):
        st.session_state.show_settings = not st.session_state.show_settings

    # Settings panel (in main area)
    if st.session_state.show_settings:
        texts_side = SIDE_TEXTS[lang]
        st.markdown(texts_side["sidebar_header"])
        st.markdown(texts_side["sidebar_description"])

        # Measurement selector
        st.session_state.target_col = st.selectbox(
            texts_side["sidebar_choose_column"],
            COL_NAMES,
            index=COL_NAMES.index(st.session_state.target_col)
        )

        # Quick-select buttons
        col1, col2 = st.columns(2)
        if col1.button(texts_side["sidebar_first_day"]):
            st.session_state.date_from = first_date
        if col2.button(texts_side["sidebar_today"]):
            st.session_state.date_from = last_date
            st.session_state.date_to = last_date

        # Date range pickers
        st.session_state.date_from = st.date_input(
            texts_side["sidebar_start_date"],
            min_value=first_date,
            max_value=last_date,
            value=st.session_state.date_from
        )
        st.session_state.date_to = st.date_input(
            texts_side["sidebar_end_date"],
            min_value=first_date,
            max_value=last_date,
            value=st.session_state.date_to
        )

        # Aggregation functions
        st.session_state.agg_functions = st.multiselect(
            texts_side["sidebar_summary_stats"],
            ["Min", "Max", "Median"],
            default=st.session_state.agg_functions
        )

    # Apply filters using session state
    date_from = st.session_state.date_from
    date_to = st.session_state.date_to
    target_col = st.session_state.target_col
    agg_functions = st.session_state.agg_functions
    filtered_df = filter_data(df, date_from, date_to)

    # Chart display helper
def display_view(df, target_col, view_title, resample_freq, selected_cols, agg_functions):
    st.subheader(view_title)
    if resample_freq == "None":
        view_df = df.copy()
    else:
        view_df = apply_aggregation(df, selected_cols, target_col, resample_freq, agg_functions)
    plot_line_chart(view_df, target_col, resample_freq)

    # Render views
    display_view(
        filtered_df,
        target_col,
        f"{texts['raw_view']} {target_col}",
        "None",
        COL_NAMES,
        agg_functions
    )
    display_view(
        filtered_df,
        target_col,
        f"{texts['hourly_view']} {target_col}",
        "Hour",
        COL_NAMES,
        agg_functions
    )
    display_view(
        filtered_df,
        target_col,
        f"{texts['daily_view']} {target_col}",
        "Day",
        COL_NAMES,
        agg_functions
    )

    # Data table
    st.subheader(texts["data_table"])
    selected_table_cols = st.multiselect(
        texts["columns_select"],
        options=COL_NAMES,
        default=COL_NAMES
    )
    selected_table_cols.insert(0, "Timestamp (GMT+7)")
    st.write(f"{texts['data_dimensions']} ({filtered_df.shape[0]}, {len(selected_table_cols)}).")
    st.dataframe(filtered_df[selected_table_cols], use_container_width=True)

    # Clear cache
    st.button(
        texts["clear_cache"],
        help=texts.get("clear_cache_help", "Clears cached data for fresh fetch."),
        on_click=st.cache_data.clear
    )

# About page
else:
    st.title("About")
    st.markdown("""
**BASWAP** is a buoy-based water-quality monitoring dashboard for Vinh Long, Vietnam...
"""
)
