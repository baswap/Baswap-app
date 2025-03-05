import streamlit as st
import logging
import requests
import json
import pytz
import pandas as pd
from datetime import datetime, timedelta

from drive_handler import DriveManager

# Constants
GMT7 = pytz.timezone("Asia/Bangkok")
UTC = pytz.utc
THINGSPEAK_URL = "https://api.thingspeak.com/channels/2652379/feeds.json"
COMBINED_FILENAME = "combined_data.csv"
COMBINED_ID = "1-2egCgGVsVMPcRrqjvcF0LCSMk1Q1KO0"

# Timezone Conversion Function
def convert_to_GMT7(timestamp):
    """Convert date to GMT+7 timezone-aware datetime."""
    if isinstance(timestamp, datetime):
        return GMT7.localize(timestamp) if timestamp.tzinfo is None else timestamp.astimezone(GMT7)
    return GMT7.localize(datetime.combine(timestamp, datetime.min.time()))

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
            utc_time = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
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
    today = convert_to_GMT7(datetime.now()).date()
    date_diff = (today - df.iloc[-1, 0].date()).days
    results = 1440 * date_diff

    feeds = fetch_thingspeak_data(results)
    return append_new_data(df, feeds)

# Sidebar Input Features
def sidebar_inputs(df):
    col_names = [col for col in df.columns if col != "Timestamp (GMT+7)"]
    selected_cols = st.sidebar.multiselect("Columns", col_names, col_names)
    selected_cols.insert(0, "Timestamp (GMT+7)")

    min_date = df["Timestamp (GMT+7)"].min().date()
    max_date = df["Timestamp (GMT+7)"].max().date()
    date_from = convert_to_GMT7(st.sidebar.date_input("Date from:", min_value=min_date, max_value=max_date, value=max_date)).date()
    date_to = convert_to_GMT7(st.sidebar.date_input("Date to:", min_value=min_date, max_value=max_date, value=max_date)).date()

    return selected_cols, date_from, date_to

# Data Filtering
def filter_data(df, date_from, date_to, selected_cols):
    filtered_df = df[(df["Timestamp (GMT+7)"].dt.date >= date_from) & 
                     (df["Timestamp (GMT+7)"].dt.date <= date_to)]
    return filtered_df[selected_cols]

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
        
        selected_cols, date_from, date_to = sidebar_inputs(df)
        filtered_df = filter_data(df, date_from, date_to, selected_cols)

        st.subheader("Detailed Dataset")
        st.write(f"Data Dimension: {filtered_df.shape[0]} rows and {filtered_df.shape[1]} columns.")
        st.dataframe(filtered_df)

if __name__ == "__main__":
    app()
