import streamlit as st
from datetime import datetime

st.set_page_config(page_title="BASWAP-APP", page_icon="💧", layout="wide")

from data import combined_data_retrieve, thingspeak_retrieve
from sidebar import sidebar_inputs
from aggregation import filter_data, apply_aggregation
from plotting import plot_line_chart, display_statistics
from config import COL_NAMES, APP_TEXTS

def update_language():
    st.session_state.language = "vi" if st.session_state.language == "en" else "en"

if "language" not in st.session_state:
    st.session_state.language = "vi"
lang = st.session_state.language
texts = APP_TEXTS[lang]

st.markdown(
    """
    <style>
        .lang-toggle {
            position: fixed;
            top: 10px;
            right: 10px;
            z-index: 100;
        }
    </style>
    """, unsafe_allow_html=True
)

st.markdown('<div class="lang-toggle">', unsafe_allow_html=True)
st.button(label=texts["toggle_button"], 
          on_click=update_language, 
          help=texts["toggle_tooltip"])
st.markdown('</div>', unsafe_allow_html=True)

st.title(texts["app_title"])
st.markdown(texts["description"])

df = combined_data_retrieve()
df = thingspeak_retrieve(df)
col_names = COL_NAMES
first_date = datetime(2025, 1, 17).date() 
last_date = df['Timestamp (GMT+7)'].max().date()

date_from, date_to, target_col, agg_functions = sidebar_inputs(df, lang, first_date, last_date)
filtered_df = filter_data(df, date_from, date_to)

display_statistics(filtered_df, target_col)

def display_view(df, target_col, view_title, resample_freq, selected_cols, agg_functions):
    st.subheader(view_title)
    if resample_freq == "None":
        view_df = df.copy()
    else:
        view_df = apply_aggregation(df, selected_cols, target_col, resample_freq, agg_functions)
    plot_line_chart(
    filtered_df,
    target_col,
    "None",
    date_from=st.session_state.date_from,
    date_to=st.session_state.date_to,
)


display_view(filtered_df, target_col, f"{texts['raw_view']} {target_col}",
             resample_freq="None", selected_cols=col_names, agg_functions=agg_functions)
display_view(filtered_df, target_col, f"{texts['hourly_view']} {target_col}",
             resample_freq="Hour", selected_cols=col_names, agg_functions=agg_functions)
display_view(filtered_df, target_col, f"{texts['daily_view']} {target_col}",
             resample_freq="Day", selected_cols=col_names, agg_functions=agg_functions)

st.subheader(texts["data_table"])
selected_table_cols = st.multiselect(
    texts["columns_select"],
    options=col_names,
    default=col_names
)
selected_table_cols.insert(0, "Timestamp (GMT+7)")
st.write(f"{texts['data_dimensions']} ({filtered_df.shape[0]}, {len(selected_table_cols)}).")
st.dataframe(filtered_df[selected_table_cols], use_container_width=True)

st.button(texts["clear_cache"], 
          help="This clears all cached data, ensuring the app fetches the latest available information.", 
          on_click=st.cache_data.clear)
