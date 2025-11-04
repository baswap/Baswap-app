import os
import sys
import json
from datetime import datetime, timezone, timedelta

import pandas as pd
import requests
import streamlit as st

# from config import GMT7, UTC, THINGSPEAK_URL, COMBINED_ID, SECRET_ACC
from config import GMT7, UTC, THINGSPEAK_URL

# utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils")))
from utils import DriveManager  # noqa: E402  (import after sys.path tweak)


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
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

    if s.dt.tz is None:                     # tz-naive → localise
        return s.dt.tz_localize("Asia/Bangkok")
    return s.dt.tz_convert("Asia/Bangkok")  # already aware → convert if needed


# ──────────────────────────────────────────────────────────────
# Cached combined-file loader
# ──────────────────────────────────────────────────────────────
@st.cache_data()
def combined_data_retrieve() -> pd.DataFrame:
    # drive_handler = DriveManager(SECRET_ACC)
    # df = drive_handler.read_csv_file(COMBINED_ID)

    # # one clean, canonical conversion – no UTC round-trip
    # df["ds"] = _to_bangkok(df["ds"])
    df = pd.read_csv("dataset/merged_all_data.csv")
    df["ds"] = (
        pd.to_datetime(df["ds"], errors="coerce")                # parse (yields tz-aware if +07 present)
        .dt.tz_convert("Asia/Bangkok")                         # ensure local time
        .dt.tz_localize(None)                                  # drop timezone -> naive datetime64[ns]
    )
    # df["ds"] = _to_bangkok(df["ds"])
    return df


# ──────────────────────────────────────────────────────────────
# ThingSpeak utilities
# ──────────────────────────────────────────────────────────────
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
    # last_ts: datetime = df[df["station"] == "VGU"]["ds"].iloc[-1]
    # define Bangkok timezone (UTC+7)
    bangkok_tz = timezone(timedelta(hours=7))

    # create timezone-aware datetime
    last_ts = datetime(2025, 11, 3, tzinfo=bangkok_tz)

    for feed in feeds:
        created = feed.get("created_at")
        if not created:
            continue

        gmt7_time = convert_utc_to_GMT7(
            datetime.strptime(created, r"%Y-%m-%dT%H:%M:%SZ")
        )

        new_row = {
            "ds": gmt7_time,
            "station": "VGU",
            "EC Value (g/l)": float(feed.get("field3", 0)) / 1000,
            "EC Value (us/cm)": float(feed.get("field3", 0))
        }

        new_df = pd.DataFrame([new_row])

        new_df["ds"] = _to_bangkok(new_df["ds"])

        if gmt7_time > last_ts:
            df = pd.concat([df, new_df], ignore_index=True)
        df["ds"] = _to_bangkok(df["ds"])

    # keep timestamps tidy & sorted
    # df["ds"] = _to_bangkok(df["ds"])
    # df.sort_values(by=["station", "ds"], inplace=True, ignore_index=True)
    return df


def thingspeak_retrieve(df: pd.DataFrame) -> pd.DataFrame:
    """Top-up *df* with fresh ThingSpeak rows."""
    # today = datetime.now(GMT7).date()
    # date_diff = max((today - df["ds"].iloc[-1].date()).days, 0)

    # 150 rows per day looks right for your sampling rate
    # results = max(150 * date_diff, 1)
    results = max(150, 1)
    feeds = fetch_thingspeak_data(results)
    return append_new_data(df, feeds)
