import streamlit as st
from datetime import datetime
from config import GMT7

def sidebar_inputs(df):
    col_names = [col for col in df.columns if col != "Timestamp (GMT+7)"]
    # Exclude certain columns by default if necessary
    selected_cols = st.sidebar.multiselect("Columns to display in detail", col_names, [name for name in col_names if name not in ["DO Value", "DO Temperature"]])
    selected_cols.insert(0, "Timestamp (GMT+7)")

    target_col = st.sidebar.selectbox("Choose a column to analyze:", [col for col in selected_cols if col != 'Timestamp (GMT+7)'], index=3)

    min_date = datetime(2025, 1, 17).date()  # Fixed first date
    max_date = datetime.now(GMT7).date()

    if "date_from" not in st.session_state:
        st.session_state.date_from = max_date
    if "date_to" not in st.session_state:
        st.session_state.date_to = max_date

    col1, col2 = st.sidebar.columns(2)
    if col1.button("First Day"):
        st.session_state.date_from = min_date  
    if col2.button("Today"):
        st.session_state.date_from, st.session_state.date_to = max_date, max_date

    date_from = st.sidebar.date_input("Date from:", min_value=min_date, max_value=max_date, value=st.session_state.date_from)
    date_to = st.sidebar.date_input("Date to:", min_value=min_date, max_value=max_date, value=st.session_state.date_to)

    agg_functions = st.sidebar.multiselect("Aggregation Functions:", ["Min", "Max", "Median"], ["Min", "Max", "Median"])

    return selected_cols, date_from, date_to, target_col, agg_functions
