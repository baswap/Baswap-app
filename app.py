import streamlit as st
import logging
import logging.handlers
import requests
import json
import csv
import os
import pytz
import pandas as pd
from datetime import date, timedelta, datetime

from drive_handler import DriveManager


def thingspeak_retrieve(df):
    # Define the timezone for GMT+7 (Asia/Bangkok)
    gmt_plus_7_tz = pytz.timezone('Asia/Bangkok')

    # Get today's date in GMT+7 (removing time part)
    today_gmt_plus_7 = datetime.now(gmt_plus_7_tz).date()
    date_dif = (today_gmt_plus_7 - df.iloc[-1, 0].date()).days

    # approximately 1440 measurements a day
    url = f"https://api.thingspeak.com/channels/2652379/feeds.json?results={1440 * date_dif}" 

    response = requests.get(url)
    data = json.loads(response.text)

    # Timezones: UTC (GMT+0) and target timezone (GMT+7)
    utc_tz = pytz.timezone('UTC')
    gmt_plus_7_tz = pytz.timezone('Asia/Bangkok')  # GMT+7

    for feed in data['feeds']:
        timestamp = feed.get('created_at', '')

        if timestamp:
            # Parse the timestamp in UTC (GMT+0)
            utc_time = datetime.strptime(timestamp, r'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=utc_tz)

            # Convert the UTC time to GMT+7
            gmt_plus_7_time = utc_time.astimezone(gmt_plus_7_tz)

            if (gmt_plus_7_time > df.iloc[-1, 0]):
                df.loc[len(df)] = [
                    gmt_plus_7_time,  # Convert timestamp
                    float(feed.get("field1", 0)),  # Convert to float
                    float(feed.get("field2", 0)),
                    int(feed.get("field3", 0)),  # Convert to int
                    float(feed.get("field4", 0)),
                    float(feed.get("field5", 0))
                ]

    df["Timestamp (GMT+7)"] = pd.to_datetime(df["Timestamp (GMT+7)"], utc=True).dt.tz_convert("Asia/Bangkok")
    return df

@st.cache_data(ttl=86400)  
def combined_data_retrieve():
    COMBINED_FILENAME = "combined_data.csv"
    COMBINED_ID = "1-2egCgGVsVMPcRrqjvcF0LCSMk1Q1KO0"

    drive_handler = DriveManager(st.secrets["SERVICE_ACCOUNT"])
    df = drive_handler.read_csv_file(COMBINED_ID)

    # Ensure proper conversion
    df["Timestamp (GMT+7)"] = pd.to_datetime(df["Timestamp (GMT+7)"], utc=True).dt.tz_convert("Asia/Bangkok")
    return df

st.title('BASWAP App')

st.markdown("""
This app retrieves the water quality from a buoy-based monitoring system in Vinh Long, Vietnam.
* **Data source:** [Thingspeak](https://thingspeak.mathworks.com/channels/2652379).
""")

# creating a single-element container.
placeholder = st.empty()

with placeholder.container():
    df = combined_data_retrieve()
    df = thingspeak_retrieve(df)

    st.sidebar.header('User Input Features')
    # Sidebar column selector
    col_names = list(df.columns)
    col_names.remove("Timestamp (GMT+7)")
    selected_cols = list(st.sidebar.multiselect('Columns', col_names, col_names))
    selected_cols.insert(0, "Timestamp (GMT+7)")

    # Sidebar date selector
    min_date = df["Timestamp (GMT+7)"].min().date()
    max_date = df["Timestamp (GMT+7)"].max().date()
    date_from = st.sidebar.date_input("Date from:", min_value=min_date, max_value=max_date, value=max_date)
    date_to = st.sidebar.date_input("Date to:", min_value=min_date, max_value=max_date, value=max_date)

    # Filtering data
    filtered_df = df[(df["Timestamp (GMT+7)"].dt.date >= date_from) & 
                            (df["Timestamp (GMT+7)"].dt.date <= date_to)]
    filtered_df = filtered_df[selected_cols]


    st.header('Display Values in Selected Columns and Time Range')
    st.write('Data Dimension: ' + str(filtered_df.shape[0]) + ' rows and ' + str(filtered_df.shape[1]) + ' columns.')
    st.dataframe(filtered_df)





