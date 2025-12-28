import os
import sys
import json
from datetime import datetime, timezone, timedelta

import pandas as pd
import requests
import streamlit as st

from config import GMT7, UTC, THINGSPEAK_URL

# local utils live one level up (keeps imports working when run from /data)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils")))
from utils import DriveManager  


# ------------------------------
# Timezone helpers
# ------------------------------
def convert_utc_to_GMT7(ts: datetime) -> datetime:
    """Take a UTC *or* naive timestamp and return it as tz-aware Asia/Bangkok."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(GMT7)


def _to_bangkok(series: pd.Series) -> pd.Series:
    """
    Ensure a Series of datetimes is tz-aware Asia/Bangkok.
    Works whether original values are strings, tz-naive, or already tz-aware.
    """
    s = pd.to_datetime(series, errors="coerce")

    # tz-naive -> localize, tz-aware -> convert
    if s.dt.tz is None:                     # tz-naive → localise
        return s.dt.tz_localize("Asia/Bangkok")
    return s.dt.tz_convert("Asia/Bangkok")  


# ------------------------------
# Load merged dataset (cached)
# ------------------------------
@st.cache_data()
def combined_data_retrieve() -> pd.DataFrame:
    # Current source: local merged CSV (Drive loading is disabled for now)
    df = pd.read_csv("dataset/merged_all_data.csv")

    # Parse ds, convert to Bangkok time, then drop tz info for easier filtering/sorting
    df["ds"] = (
        pd.to_datetime(df["ds"], errors="coerce")                # parse (yields tz-aware if +07 present)
        .dt.tz_convert("Asia/Bangkok")                         # ensure local time
        .dt.tz_localize(None)                                  # drop timezone -> naive datetime64[ns]
    )
    return df


# ------------------------------
# ThingSpeak fetch + merge
# ------------------------------
def fetch_thingspeak_data(results: int) -> list[dict]:
    """Pull the latest <results> rows from ThingSpeak."""
    url = f"{THINGSPEAK_URL}?results={results}"
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        return json.loads(r.text).get("feeds", [])
    st.error("Failed to fetch data from ThingSpeak API")
    return []

@st.cache_data()
def append_new_data(df: pd.DataFrame, feeds: list[dict]) -> pd.DataFrame:
    """Append any newer rows from ThingSpeak to *df*."""
    # last_ts is hardcoded!!!
    bangkok_tz = timezone(timedelta(hours=7))
    last_ts = datetime(2025, 11, 3, tzinfo=bangkok_tz)

    for feed in feeds:
        created = feed.get("created_at")
        if not created:
            continue

        # ThingSpeak timestamps are UTC "Z"
        gmt7_time = convert_utc_to_GMT7(
            datetime.strptime(created, r"%Y-%m-%dT%H:%M:%SZ")
        )

        # Map ThingSpeak fields into our schema
        new_row = {
            "ds": gmt7_time,
            "station": "VGU",
            "EC Value (g/l)": float(feed.get("field3", 0)) / 1000,
            "EC Value (us/cm)": float(feed.get("field3", 0))
        }

        new_df = pd.DataFrame([new_row])
        new_df["ds"] = _to_bangkok(new_df["ds"])

        # Only append if it's newer than our last seen timestamp
        if gmt7_time > last_ts:
            df = pd.concat([df, new_df], ignore_index=True)

        # Keep ds consistently tz-aware across the whole df
        df["ds"] = _to_bangkok(df["ds"])

    return df


def thingspeak_retrieve(df: pd.DataFrame) -> pd.DataFrame:
    """Top-up *df* with fresh ThingSpeak rows."""
    # Fixed pull size for now (150 ~= about 1 day at current sampling)
    results = max(150, 1)
    feeds = fetch_thingspeak_data(results)
    return append_new_data(df, feeds)
