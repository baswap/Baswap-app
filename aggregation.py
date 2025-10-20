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

    # ensure tz-naive datetime index
    ts = pd.to_datetime(dfi["Timestamp (GMT+7)"], errors="coerce")
    try:
        if getattr(ts.dt, "tz", None) is not None:
            ts = ts.dt.tz_localize(None)
    except Exception:
        pass
    dfi["Timestamp (GMT+7)"] = ts
    dfi = dfi.set_index("Timestamp (GMT+7)").sort_index()

    freq = rule_map[resample_freq]
    grouper = pd.Grouper(freq=freq)

    s = dfi[target_col]
    agg_results = []

    for f in agg_functions:
        if f == "Median":
            agg_df = s.groupby(grouper).median().reset_index(name=target_col)
        else:
            idx = (s.groupby(grouper).idxmin() if f == "Min" else s.groupby(grouper).idxmax())
            idx = idx.dropna()
            if idx.empty:
                agg_df = pd.DataFrame(columns=["Timestamp (GMT+7)", target_col])
            else:
                sel = dfi.loc[idx.to_numpy(), [target_col]].reset_index()
                agg_df = sel[["Timestamp (GMT+7)", target_col]]
        agg_df["Aggregation"] = f
        agg_results.append(agg_df)

    if not agg_results:
        return dfi.reset_index()
    return pd.concat(agg_results, ignore_index=True)
