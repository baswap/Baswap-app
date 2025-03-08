import streamlit as st
import logging
import requests
import json
import pytz
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

from drive_handler import DriveManager

# Constants
GMT7 = pytz.timezone("Asia/Bangkok")
UTC = pytz.utc
THINGSPEAK_URL = "https://api.thingspeak.com/channels/2652379/feeds.json"
COMBINED_FILENAME = "combined_data.csv"
COMBINED_ID = "1-2egCgGVsVMPcRrqjvcF0LCSMk1Q1KO0"

def convert_utc_to_GMT7(timestamp):
    """Convert UTC timestamp to GMT+7."""
    return timestamp.replace(tzinfo=UTC).astimezone(GMT7)

# Data Retrieval from Google Drive
@st.cache_data(ttl=86400)
def combined_data_retrieve():
    drive_handler = DriveManager(st.secrets["SERVICE_ACCOUNT"])
    df = drive_handler.read_csv_file(COMBINED_ID)
    df["Timestamp (GMT+7)"] = pd.to_datetime(df["Timestamp (GMT+7)"], utc=True).dt.tz_convert("Asia/Bangkok")
    return df

# Thingspeak API Data Retrieval
def fetch_thingspeak_data(results):
    url = f"{THINGSPEAK_URL}?results={results}"
    response = requests.get(url)
    if response.status_code == 200:
        return json.loads(response.text)["feeds"]
    else:
        st.error("Failed to fetch data from Thingspeak API")
        return []

def append_new_data(df, feeds):
    """Append new data from Thingspeak API to DataFrame."""
    last_timestamp = df.iloc[-1, 0]

    for feed in feeds:
        timestamp = feed.get('created_at', '')
        if timestamp:
            utc_time = datetime.strptime(timestamp, r"%Y-%m-%dT%H:%M:%SZ")
            gmt7_time = convert_utc_to_GMT7(utc_time)

            if gmt7_time > last_timestamp:
                df.loc[len(df)] = [
                    gmt7_time,
                    float(feed.get("field1", 0)),
                    float(feed.get("field2", 0)),
                    int(feed.get("field3", 0)),
                    float(feed.get("field4", 0)),
                    float(feed.get("field5", 0))
                ]

    df["Timestamp (GMT+7)"] = pd.to_datetime(df["Timestamp (GMT+7)"], utc=True).dt.tz_convert("Asia/Bangkok")
    return df

def thingspeak_retrieve(df):
    today = datetime.now(GMT7).date()
    date_diff = (today - df.iloc[-1, 0].date()).days
    results = 150 * date_diff

    feeds = fetch_thingspeak_data(results)
    return append_new_data(df, feeds)

# Sidebar Input Features
def sidebar_inputs(df):
    col_names = [col for col in df.columns if col != "Timestamp (GMT+7)"]
    selected_cols = st.sidebar.multiselect("Columns to display in detail", col_names, [name for name in col_names if name not in ["DO Value", "DO Temperature"]])
    selected_cols.insert(0, "Timestamp (GMT+7)")

    target_col = st.sidebar.selectbox("Choose a column to analyze:", [col for col in selected_cols if col != 'Timestamp (GMT+7)'], index = 0)

    min_date = df["Timestamp (GMT+7)"].min().date()
    max_date = df["Timestamp (GMT+7)"].max().date()
    date_from = st.sidebar.date_input("Date from:", min_value=min_date, max_value=max_date, value=max_date)
    date_to = st.sidebar.date_input("Date to:", min_value=min_date, max_value=max_date, value=max_date)# Filtering data

    return selected_cols, date_from, date_to, target_col

# Data Filtering
def filter_data(df, date_from, date_to, selected_cols):
    filtered_df = df[(df["Timestamp (GMT+7)"].dt.date >= date_from) & 
                     (df["Timestamp (GMT+7)"].dt.date <= date_to)]
    return filtered_df[selected_cols]

def plot_line_chart(df, col):
    # Ensure column exists
    if col not in df.columns:
        st.error(f"Column '{col}' not found in DataFrame.")
        return

    # Create a copy of the DataFrame to avoid modifying the original
    df_filtered = df.copy()

    # Convert Timestamp to string format for detailed hover
    df_filtered["Timestamp (UTC+7)"] = df_filtered["Timestamp (GMT+7)"].dt.strftime(r"%Y-%m-%d %H:%M:%S")

    # Reorder columns: Move Timestamp_str to the beginning and exclude Timestamp (GMT+7)
    df_filtered = df_filtered[["Timestamp (UTC+7)"] + [c for c in df_filtered.columns if c != "Timestamp (UTC+7)"]]

    # Altair Chart
    chart = (
        alt.Chart(df_filtered)
        .mark_line(point=True)  # Add points to the line
        .encode(
            x=alt.X("Timestamp (GMT+7):T", title="Timestamp"),
            y=alt.Y(f"{col}:Q", title="Value"),
            tooltip=[alt.Tooltip("Timestamp (UTC+7):N", title="Time"),  # Explicitly set as Nominal
                 alt.Tooltip(f"{col}:Q", title="Value")],
        )
        .interactive()  # Enable zooming & panning
    )

    # Display the chart in Streamlit
    st.altair_chart(chart, use_container_width=True)

# Streamlit Layout
def app():
    st.set_page_config(page_title="BASWAP-APP", page_icon="💧", layout="wide")
    st.title("BASWAP APP")

    st.markdown("""
    This app retrieves the water quality from a buoy-based monitoring system in Vinh Long, Vietnam.
    * **Data source:** [Thingspeak](https://thingspeak.mathworks.com/channels/2652379).
    """)

    placeholder = st.empty()
    with placeholder.container():
        df = combined_data_retrieve()
        df = thingspeak_retrieve(df)
        
        selected_cols, date_from, date_to, target_col = sidebar_inputs(df)
        filtered_df = filter_data(df, date_from, date_to, selected_cols)

        col = st.columns((1.5, 4.5, 2), gap='medium')

        with col[0]:
            st.markdown('#### Key numbers')

            # Compute statistics
            max_value = filtered_df[target_col].max()
            min_value = filtered_df[target_col].min()
            average_value = filtered_df[target_col].mean()
            std_dev_value = filtered_df[target_col].std()

            # Display metrics in Streamlit
            st.metric(label="Maximum Value", value=f"{max_value:.2f}")
            st.metric(label="Minimum Value", value=f"{min_value:.2f}")
            st.metric(label="Average Value", value=f"{average_value:.2f}")
            st.metric(label="Standard Deviation", value=f"{std_dev_value:.2f}")

        with col[1]:
            st.markdown('#### Graphs')

            plot_line_chart(filtered_df, target_col)

            st.markdown('###### Detailed Dataset')
            st.write(f"Data Dimension: {filtered_df.shape[0]} rows and {filtered_df.shape[1]} columns.")
            st.dataframe(filtered_df)

        with col[2]:
            st.markdown('#### Further information')
            if st.button("Clear Cache"):
                # Clear values from *all* all in-memory and on-disk data caches:
                # i.e. clear values from both square and cube
                st.cache_data.clear()

if __name__ == "__main__":
    app()
