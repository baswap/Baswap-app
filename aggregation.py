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

    rule_map = {"Hour": "H", "Day": "D"}
    valid = {"Min", "Max", "Median"}
    if not set(agg_functions).issubset(valid):
        st.error("Invalid aggregation functions selected.")
        return df

    dfi = df.copy()

    # normalize timestamps to tz-naive and ensure non-null
    ts = pd.to_datetime(dfi["Timestamp (GMT+7)"], errors="coerce")
    try:
        if getattr(ts.dt, "tz", None) is not None:
            ts = ts.dt.tz_localize(None)
    except Exception:
        pass
    dfi["Timestamp (GMT+7)"] = ts
    dfi = dfi.dropna(subset=["Timestamp (GMT+7)"]).sort_values("Timestamp (GMT+7)")

    if dfi.empty:
        return dfi

    rule = rule_map[resample_freq]
    # assign each row to its hour/day bin
    bin_col = dfi["Timestamp (GMT+7)"].dt.floor(rule)

    out_frames = []
    for f in agg_functions:
        if f == "Median":
            agg_df = (
                dfi.assign(_bin=bin_col)
                   .groupby("_bin")[target_col]
                   .median()
                   .reset_index()
                   .rename(columns={"_bin": "Timestamp (GMT+7)", target_col: target_col})
            )
        else:
            # pick the original row at min/max within each bin
            idx = (
                dfi.assign(_bin=bin_col)
                   .groupby("_bin")[target_col]
                   .idxmin() if f == "Min" else
                dfi.assign(_bin=bin_col)
                   .groupby("_bin")[target_col]
                   .idxmax()
            ).dropna()

            if len(idx) == 0:
                agg_df = pd.DataFrame(columns=["Timestamp (GMT+7)", target_col])
            else:
                agg_df = (
                    dfi.loc[idx, ["Timestamp (GMT+7)", target_col]]
                       .reset_index(drop=True)
                )

        agg_df["Aggregation"] = f
        out_frames.append(agg_df)

    return pd.concat(out_frames, ignore_index=True)
