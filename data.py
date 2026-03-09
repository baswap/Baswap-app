import os
import sys
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine

import pandas as pd
import requests
import streamlit as st

from config import GMT7, UTC, THINGSPEAK_URL, DATABASE_URL

# local utils live one level up (keeps imports working when run from /data)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils")))


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
    if s.dt.tz is None:  # tz-naive → localise
        return s.dt.tz_localize("Asia/Bangkok")
    return s.dt.tz_convert("Asia/Bangkok")


# ------------------------------
# Load merged dataset (cached)
# ------------------------------
@st.cache_data(ttl=600)
def combined_data_retrieve() -> pd.DataFrame:

    df = load_data_neon()

    df = thingspeak_retrieve(df)

    df["ds"] = (
        pd.to_datetime(df["ds"], errors="coerce")
        .dt.tz_convert("Asia/Bangkok")
        .dt.tz_localize(None)
    )

    return df


# ------------------------------
# ThingSpeak fetch + merge
# ------------------------------
@st.cache_data(ttl=600)
def fetch_thingspeak_data(results: int) -> list[dict]:
    """Pull the latest <results> rows from ThingSpeak."""
    url = f"{THINGSPEAK_URL}?results={results}"
    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        return json.loads(r.text).get("feeds", [])
    st.error("Failed to fetch data from ThingSpeak API")
    return []


@st.cache_data(ttl=600)
def append_new_data(df: pd.DataFrame, feeds: list[dict]) -> pd.DataFrame:
    """Append any newer rows from ThingSpeak to df using Neon schema."""

    if df.empty:
        last_ts = None
    else:
        last_ts = pd.to_datetime(df["ds"]).max()

    if last_ts is not None and last_ts.tzinfo is None:
        last_ts = last_ts.replace(tzinfo=GMT7)

    rows = []

    for feed in feeds:
        created = feed.get("created_at")
        if not created:
            continue

        # Convert ThingSpeak UTC timestamp -> GMT+7
        gmt7_time = convert_utc_to_GMT7(
            datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ")
        )

        if last_ts is not None and gmt7_time <= last_ts:
            continue

        def to_float(x):
            try:
                return float(x)
            except (TypeError, ValueError):
                return None

        ec_us_cm = to_float(feed.get("field1"))
        temperature = to_float(feed.get("field2"))
        ec_mgl = to_float(feed.get("field3"))
        ec_gl = ec_mgl / 1000 if ec_mgl is not None else None

        rows.append(
            {
                "ds": gmt7_time,
                "station": "VinhLong",
                "ec_us_cm": ec_us_cm,
                "temperature": temperature,
                "ec_gl": ec_gl,
            }
        )

    if not rows:
        return df

    new_df = pd.DataFrame(rows)

    # Ensure timezone consistency
    new_df["ds"] = _to_bangkok(new_df["ds"])

    df = pd.concat([df, new_df], ignore_index=True)

    return df


@st.cache_data(ttl=600)
def thingspeak_retrieve(df: pd.DataFrame) -> pd.DataFrame:
    """Top-up *df* with fresh ThingSpeak rows."""
    # Fixed pull size for now (10 ~= about 1 day at current sampling)
    results = 10
    feeds = fetch_thingspeak_data(results)
    return append_new_data(df, feeds)


# ------------------------------
# Neon database
# ------------------------------
@st.cache_data(ttl=3 * 3600 + 300)  # cache for 3 hours (data updates every ~3h)
def load_data_neon() -> pd.DataFrame:
    """Load recent data for a station from Neon database."""
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        query = f"""
            SELECT ds, station, ec_us_cm, temperature, ec_gl
            FROM sensor_data
            ORDER BY ds DESC
        """
        df = pd.read_sql(query, conn)
    df["ds"] = _to_bangkok(df["ds"])
    return df
