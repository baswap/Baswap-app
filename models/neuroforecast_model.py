import numpy as np
import pandas as pd
import time
from neuralforecast import NeuralForecast
from streamlit import cache_data, cache_resource

# @cache_resource
def load_models(freq):
    if freq == "1h":
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
