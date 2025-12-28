import streamlit as st
import pandas as pd
from station_data import norm_name_capitalize

def filter_data(df, station, date_from, date_to):
    # Filter to one station, then clip rows to the selected date range.
    df = df[df["station"] == norm_name_capitalize(station)].copy()

    # If dates aren't set yet, return an empty frame (keeps downstream code simple).
    if date_from is None or date_to is None:
        return df.iloc[0:0].copy()

    # Allow users to pick dates in any order.
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    # Parse ds to datetime and drop timezone info so date comparisons behave consistently.
    ts = pd.to_datetime(df["ds"], errors="coerce")
    try:
        if getattr(ts.dt, "tz", None) is not None:
            ts = ts.dt.tz_localize(None)
    except Exception:
        pass

    # Keep rows whose ds falls within [date_from, date_to].
    mask = (ts.dt.date >= date_from) & (ts.dt.date <= date_to)
    out = df.loc[mask].copy()
    out["ds"] = ts[mask]
    out.sort_values("ds", inplace=True)
    return out

def apply_aggregation(df, target_col, resample_freq, agg_functions):
    # Resample target_col to Hour/Day and return one row per bin for each requested stat.
    import pandas as pd

    # No resampling requested.
    if resample_freq == "None":
        return df.copy()

    # UI labels -> pandas resample codes.
    rule_map = {"Hour": "h", "Day": "d"}

    # Only support the known aggregation modes.
    valid = {"Min", "Max", "Median"}
    if not set(agg_functions).issubset(valid):
        return df

    dfi = df.copy()

    # Ensure ds is datetime and tz-naive, then use it as the index for grouping.
    ts = pd.to_datetime(dfi["ds"], errors="coerce")
    try:
        if getattr(ts.dt, "tz", None) is not None:
            ts = ts.dt.tz_localize(None)
    except Exception:
        pass
    dfi["ds"] = ts
    dfi = dfi.set_index("ds").sort_index()

    freq = rule_map[resample_freq]
    grouper = pd.Grouper(freq=freq)

    s = dfi[target_col]

    # For forecast/prediction columns, keep the last value in each bin.
    pred_cols = [c for c in dfi.columns if str(c).lower().startswith("predict")]
    preds_binned = None
    if pred_cols:
        preds_binned = dfi[pred_cols].groupby(grouper).last().reset_index()

    # Build one output table per aggregation, then stack them together.
    out = []
    for f in agg_functions:
        if f == "Median":
            agg_df = s.groupby(grouper).median().reset_index(name=target_col)
        else:
            # Min/Max return the actual observed point from the bin (preserves the real value).
            idx = (s.groupby(grouper).idxmin() if f == "Min" else s.groupby(grouper).idxmax())
            idx = idx.dropna()
            if idx.empty:
                agg_df = pd.DataFrame(columns=["ds", target_col])
            else:
                sel = dfi.loc[idx.to_numpy(), [target_col]].reset_index()
                agg_df = sel[["ds", target_col]]

        # Reattach binned prediction columns, if any.
        if preds_binned is not None:
            agg_df = agg_df.merge(preds_binned, on="ds", how="left")

        # Tag rows so callers can split/plot by aggregation type.
        agg_df["Aggregation"] = f
        out.append(agg_df)

    return pd.concat(out, ignore_index=True) if out else dfi.reset_index()
