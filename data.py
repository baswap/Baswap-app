import os
import sys
import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
from config import GMT7, UTC, THINGSPEAK_URL, COMBINED_ID, SECRET_ACC

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils")))
from utils import DriveManager

def convert_utc_to_GMT7(timestamp):
    """Convert UTC timestamp to GMT+7."""
    return timestamp.replace(tzinfo=UTC).astimezone(GMT7)

@st.cache_data(ttl=86400)
def combined_data_retrieve():
    drive_handler = DriveManager(SECRET_ACC)
    df = drive_handler.read_csv_file(COMBINED_ID)
    df["Timestamp (GMT+7)"] = pd.to_datetime(df["Timestamp (GMT+7)"], utc=True).dt.tz_convert("Asia/Bangkok")
    return df

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
                    float(feed.get("field5", 0)),
                    int(feed.get("field3", 0)) / 2000
                ]

    df["Timestamp (GMT+7)"] = pd.to_datetime(df["Timestamp (GMT+7)"], utc=True).dt.tz_convert("Asia/Bangkok")
    return df

def thingspeak_retrieve(df):
    today = datetime.now(GMT7).date()
    date_diff = (today - df.iloc[-1, 0].date()).days
    results = 150 * date_diff
    feeds = fetch_thingspeak_data(results)
    return append_new_data(df, feeds)
