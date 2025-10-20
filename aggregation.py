import streamlit as st
import pandas as pd

def filter_data(df, date_from, date_to):
    if date_from is None or date_to is None:
        return df.iloc[0:0].copy()
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    ts = pd.to_datetime(df["Timestamp (GMT+7)"], errors="coerce")
    # normalize to tz-naive for stable comparisons/plotting
    try:
        if getattr(ts.dt, "tz", None) is not None:
            ts = ts.dt.tz_localize(None)
    except Exception:
        pass

    mask = (ts.dt.date >= date_from) & (ts.dt.date <= date_to)
    out = df.loc[mask].copy()
    out["Timestamp (GMT+7)"] = ts[mask]
    out.sort_values("Timestamp (GMT+7)", inplace=True)
    return out

def apply_aggregation(df, selected_cols, target_col, resample_freq, agg_functions):
    if resample_freq == "None":
        return df.copy()

    rule_map = {"Hour": "h", "Day": "d"}
    rule = rule_map[resample_freq]
    valid = {"Min", "Max", "Median"}
    if not set(agg_functions).issubset(valid):
        st.error("Invalid aggregation functions selected.")
        return df

    dfi = df.copy()
    ts = pd.to_datetime(dfi["Timestamp (GMT+7)"], errors="coerce")
    try:
        if getattr(ts.dt, "tz", None) is not None:
            ts = ts.dt.tz_localize(None)
    except Exception:
        pass
    dfi["Timestamp (GMT+7)"] = ts
    dfi = dfi.set_index("Timestamp (GMT+7)").sort_index()

    agg_results = []
    # anchor bins to day starts for deterministic edges
    resampler = dfi[target_col].resample(rule, origin="start_day")

    for f in agg_functions:
        if f in ("Min", "Max"):
            idx = getattr(resampler, "idxmin" if f == "Min" else "idxmax")().dropna()
            agg_df = dfi.loc[idx].reset_index()
        else:
            agg_df = resampler.median().reset_index(name=target_col)
        agg_df["Aggregation"] = f
        agg_results.append(agg_df)

    return pd.concat(agg_results, ignore_index=True)
