import numpy as np
import pandas as pd
import time
from neuralforecast import NeuralForecast
from streamlit import cache_data, cache_resource
from pathlib import Path
import os
import streamlit as st

#!/usr/bin/env python3
import os
import sys
import csv
from pathlib import Path

def human(bytesize):
    # both MiB (binary) and MB (decimal) if you need one; here show MiB
    return f"{bytesize / 1024**2:.6f} MiB"

def list_files(root):
    root = Path(root)
    rows = []
    total = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for f in filenames:
            fp = Path(dirpath) / f
            try:
                size = fp.stat().st_size
            except (OSError, PermissionError):
                continue
            rows.append((size, str(fp)))
            total += size
    # sort descending by size
    rows.sort(reverse=True, key=lambda x: x[0])
    return rows, total

def print_table(rows, total, top=None):
    print(f"{'Size (MiB)':>12}  {'Bytes':>12}  Path")
    print("-"*80)
    shown = rows if top is None else rows[:top]
    for size, path in shown:
        print(f"{size/1024**2:12.6f}  {size:12d}  {path}")
    print("-"*80)
    print(f"TOTAL: {total/1024**2:.6f} MiB   ({total} bytes)")

@cache_resource
def load_models(freq):
    if freq == "1h":
        # rows, total = list_files("models/weights/nbeats_24")
        # print_table(rows, total, top=200)   # change top=None to show everything
        nf = NeuralForecast.load(path="models/weights/nbeats_24")
    print("model loaded")
    return nf

@cache_data
def make_predictions(df, freq="1h"):
    time_start = time.time()
    model = load_models(freq)
    preds = model.predict(df)
    print("Prediction takes:", time.time() - time_start, "(s)")
    return preds

# Create dummy data
def create_dummy_data(n=48):
    df = pd.DataFrame({
        "unique_id": ["series_1"] * n,                # Same ID for the whole series
        "ds": pd.date_range(start="2023-01-01", periods=n, freq="h"),  # hourly timestamps
        "y": np.random.randn(n)                      # random values
    })
    return df

if __name__ == "__main__":
    dummy_df = create_dummy_data()
    for _ in range(5):
        make_predictions(dummy_df, freq="1h")
