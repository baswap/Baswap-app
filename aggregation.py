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
    ts = pd.to_datetime(df["ds"], errors="coerce")
    try:
        if getattr(ts.dt, "tz", None) is not None:
            ts = ts.dt.tz_localize(None)
    except Exception:
        pass

    mask = (ts.dt.date >= date_from) & (ts.dt.date <= date_to)
    out = df.loc[mask].copy()
    out["ds"] = ts[mask]
    out.sort_values("ds", inplace=True)
    return out

def apply_aggregation(df, selected_cols, target_col, resample_freq, agg_functions):
    import pandas as pd

    if resample_freq == "None":
        return df.copy()

    rule_map = {"Hour": "H", "Day": "D"}
    valid = {"Min", "Max", "Median"}
    if not set(agg_functions).issubset(valid):
        return df

    dfi = df.copy()

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

    # resample any forecast columns by "last" so they survive the binning
    pred_cols = [c for c in dfi.columns if str(c).lower().startswith("predict")]
    preds_binned = None
    if pred_cols:
        preds_binned = dfi[pred_cols].groupby(grouper).last().reset_index()

    out = []
    for f in agg_functions:
        if f == "Median":
            agg_df = s.groupby(grouper).median().reset_index(name=target_col)
        else:
            idx = (s.groupby(grouper).idxmin() if f == "Min" else s.groupby(grouper).idxmax())
            idx = idx.dropna()
            if idx.empty:
                agg_df = pd.DataFrame(columns=["ds", target_col])
            else:
                sel = dfi.loc[idx.to_numpy(), [target_col]].reset_index()
                agg_df = sel[["ds", target_col]]

        if preds_binned is not None:
            agg_df = agg_df.merge(preds_binned, on="ds", how="left")

        agg_df["Aggregation"] = f
        out.append(agg_df)

    return pd.concat(out, ignore_index=True) if out else dfi.reset_index()

