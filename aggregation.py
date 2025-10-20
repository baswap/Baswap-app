import streamlit as st
import pandas as pd

def filter_data(df, date_from, date_to):
    # guard inputs
    if date_from is None or date_to is None:
        return df.iloc[0:0].copy()
    # normalize ordering
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    # make timestamps tz-naive for stable comparisons
    ts = pd.to_datetime(df["Timestamp (GMT+7)"], errors="coerce")
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
    valid = {"Min", "Max", "Median"}
    if not set(agg_functions).issubset(valid):
        st.error("Invalid aggregation functions selected.")
        return df

    dfi = df.copy()

    # tz-naive indexed time for deterministic bins
    ts = pd.to_datetime(dfi["Timestamp (GMT+7)"], errors="coerce")
    try:
        if getattr(ts.dt, "tz", None) is not None:
            ts = ts.dt.tz_localize(None)
    except Exception:
        pass
    dfi["Timestamp (GMT+7)"] = ts
    dfi = dfi.set_index("Timestamp (GMT+7)").sort_index()

    rule = rule_map[resample_freq]
    resampler = dfi[target_col].resample(rule, origin="start_day")

    agg_results = []
    for f in agg_functions:
        if f == "Median":
            agg_df = resampler.median().reset_index(name=target_col)
        else:
            idx_series = (resampler.idxmin() if f == "Min" else resampler.idxmax()).dropna()
            if idx_series.empty:
                agg_df = pd.DataFrame(columns=["Timestamp (GMT+7)", target_col])
            else:
                agg_df = dfi.loc[idx_series].reset_index()[["Timestamp (GMT+7)", target_col]]
        agg_df["Aggregation"] = f
        agg_results.append(agg_df)

    if not agg_results:
        return dfi.reset_index()
    return pd.concat(agg_results, ignore_index=True)
