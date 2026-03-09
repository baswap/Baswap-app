# update_db.py
import os
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict
import requests
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

import dotenv

dotenv.load_dotenv()  # Load environment variables from .env file if present

# CONFIG (read from env)
DATABASE_URL = os.environ["DATABASE_URL"] or os.getenv("DATABASE_URL")
THINGSPEAK_URL = os.environ["THINGSPEAK_URL"] or os.getenv("THINGSPEAK_URL")
STATION_NAME = "VinhLong"

# ---------- helper timezone funcs ----------
GMT7 = timezone(timedelta(hours=7))


def parse_thingspeak_ts(ts_utc_str: str) -> datetime:
    """ThingSpeak timestamps are like '2025-11-03T12:34:56Z' (UTC). Return tz-aware GMT+7 datetime."""
    # parse as UTC, then convert
    dt_utc = datetime.strptime(ts_utc_str, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    return dt_utc.astimezone(GMT7)


# ---------- fetch ----------
def fetch_thingspeak_data(results: int = 400) -> List[Dict]:
    """
    Pull the latest <results> rows from ThingSpeak.
    Use THINGSPEAK_URL environment variable (full JSON feed URL).
    """
    url = f"{THINGSPEAK_URL}?results={results}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    payload = r.json()
    return payload.get("feeds", [])


# ---------- process & resample ----------
def feeds_to_resampled_df(
    feeds: List[Dict], station: str = "VinhLong", sample_minutes: int = 10
) -> pd.DataFrame:
    """
    Convert ThingSpeak feeds into a DataFrame and resample to `sample_minutes` by taking the last reading in each bin.
    Returns a DataFrame with columns ['ds','station','ec_us_cm','temperature','ec_gl'] and tz-aware ds.
    """
    rows = []
    for f in feeds:
        created = f.get("created_at")
        if not created:
            continue
        try:
            ds = parse_thingspeak_ts(created)
        except Exception:
            continue

        # Extract numeric fields gracefully
        def to_float(x):
            try:
                return float(x) if x is not None and x != "" else None
            except Exception:
                return None

        ec_us_cm = to_float(f.get("field1"))  # example mapping
        temperature = to_float(f.get("field2"))
        ec_mgl = to_float(f.get("field3"))
        if ec_mgl is not None:
            ec_gl = ec_mgl / 1000.0  # convert mg/L to g/L as you did earlier

        rows.append(
            {
                "ds": ds,
                "station": station,
                "ec_us_cm": ec_us_cm,
                "temperature": temperature,
                "ec_gl": ec_gl,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=["ds", "station", "ec_us_cm", "temperature", "ec_gl"]
        )

    df = pd.DataFrame(rows)
    # set index for resampling (pandas works best when index is tz-aware datetime)
    df = df.set_index("ds").sort_index()

    # Resample to sample_minutes, picking the last non-null in each bin
    # We use .last() which picks the last row in each interval (NaNs preserved if none)
    resampled = df.resample(f"{sample_minutes}min").last()

    # drop rows where all sensors are NaN
    resampled = resampled.dropna(how="all", subset=["ec_us_cm", "temperature", "ec_gl"])

    # reset index and re-add station column (resample preserves index, station may be NaN if multiple stations)
    resampled = resampled.reset_index()
    resampled["station"] = station

    # Ensure ds is tz-aware (should be already)
    resampled["ds"] = pd.to_datetime(resampled["ds"]).dt.tz_convert(GMT7)

    # Order columns
    resampled = resampled[["ds", "station", "ec_us_cm", "temperature", "ec_gl"]]

    return resampled


# ---------- upsert into Postgres ----------
def upsert_df_to_postgres(conn, df: pd.DataFrame, table_name: str = "water_readings"):
    """
    Bulk upsert using psycopg2.execute_values and ON CONFLICT.
    Updates numeric fields to latest values in case of conflict.
    """
    if df.empty:
        print("No rows to upsert.")
        return

    tuples = [
        (
            row.ds.to_pydatetime(),  # psycopg2 accepts datetime with tzinfo
            row.station,
            None if pd.isna(row.ec_us_cm) else float(row.ec_us_cm),
            None if pd.isna(row.temperature) else float(row.temperature),
            None if pd.isna(row.ec_gl) else float(row.ec_gl),
        )
        for _, row in df.iterrows()
    ]

    cols = ("ds", "station", "ec_us_cm", "temperature", "ec_gl")
    # build SQL
    insert_sql = f"""
    INSERT INTO {table_name} (ds, station, ec_us_cm, temperature, ec_gl)
    VALUES %s
    ON CONFLICT (ds, station) DO UPDATE
      SET ec_us_cm = EXCLUDED.ec_us_cm,
          temperature = EXCLUDED.temperature,
          ec_gl = EXCLUDED.ec_gl;
    """
    with conn.cursor() as cur:
        execute_values(cur, insert_sql, tuples, template=None, page_size=100)
    conn.commit()
    print(f"Upserted {len(tuples)} rows (resampled).")


# ---------- main ----------
def main():
    results = int(os.environ.get("THINGSPEAK_PULL", "200"))  # 200 as default (adjust)
    sample_minutes = int(os.environ.get("SAMPLE_MINUTES", "10"))

    print("Fetching ThingSpeak ...")
    feeds = fetch_thingspeak_data(results=results)
    print(f"Fetched {len(feeds)} feeds.")

    df_resampled = feeds_to_resampled_df(
        feeds, station=STATION_NAME, sample_minutes=sample_minutes
    )
    print(
        f"Resampled to {len(df_resampled)} rows at {sample_minutes}-minute frequency."
    )

    # connect and upsert
    print("Connecting to Postgres...")
    conn = psycopg2.connect(DATABASE_URL)
    try:
        upsert_df_to_postgres(conn, df_resampled, table_name="sensor_data")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
