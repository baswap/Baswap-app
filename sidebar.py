import streamlit as st
from datetime import datetime
from config import GMT7, COL_NAMES, SIDE_TEXTS

def sidebar_inputs(df, lang):
    texts = SIDE_TEXTS[lang]
    col_names = COL_NAMES

    # Sidebar header and description
    st.sidebar.markdown(texts["sidebar_header"])
    st.sidebar.markdown(texts["sidebar_description"])

    # Column selection for plotting
    target_col = st.sidebar.selectbox(texts["sidebar_choose_column"], col_names, index=1)

    min_date = datetime(2025, 1, 17).date()  # Fixed first date
    max_date = datetime.now(GMT7).date()

    if "date_from" not in st.session_state:
        st.session_state.date_from = max_date
    if "date_to" not in st.session_state:
        st.session_state.date_to = max_date

    col1, col2 = st.sidebar.columns(2)
    if col1.button(texts["sidebar_first_day"]):
        st.session_state.date_from = min_date  
    if col2.button(texts["sidebar_today"]):
        st.session_state.date_from, st.session_state.date_to = max_date, max_date

    date_from = st.sidebar.date_input(
        texts["sidebar_start_date"], 
        min_value=min_date, 
        max_value=max_date, 
        value=st.session_state.date_from
    )
    date_to = st.sidebar.date_input(
        texts["sidebar_end_date"], 
        min_value=min_date, 
        max_value=max_date, 
        value=st.session_state.date_to
    )

    agg_functions = st.sidebar.multiselect(
        texts["sidebar_summary_stats"],
        ["Min", "Max", "Median"],
        ["Min", "Max", "Median"]
    )

    return date_from, date_to, target_col, agg_functions
