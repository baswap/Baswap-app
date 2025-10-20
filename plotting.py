from __future__ import annotations

import streamlit as st
import altair as alt
import pandas as pd
import numpy as np
from typing import Optional

# from models.lstm_model import make_predictions
from models.neuroforecast_model import make_predictions

COLOR_PI90 = "#fecaca" 
COLOR_PI50 = "#fca5a5"

def _t(key: str, default: str) -> str:
    """Translate via st.session_state['texts'] with fallback to `default`."""
    return st.session_state.get("texts", {}).get(key, default)


def _render_obs_pred_legend(show_predicted: bool = False) -> None:
    """Custom legend shown above the chart (no change to chart colors)."""
    observed_label  = _t("legend_observed",  "Observed")
    predicted_label = _t("legend_predicted", "Predicted")
    pi90_label      = _t("legend_pi90",      "90% prediction interval")
    pi50_label      = _t("legend_pi50",      "50% prediction interval")

    pred_html = f"<div class='agg-item'><span class='dash'></span>{predicted_label}</div>" if show_predicted else ""
    pi_html = (
        f"<div class='agg-item'><span class='swatch pi90'></span>{pi90_label}</div>"
        f"<div class='agg-item'><span class='swatch pi50'></span>{pi50_label}</div>"
        if show_predicted else ""
    )

    st.markdown(
        f"""
        <style>
          .agg-legend {{
            display:flex; flex-wrap:wrap; gap:.6rem 1rem; align-items:center;
            margin:.25rem 0 .5rem 0; font-weight:600;
          }}
          .agg-item {{ display:inline-flex; align-items:center; gap:.45rem; }}

          /* Observed / Predicted styles */
          .agg-item .dot {{
            width:12px; height:12px; border-radius:999px; display:inline-block;
            background: steelblue;
          }}
          .agg-item .dash {{
            width:20px; height:0; border-top:2px dashed red; display:inline-block;
          }}

          /* Swatches */
          .agg-item .swatch {{
            position:relative; width:18px; height:12px; border-radius:2px;
            display:inline-block; border:1px solid rgba(0,0,0,.15); overflow:hidden;
          }}
          .agg-item .swatch::before,
          .agg-item .swatch::after {{ content:""; position:absolute; inset:0; border-radius:2px; }}

          /* 90% chip (same look as chart) */
          .agg-item .swatch.pi90::before {{ background: rgba(255,0,0,0.15); }}
          .agg-item .swatch.pi90::after  {{ background: transparent; }}

          /* 50% chip — make it BRIGHTER/REDder than before */
          .agg-item .swatch.pi50::before {{ background: rgba(255,0,0,0.15); }}   /* base */
          .agg-item .swatch.pi50::after  {{ background: rgba(255,60,60,0.75); }}  /* brighter overlay */

          
          @media (max-width: 640px) {{
            .agg-legend {{ gap:.5rem .9rem; font-size:0.95rem; }}
          }}
        </style>
        <div class="agg-legend">
          <div class="agg-item"><span class="dot"></span>{observed_label}</div>
          {pred_html}
          {pi_html}
        </div>
        """,
        unsafe_allow_html=True,
    )





def _coerce_naive_datetime(s: pd.Series) -> pd.Series:
    """Coerce any datetime-like series to tz-naive datetime64[ns]."""
    s = pd.to_datetime(s, errors="coerce")
    try:
        if getattr(s.dt, "tz", None) is not None:
            s = s.dt.tz_localize(None)
    except Exception:
        pass
    return s


def _inject_nans_for_gaps(
    df: pd.DataFrame,
    time_col: str,
    value_col: str,
    *,
    cat_col: Optional[str],
    max_gap: pd.Timedelta,
    display_col: Optional[str] = None,
    display_fmt: Optional[str] = None,
) -> pd.DataFrame:
    """
    Insert NaN rows at midpoints of gaps > max_gap so Altair breaks the line.
    If cat_col is provided (e.g. 'Aggregation'), compute per category.
    """
    d = df.copy()
    d[time_col] = _coerce_naive_datetime(d[time_col])

    groups = [(None, d)] if not cat_col else d.groupby(cat_col, dropna=False)
    pieces = []

    for key, g in groups:
        g = g.sort_values(time_col)
        deltas = g[time_col].diff()
        gap_mask = deltas > max_gap
        if not gap_mask.any():
            pieces.append(g)
            continue

        prev_times = g[time_col].shift(1)[gap_mask]
        next_times = g[time_col][gap_mask]
        mid_times = prev_times + (next_times - prev_times) / 2
        mid_times = _coerce_naive_datetime(mid_times)

        fill = pd.DataFrame({time_col: mid_times, value_col: np.nan})
        if cat_col:
            fill[cat_col] = key
        if display_col and display_fmt:
            fill[display_col] = pd.to_datetime(fill[time_col]).dt.strftime(display_fmt)

        pieces.append(pd.concat([g, fill], ignore_index=True))

    out = pd.concat(pieces, ignore_index=True)
    out[time_col] = _coerce_naive_datetime(out[time_col])
    out = out.sort_values(by=[time_col], kind="mergesort").reset_index(drop=True)
    return out

def render_predictions(data: pd.DataFrame, col: str, resample_freq: str):
    """
    Builds two frames aligned in time:
      - line_df  : ['Timestamp','median'] includes last observed + future median.
      - bands_df : ['Timestamp','lo50','hi50','lo90','hi90'] for FUTURE steps only.

    Robust to NaNs and guarantees bands start at the same step as the dashed line.
    """
    if data is None or data.empty or col not in data.columns:
        return None, None

    df_in = data.copy()

    # Prefer aggregated 'Median' (fallback to 'Max') with ≥2 valid points
    if "Aggregation" in df_in.columns:
        picked = None
        for candidate in ("Median", "Max"):
            sub = df_in[df_in["Aggregation"] == candidate].copy()
            if pd.to_numeric(sub[col], errors="coerce").dropna().shape[0] >= 2:
                picked = sub
                break
        if picked is None:
            return None, None
        df_in = picked

    # Anchor on the last NON-NULL observed value and its rounded timestamp
    if "Timestamp (Rounded)" not in df_in.columns:
        return None, None
    y_all = pd.to_numeric(df_in[col], errors="coerce")
    valid_idx = y_all.dropna().index
    if len(valid_idx) < 2:
        return None, None
    last_idx = valid_idx[-1]
    last_timestamp = pd.to_datetime(df_in.loc[last_idx, "Timestamp (Rounded)"])
    last_value_orig = float(y_all.loc[last_idx])

    # History for the model up to the last valid point
    hist = df_in.loc[df_in.index <= last_idx, ["Timestamp (GMT+7)", col]].copy()
    hist.rename(columns={"Timestamp (GMT+7)": "ds", col: "y"}, inplace=True)
    hist["ds"] = pd.to_datetime(hist["ds"], errors="coerce")
    hist["y"] = pd.to_numeric(hist["y"], errors="coerce")
    hist = hist.dropna(subset=["ds", "y"]).sort_values("ds").drop_duplicates(subset=["ds"], keep="last")

    # Unit conversion for the model if needed
    if col == "EC Value (g/l)":
        hist["y"] = hist["y"] * 2000.0

    hist["unique_id"] = "Baswap station"
    nf_input = hist[["unique_id", "ds", "y"]]

    try:
        preds = make_predictions(nf_input, resample_freq)
    except Exception:
        return None, None
    if preds is None or preds.empty:
        return None, None

    # Tolerant column picking (works across model variants)
    colmap = {
        "median": ["AutoNBEATS-median", "median", "yhat", "yhat_median"],
        "lo50":   ["AutoNBEATS-lo-50", "lo50", "p25"],
        "hi50":   ["AutoNBEATS-hi-50", "hi50", "p75"],
        "lo90":   ["AutoNBEATS-lo-90", "lo90", "p05"],
        "hi90":   ["AutoNBEATS-hi-90", "hi90", "p95"],
    }
    def _pick(name: str):
        for c in colmap[name]:
            if c in preds.columns:
                return pd.to_numeric(preds[c], errors="coerce")
        return None

    m   = _pick("median")
    lo5 = _pick("lo50")
    hi5 = _pick("hi50")
    lo9 = _pick("lo90")
    hi9 = _pick("hi90")
    if any(s is None for s in (m, lo5, hi5, lo9, hi9)):
        return None, None

    pred_df = pd.DataFrame({"median": m, "lo50": lo5, "hi50": hi5, "lo90": lo9, "hi90": hi9})

    # Back to original units if we scaled
    if col == "EC Value (g/l)":
        pred_df = pred_df / 2000.0

    # 🔧 KEY STEP: drop rows where ANY band is NaN/inf, so bands & median align
    pred_df = pred_df.replace([np.inf, -np.inf], np.nan)
    pred_df = pred_df.dropna(subset=["median", "lo50", "hi50", "lo90", "hi90"]).reset_index(drop=True)
    if pred_df.empty:
        return None, None

    # Build future timestamps for the remaining rows
    n = len(pred_df)
    if resample_freq == "Day":
        pred_times = [last_timestamp + pd.Timedelta(days=i + 1) for i in range(n)]
    else:
        pred_times = [last_timestamp + pd.Timedelta(hours=i + 1) for i in range(n)]

    line_df = pd.DataFrame({
        "Timestamp": [last_timestamp] + pred_times,
        "median":    [last_value_orig] + pred_df["median"].tolist(),
    })
    bands_df = pd.DataFrame({
        "Timestamp": pred_times,
        "lo50": pred_df["lo50"].values,
        "hi50": pred_df["hi50"].values,
        "lo90": pred_df["lo90"].values,
        "hi90": pred_df["hi90"].values,
    })
    return line_df, bands_df


def plot_line_chart(df: pd.DataFrame, col: str, resample_freq: str = "None") -> None:
    # explicit empty guards to avoid "disappearing" charts
    if df is None or df.empty or col not in df.columns or df[col].dropna().empty:
        st.info("No data for this date range.")
        return

    df_filtered = df.copy().sort_values("Timestamp (GMT+7)")
    df_filtered["Timestamp (GMT+7)"] = _coerce_naive_datetime(df_filtered["Timestamp (GMT+7)"])

    # Round time and choose gap/format
    if resample_freq == "Hour":
        df_filtered["Timestamp (Rounded)"] = pd.to_datetime(
            df_filtered["Timestamp (GMT+7)"], errors="coerce"
        ).dt.floor("h")
        gap = pd.Timedelta(hours=3)
        disp_fmt = "%H:%M:%S"
    elif resample_freq == "Day":
        df_filtered["Timestamp (Rounded)"] = pd.to_datetime(
            df_filtered["Timestamp (GMT+7)"], errors="coerce"
        ).dt.floor("d")
        gap = pd.Timedelta(days=3)
        disp_fmt = "%d/%m/%Y"
    else:
        df_filtered["Timestamp (Rounded)"] = _coerce_naive_datetime(
            df_filtered["Timestamp (GMT+7)"]
        )
        gap = pd.Timedelta(hours=1)
        disp_fmt = "%d/%m/%Y %H:%M:%S"

    # normalize rounded timestamps and display strings
    df_filtered["Timestamp (Rounded)"] = _coerce_naive_datetime(df_filtered["Timestamp (Rounded)"])
    df_filtered["Timestamp (Rounded Display)"] = pd.to_datetime(
        df_filtered["Timestamp (Rounded)"]
    ).dt.strftime(disp_fmt)

    cat_col = "Aggregation" if "Aggregation" in df_filtered.columns else None

    # break the line across long gaps
    df_broken = _inject_nans_for_gaps(
        df_filtered,
        time_col="Timestamp (Rounded)",
        value_col=col,
        cat_col=cat_col,
        max_gap=gap,
        display_col="Timestamp (Rounded Display)",
        display_fmt=disp_fmt,
    )

    # Localized axis & tooltip labels
    axis_x = _t("axis_timestamp", "Timestamp")
    axis_y = _t("axis_value", "Value")
    t_rounded = _t("tooltip_rounded_time", axis_x)
    t_exact = _t("tooltip_exact_time", axis_x)
    t_value = _t("tooltip_value", axis_y)
    t_pred_time = _t("tooltip_predicted_time", axis_x)
    t_pred_value = _t("tooltip_predicted_value", axis_y)

    # Observed/Predicted legend (HTML above chart)
    show_pred = (col in ["EC Value (us/cm)", "EC Value (g/l)"])
    _render_obs_pred_legend(show_predicted=show_pred)

    # Observed chart
    encodings = dict(
        x=alt.X("Timestamp (Rounded):T", title=axis_x),
        y=alt.Y(f"{col}:Q", title=axis_y),
        color=alt.value("steelblue"),
        tooltip=[
            alt.Tooltip("Timestamp (Rounded Display):N", title=t_rounded),
            alt.Tooltip("Timestamp (GMT+7):T", title=t_exact, format="%d/%m/%Y %H:%M:%S"),
            alt.Tooltip(f"{col}:Q", title=t_value),
        ],
    )
    if cat_col:
        encodings["detail"] = alt.Detail("Aggregation:N")

    main_chart = alt.Chart(df_broken).mark_line(point=True).encode(**encodings).interactive()

    # Prediction overlays only if we still have usable data
    if show_pred:
        line_df, bands_df = render_predictions(df_filtered, col, resample_freq)
        if line_df is not None and bands_df is not None and not bands_df.empty:
            band90 = (
                alt.Chart(bands_df)
                .mark_area(opacity=0.15, color="red")
                .encode(
                    x=alt.X("Timestamp:T", title=axis_x),
                    y=alt.Y("lo90:Q", title=axis_y),
                    y2=alt.Y2("hi90:Q"),
                    tooltip=[
                        alt.Tooltip("Timestamp:T", title=t_pred_time, format="%d/%m/%Y %H:%M:%S"),
                        alt.Tooltip("lo90:Q", title="P5"),
                        alt.Tooltip("hi90:Q", title="P95"),
                    ],
                )
            )
            band50 = (
                alt.Chart(bands_df)
                .mark_area(opacity=0.30, color="red")
                .encode(
                    x=alt.X("Timestamp:T", title=axis_x),
                    y=alt.Y("lo50:Q", title=axis_y),
                    y2=alt.Y2("hi50:Q"),
                    tooltip=[
                        alt.Tooltip("Timestamp:T", title=t_pred_time, format="%d/%m/%Y %H:%M:%S"),
                        alt.Tooltip("lo50:Q", title="P25"),
                        alt.Tooltip("hi50:Q", title="P75"),
                    ],
                )
            )
            pred_line = (
                alt.Chart(line_df)
                .mark_line(color="red", strokeDash=[5, 5], point=alt.OverlayMarkDef(color="red"))
                .encode(
                    x=alt.X("Timestamp:T", title=axis_x),
                    y=alt.Y("median:Q", title=axis_y),
                    tooltip=[
                        alt.Tooltip("Timestamp:T", title=t_pred_time, format="%d/%m/%Y %H:%M:%S"),
                        alt.Tooltip("median:Q", title=t_pred_value),
                    ],
                )
            )
            chart = alt.layer(band90, band50, pred_line, main_chart)
            st.altair_chart(chart, use_container_width=True)
            return

    st.altair_chart(main_chart, use_container_width=True)



def display_statistics(df: pd.DataFrame, target_col: str) -> None:
    t_max = _t("stats_max", "Maximum")
    t_min = _t("stats_min", "Minimum")
    t_avg = _t("stats_avg", "Average")
    t_std = _t("stats_std", "Std Dev")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label=t_max, value=f"{df[target_col].max():.2f}")
    col2.metric(label=t_min, value=f"{df[target_col].min():.2f}")
    col3.metric(label=t_avg, value=f"{df[target_col].mean():.2f}")
    col4.metric(label=t_std, value=f"{df[target_col].std():.2f}")
