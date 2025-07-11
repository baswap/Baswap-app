# ── app.py ─────────────────────────────────────────────────────────────────────
import streamlit as st
import folium
from streamlit_folium import st_folium
from datetime import datetime

from config import SECRET_ACC, COMBINED_ID, APP_TEXTS, SIDE_TEXTS, COL_NAMES
from utils.drive_handler import DriveManager
from data import combined_data_retrieve, thingspeak_retrieve
from aggregation import filter_data, apply_aggregation
from plotting import plot_line_chart, display_statistics

# -----------------------------------------------------------------------------#
# 1. Page / Session ­Setup                                                     #
# -----------------------------------------------------------------------------#
st.set_page_config(page_title="BASWAP", page_icon="💧", layout="wide")

qs   = st.query_params
page = qs.get("page", "Overview")
lang = qs.get("lang",  "vi")
if page not in ("Overview", "About"): page = "Overview"
if lang not in ("en", "vi"):          lang = "vi"

toggle_lang  = "en" if lang == "vi" else "vi"
toggle_label = APP_TEXTS[lang]["toggle_button"]
texts        = APP_TEXTS[lang]
side_texts   = SIDE_TEXTS[lang]

# Ensure key session-state variables exist
for key in ("show_settings", "target_col", "date_from", "date_to", "agg_functions"):
    if key not in st.session_state:
        st.session_state[key] = False if key == "show_settings" else None

# -----------------------------------------------------------------------------#
# 2. Top Header Bar (unchanged)                                                #
# -----------------------------------------------------------------------------#
st.markdown(
    """
    <style>
        header {visibility:hidden;}
        .custom-header{
            position:fixed;top:0;left:0;right:0;height:4.5rem;
            display:flex;align-items:center;gap:2rem;padding:0 1rem;
            background:#fff;box-shadow:0 1px 2px rgba(0,0,0,0.1);
            z-index:1000;
        }
        .custom-header .logo{font-size:1.65rem;font-weight:600;color:#000;}
        .custom-header .nav{display:flex;gap:1rem;}
        .custom-header .nav a{
            text-decoration:none;color:#262730;font-size:0.9rem;
            padding-bottom:0.25rem;border-bottom:2px solid transparent;
        }
        .custom-header .nav a.active{color:#09c;border-bottom-color:#09c;}
        body>.main{margin-top:4.5rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="custom-header">
      <div class="logo">BASWAP</div>
      <div class="nav">
        <a href="?page=Overview&lang={lang}" class="{ 'active' if page=='Overview' else '' }">Overview</a>
        <a href="?page=About&lang={lang}"     class="{ 'active' if page=='About'    else '' }">About</a>
      </div>
      <div class="nav" style="margin-left:auto;">
        <a href="?page={page}&lang={toggle_lang}">{toggle_label}</a>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------#
# 3. Utility – Centralised Settings Panel                                      #
# -----------------------------------------------------------------------------#
def settings_panel(df, first_date, last_date):
    """Render former-sidebar controls inside a regular container."""
    with st.container():
        st.markdown(side_texts["sidebar_header"])
        st.markdown(side_texts["sidebar_description"])

        # --- Column (measurement) selector -----------------------------------#
        if st.session_state.target_col is None:
            st.session_state.target_col = COL_NAMES[0]
        target_col = st.selectbox(
            side_texts["sidebar_choose_column"],
            COL_NAMES,
            index=COL_NAMES.index(st.session_state.target_col),
        )
        st.session_state.target_col = target_col

        # --- Quick-range buttons --------------------------------------------#
        c1, c2 = st.columns(2)
        if c1.button(side_texts["sidebar_first_day"]):
            st.session_state.date_from = first_date
        if c2.button(side_texts["sidebar_today"]):
            st.session_state.date_from = st.session_state.date_to = last_date

        # --- Date inputs -----------------------------------------------------#
        if st.session_state.date_from is None: st.session_state.date_from = last_date
        if st.session_state.date_to   is None: st.session_state.date_to   = last_date

        date_from = st.date_input(
            side_texts["sidebar_start_date"],
            min_value=first_date, max_value=last_date,
            value=st.session_state.date_from,
        )
        date_to   = st.date_input(
            side_texts["sidebar_end_date"],
            min_value=first_date, max_value=last_date,
            value=st.session_state.date_to,
        )
        st.session_state.date_from, st.session_state.date_to = date_from, date_to

        # --- Aggregation multiselect ----------------------------------------#
        if st.session_state.agg_functions is None:
            st.session_state.agg_functions = ["Min", "Max", "Median"]
        agg_functions = st.multiselect(
            side_texts["sidebar_summary_stats"],
            ["Min", "Max", "Median"],
            default=st.session_state.agg_functions,
        )
        st.session_state.agg_functions = agg_functions

# -----------------------------------------------------------------------------#
# 4. ROUTING: “Overview” page                                                  #
# -----------------------------------------------------------------------------#
if page == "Overview":

    # 4-A. Map + Descriptive Header
    st_folium(folium.Map(location=[10.231140, 105.980999], zoom_start=8),
               width="100%", height=400)

    st.title(texts["app_title"])
    st.markdown(texts["description"])

    # 4-B. Data fetch / prep
    df         = thingspeak_retrieve(combined_data_retrieve())
    first_date = datetime(2025, 1, 17).date()
    last_date  = df["Timestamp (GMT+7)"].max().date()

    # 4-C. Overall statistics (uses whatever is currently stored)
    #      If none yet => fall back to defaults
    target_col = st.session_state.target_col or COL_NAMES[0]
    date_from  = st.session_state.date_from or last_date
    date_to    = st.session_state.date_to or last_date

    filtered_df = filter_data(df, date_from, date_to)
    display_statistics(filtered_df, target_col)

    # 4-D. “Settings” toggle button -----------------------------------------#
    if st.button("⚙️  Settings"):
        st.session_state.show_settings = not st.session_state.show_settings

    if st.session_state.show_settings:
        with st.expander("Graph Settings", expanded=True):
            settings_panel(df, first_date, last_date)
        # Re-compute with possibly updated choices
        target_col  = st.session_state.target_col
        date_from   = st.session_state.date_from
        date_to     = st.session_state.date_to
        agg_functions = st.session_state.agg_functions
        filtered_df = filter_data(df, date_from, date_to)

    # 4-E. Charts (Raw / Hourly / Daily) ------------------------------------#
    def show_view(df_view, title, freq):
        st.subheader(title)
        view_df = (
            df_view if freq == "None"
            else apply_aggregation(df_view, COL_NAMES, target_col, freq, agg_functions)
        )
        plot_line_chart(view_df, target_col, freq)

    show_view(filtered_df, f"{texts['raw_view']} {target_col}",   "None")
    show_view(filtered_df, f"{texts['hourly_view']} {target_col}", "Hour")
    show_view(filtered_df, f"{texts['daily_view']} {target_col}",  "Day")

    # 4-F. Data table --------------------------------------------------------#
    st.subheader(texts["data_table"])
    selected_cols = st.multiselect(
        texts["columns_select"], options=COL_NAMES, default=COL_NAMES
    )
    selected_cols.insert(0, "Timestamp (GMT+7)")
    st.write(f"{texts['data_dimensions']} ({filtered_df.shape[0]}, {len(selected_cols)}).")
    st.dataframe(filtered_df[selected_cols], use_container_width=True)

    # 4-G. Clear-cache button
    st.button(texts["clear_cache"],
              help="Clears cached data for fresh fetch.",
              on_click=st.cache_data.clear)

# -----------------------------------------------------------------------------#
# 5. ROUTING: “About” page                                                     #
# -----------------------------------------------------------------------------#
else:
    st.title("About")
    st.markdown("""
**BASWAP** is a buoy-based water-quality monitoring dashboard for Vinh Long, Vietnam…
""")
# -----------------------------------------------------------------------------#
