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

    # make timestamps tz-naive and set as index
    ts = pd.to_datetime(dfi["Timestamp (GMT+7)"], errors="coerce")
    try:
        if getattr(ts.dt, "tz", None) is not None:
            ts = ts.dt.tz_localize(None)
    except Exception:
        pass
    dfi["Timestamp (GMT+7)"] = ts
    dfi = dfi.sort_values("Timestamp (GMT+7)").set_index("Timestamp (GMT+7)")

    if dfi.empty:
        return dfi.reset_index()

    rule = rule_map[resample_freq]
    # bin each row to the start of its hour/day; group on those bins
    bin_index = dfi.index.floor(rule)

    out_frames = []
    for f in agg_functions:
        if f == "Median":
            agg_df = dfi.groupby(bin_index)[target_col].median().reset_index()
            # name the time column
            agg_df.rename(columns={agg_df.columns[0]: "Timestamp (GMT+7)"}, inplace=True)
        else:
            # use GroupBy.idxmin/idxmax (available on GroupBy, not Resampler)
            idx = (
                dfi.groupby(bin_index)[target_col].idxmin()
                if f == "Min"
                else dfi.groupby(bin_index)[target_col].idxmax()
            ).dropna()

            if idx.empty:
                agg_df = pd.DataFrame(columns=["Timestamp (GMT+7)", target_col])
            else:
                agg_df = dfi.loc[idx, [target_col]].reset_index()
                agg_df.rename(columns={"index": "Timestamp (GMT+7)"}, inplace=True)

        agg_df["Aggregation"] = f
        out_frames.append(agg_df)

    return pd.concat(out_frames, ignore_index=True)

