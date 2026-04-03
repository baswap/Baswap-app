import os
import sys
import json
from datetime import datetime
from typing import List, Dict

from sqlalchemy import create_engine

import pandas as pd
import requests
import streamlit as st

from config import GMT7, UTC, THINGSPEAK_URL, DATABASE_URL

# local utils live one level up (keeps imports working when run from /data)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "utils")))


# ------------------------------
# Helpers
# ------------------------------
def convert_utc_to_GMT7(ts: datetime) -> datetime:
    """Take a UTC *or* naive timestamp and return it as tz-aware GMT+7 (uses GMT7 from config)."""
    if ts is None:
        return None
    if getattr(ts, "tzinfo", None) is None:
        # treat naive as UTC
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(GMT7)


def _ensure_utc_series(s: pd.Series) -> pd.Series:
    """Return a tz-aware UTC datetime Series (coerces errors -> NaT)."""
    return pd.to_datetime(s, errors="coerce", utc=True)


def _to_bangkok(series: pd.Series) -> pd.Series:
    """
    Ensure a Series of datetimes becomes tz-aware Asia/GMT+7 (uses GMT7 from config).
    Works whether original values are strings, tz-naive, or already tz-aware.
    Implementation: parse -> utc-localize -> convert to GMT7.
    """
    return _ensure_utc_series(series).dt.tz_convert(GMT7)


# ------------------------------
# ThingSpeak fetch + merge
# ------------------------------
@st.cache_data(ttl=600)
def fetch_thingspeak_data(results: int) -> List[Dict]:
    """Pull the latest <results> rows from ThingSpeak."""
    url = f"{THINGSPEAK_URL}?results={results}"
    try:
        r = requests.get(url, timeout=10)
    except Exception as exc:
        st.error(f"Failed to fetch data from ThingSpeak API: {exc}")
        return []

    if r.status_code == 200:
        return json.loads(r.text).get("feeds", [])
    st.error(f"Failed to fetch data from ThingSpeak API (status {r.status_code})")
    return []


@st.cache_data(ttl=600)
def append_new_data(df: pd.DataFrame, feeds: List[Dict]) -> pd.DataFrame:
    """Append any newer rows from ThingSpeak to df using Neon schema.

    Notes:
    - All comparisons are done in UTC (tz-aware).
    - Rows from ThingSpeak are parsed as UTC and kept as tz-aware UTC while merging.
    - Dedupe/sort applied after concat.
    """
    # determine last timestamp in df (as tz-aware UTC) or None
    if df.empty:
        last_ts_utc = None
    else:
        last_ts_utc = _ensure_utc_series(df["ds"]).max()
        if pd.isna(last_ts_utc):
            last_ts_utc = None

    rows = []
    for feed in feeds:
        created = feed.get("created_at")
        if not created:
            continue

        # parse ThingSpeak UTC timestamp into tz-aware UTC
        # expected format: "2026-03-09T12:34:56Z"
        try:
            created_ts_utc = pd.to_datetime(
                created, format="%Y-%m-%dT%H:%M:%SZ", utc=True
            )
        except Exception:
            created_ts_utc = pd.to_datetime(created, utc=True, errors="coerce")

        if pd.isna(created_ts_utc):
            continue

        # skip older/equal rows
        if last_ts_utc is not None and created_ts_utc <= last_ts_utc:
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
                "ds": created_ts_utc,  # tz-aware UTC
                "station": "VinhLong",
                "ec_us_cm": ec_us_cm,
                "temperature": temperature,
                "ec_gl": ec_gl,
            }
        )

    if not rows:
        return df

    new_df = pd.DataFrame(rows)

    # ensure ds column on new rows is tz-aware UTC
    new_df["ds"] = _ensure_utc_series(new_df["ds"])

    # concat, normalize ds on whole df to tz-aware UTC, sort, dedupe
    df = pd.concat([df, new_df], ignore_index=True)
    df["ds"] = _ensure_utc_series(df["ds"])
    df = (
        df.sort_values("ds")
        .drop_duplicates(subset=["ds", "station"], keep="last")
        .reset_index(drop=True)
    )

    return df


@st.cache_data(ttl=600)
def thingspeak_retrieve(df: pd.DataFrame) -> pd.DataFrame:
    """Top-up *df* with fresh ThingSpeak rows."""
    results = 200  # fixed pull size (adjust if needed)
    feeds = fetch_thingspeak_data(results)
    return append_new_data(df, feeds)


# ------------------------------
# Neon database
# ------------------------------
@st.cache_data(ttl=3 * 3600 + 300)  # cache for 3 hours (data updates every ~3h)
def load_data_neon() -> pd.DataFrame:
    """
    Load recent data from Neon database:
    - VinhLong: last 14 days
    - all other stations: last 12 hours

    Assumes Neon `ds` is stored in UTC (or as UTC strings). We parse as UTC to get
    tz-aware timestamps and keep them as UTC until final conversion.
    """
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        query = """
            SELECT ds, station, ec_us_cm, temperature, ec_gl
            FROM sensor_data
            WHERE
                (
                    station = 'VinhLong'
                    AND ds >= NOW() - INTERVAL '14 days'
                )
                OR
                (
                    station <> 'VinhLong'
                    AND ds >= NOW() - INTERVAL '12 hours'
                )
            ORDER BY ds DESC
        """
        df = pd.read_sql(query, conn)

    # normalize to tz-aware UTC (handles strings, naive, or tz-aware inputs)
    df["ds"] = _ensure_utc_series(df["ds"])
    return df


# ------------------------------
# Load merged dataset (cached) — final conversion to GMT+7
# ------------------------------
@st.cache_data(ttl=600)
def combined_data_retrieve() -> pd.DataFrame:
    """Load Neon + ThingSpeak merged; convert final `ds` to GMT+7 naive timestamps."""
    df = load_data_neon()
    df = thingspeak_retrieve(df)

    # At this point df["ds"] should be tz-aware UTC. Convert to GMT+7 then drop tzinfo if you want naive local times.
    df["ds"] = _ensure_utc_series(df["ds"]).dt.tz_convert(GMT7)

    # keep deterministic ordering
    df = df.sort_values("ds").reset_index(drop=True)

    return df
