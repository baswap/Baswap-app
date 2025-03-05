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
    # drive_handler = DriveManager(st.secrets["SERVICE_ACCOUNT"])
    drive_handler = DriveManager("ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsCiAgInByb2plY3RfaWQiOiAiYmFzd2FwIiwKICAicHJpdmF0ZV9rZXlfaWQiOiAiMThhMjVlNDRiNDIxMjQxMmYwMDQ0YzYyZTliNGY4ZWIzMmM5ZDdhNCIsCiAgInByaXZhdGVfa2V5IjogIi0tLS0tQkVHSU4gUFJJVkFURSBLRVktLS0tLVxuTUlJRXZnSUJBREFOQmdrcWhraUc5dzBCQVFFRkFBU0NCS2d3Z2dTa0FnRUFBb0lCQVFDWklnM3VwWHdoUWdRM1xuWFpzVnQzRCtXNHpYdFV3U1J1ejZVWFhlQUZIcDR5Wm8vbkpYRE5sRzdPaDdIWW1oSHlGeHlUc2N3b09hSVNQR1xuOER1R2w1R3Ewd0ZQcDJ6V3pTNXlYb3FMdEp3Q2QvU0xTbjc2cDJBRlZtZUg5cXJDcVkrUXhIYnlWMnlPTml0RFxuTEVqeVlPNEFCQ20rdU53UXZrTi9Sc1RDaHlOWEhlYUlPSUp1MEIrbHd4ejdhVGxWWkhOalMzT3BGaFgycE80Vlxub3VxMEh6eUdzQTZYQ3FVM3ZoOHlJeU1CbEd3THpSRUVIeUluMytpbHZkaS94OGYvSEZnODlHQll6VDlWQjNYWFxueU1UTksySU5IV2RxbW54WENSdUNXSEIxRmxObVd5STAyVElCb0Q3cXplYjBIb1lKTldYSWJzNVY0N2tKYmxOaFxuTkh6dU9sTFBBZ01CQUFFQ2dnRUFDQ0dleThWTnloWlBVd0ZOY3VIQ3hqN21RNjRFMUJPZ0VjcXhqNUJFeVQ2ZVxuazRTdlhaLzVDYU1hMVM3RVdDSG5ETHU2djlRMFdNTFp1MzZXS3BkeHpMaFhvWHNxZEYyQTBlSGpTWGZWc092ZFxudUdmRVJsc001anVvVTdmdGFWakhudEJQNEo1enpUbGpJclgvU1orTUE4UTAwMFBOcTdYdXI1dDZaem4xem5KYVxuNjY3eFhHMzQvV1dTQTB5THZ1K1RsWUZ0WFRpNmhLUlNQVnNSMVhwVk1BdWdEdzArdzVYUmQxY3lvUFJsY1dReFxuSDRrVDFPem9UT2htU1lCWHFrd2tVd3l5c291NldRY3ZEcUdaTldaeDY0WUthRUsremlyU3p2UUhweDlidkxiOFxuQW91NUkzbXlXR3JiNkd2V09hVXdHUGxFaUpWbmdhZ1lVUFNFbWVydGdRS0JnUURXUUROeTlDTFlRZDhsSTNSRFxua1RuejdPSldoK0lWN3IwQUQyK2ZGeXlldlZLNmExbXdIVlFnUkpoNkNCcHh6c2ZxU0hQcTZodkxuem1jcWZYb1xuZ2NEcTIrTDBMOTJTdkpyd2FyQTRFVnJKRUVxZ25tOHlSL2RGdk1tcGMzSkFOWDJDMjVJM2NGR1oyNXBCMEVpeFxucm82M1kyQ3hEcEhINHV3RTJiRm1wMTJUSndLQmdRQzIrUVhkeS9DTzhLWTM3VC9GUUs5UW1NT0lWazhYTFJFMVxuSEN4SysvcW95eEgrRFVtS2hjWUZCWjhjNWlDa2VyRm1CSHRNa3d1RzBxMHg4TmhDd01GWEUwOWhuMWQ2ejZGNlxuL21pWktucTV6SkdheU5qM21kWlMvaVBGbVBXcXVjbVBXTFZZeVpoZVNINFJMd2toQzRwT0E5bnJ0VHBsSjdjZ1xuakhQM00zbnNHUUtCZ1FETU9XcFJXeEdUM2taY1drMUswclhSSTY0a0dXYVN6WHp1LzhmQWVCQ2FSNUVDRGEzeVxuU0NLV2w0eFlWajBPMnJLSlNnTGttNzllK3ltcGdnRGJYa09NRzRsY2hmdkpFV3NIWEVzWlJzR3BBcFNBUWtWd1xuUWxVYjduYXp4VTNVa3FoUEFnbUFPdG90dEx4M201aVBkZnFvS0Z4VXFiU2dPbGdMejQ1Z2NZeXE1UUtCZ0ZESFxuNUtVbGt0RW93ZG5UTHVKaFNvVmt6SDcyeS9oSmQxMWhVTlRTSnJvNjNYaXlXUk9GT0FXams3bm9oK1RXSGxnU1xuQm5XcVBkNktTTmpSb2tqbVhQV2FtdU5ZdkFDR2hwNk1qNVYvd2FzaCsrN0FXYm9HK3k2czhSSWVFK2dLR2tqbFxuT3pzMTFjVmFiLzRhTEFlZzFyRFcxbkZRRTdYeE1OSjM4QUxsZ1NDUkFvR0JBTks2SnJFb0JhVzgrdCtnY3hQOVxuUXQvS0FFWW1xKy81d1YzOGJGbGhvSDhCS0swTURwVTZUUDc2VnR6aUVpcDFxSjY3VFg2bi9idVZ6aWJJai85SVxuZ1hJRFNlRDVWWHhHdkQ3cFArUm9kOTZ2cWNNREgycUF4aEs1WDk4S0FCRlZnR2tSQ2pxaXBhdStrOVpyOU1OL1xueHZieUU1Q3JqY1I5aEtMQndTSjJ3cDlJXG4tLS0tLUVORCBQUklWQVRFIEtFWS0tLS0tXG4iLAogICJjbGllbnRfZW1haWwiOiAiYmFzd2FwLWRyaXZlQGJhc3dhcC5pYW0uZ3NlcnZpY2VhY2NvdW50LmNvbSIsCiAgImNsaWVudF9pZCI6ICIxMTMzOTQ5MjM5MjM1ODY4Mjg3ODQiLAogICJhdXRoX3VyaSI6ICJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20vby9vYXV0aDIvYXV0aCIsCiAgInRva2VuX3VyaSI6ICJodHRwczovL29hdXRoMi5nb29nbGVhcGlzLmNvbS90b2tlbiIsCiAgImF1dGhfcHJvdmlkZXJfeDUwOV9jZXJ0X3VybCI6ICJodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9vYXV0aDIvdjEvY2VydHMiLAogICJjbGllbnRfeDUwOV9jZXJ0X3VybCI6ICJodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9yb2JvdC92MS9tZXRhZGF0YS94NTA5L2Jhc3dhcC1kcml2ZSU0MGJhc3dhcC5pYW0uZ3NlcnZpY2VhY2NvdW50LmNvbSIsCiAgInVuaXZlcnNlX2RvbWFpbiI6ICJnb29nbGVhcGlzLmNvbSIKfQo=")

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
    selected_cols = st.sidebar.multiselect("Columns", col_names, [name for name in col_names if name not in ["DO Value", "DO Temperature"]])
    selected_cols.insert(0, "Timestamp (GMT+7)")

    min_date = df["Timestamp (GMT+7)"].min().date()
    max_date = df["Timestamp (GMT+7)"].max().date()
    date_from = st.sidebar.date_input("Date from:", min_value=min_date, max_value=max_date, value=max_date)
    date_to = st.sidebar.date_input("Date to:", min_value=min_date, max_value=max_date, value=max_date)# Filtering data
    
    target_col = st.sidebar.selectbox("Choose a column:", [col for col in selected_cols if col != 'Timestamp (GMT+7)'], index = 2)

    return selected_cols, date_from, date_to, target_col

# Data Filtering
def filter_data(df, date_from, date_to, selected_cols):
    filtered_df = df[(df["Timestamp (GMT+7)"].dt.date >= date_from) & 
                     (df["Timestamp (GMT+7)"].dt.date <= date_to)]
    return filtered_df[selected_cols]

def plot_line_chart(df, col):
    # Convert to string format for detailed hover
    df["Timestamp_str"] = df["Timestamp (GMT+7)"].dt.strftime(r"%Y-%m-%d %H:%M:%S") 
    # Altair Chart
    chart = (
        alt.Chart(df)
        .mark_line(point=True)  # Add points to the line
        .encode(
            x=alt.X("Timestamp (GMT+7):T", title="Timestamp"),
            y=alt.Y(f"{col}:Q", title="Value"),
            tooltip=["Timestamp_str:N", f"{col}:Q"],  # Hover tooltip
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
        print(df.iloc[-1, 0])
        
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
