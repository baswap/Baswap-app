from __future__ import annotations

import streamlit as st
import altair as alt
import pandas as pd
import numpy as np
from typing import Optional

# from models.lstm_model import make_predictions
from models.neuroforecast_model import make_predictions

COLOR_PI90 = "#fecaca"  # light red
COLOR_PI50 = "#fca5a5"

def _t(key: str, default: str) -> str:
    """Translate via st.session_state['texts'] with fallback to `default`."""
    return st.session_state.get("texts", {}).get(key, default)


def _render_obs_pred_legend(show_predicted: bool = False) -> None:
    """Custom legend shown above the chart."""
    observed_label  = _t("legend_observed",  "Observed")
    predicted_label = _t("legend_predicted", "Predicted")
    pi90_label      = _t("legend_pi90",      "90% prediction interval")
    pi50_label      = _t("legend_pi50",      "50% prediction interval")

    pred_html = f"<div class='agg-item'><span class='dash'></span>{predicted_label}</div>" if show_predicted else ""
    # Only show the shaded-interval legend when predictions are visible
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
          .agg-item .dot {{
            width:12px; height:12px; border-radius:999px; display:inline-block;
            background: steelblue;             /* observed color */
          }}
          .agg-item .dash {{
            width:20px; height:0; border-top:2px dashed red; display:inline-block;
          }}
          .agg-item .swatch {{
            width:18px; height:12px; border-radius:2px; display:inline-block;
            border:1px solid rgba(0,0,0,.15);
          }}
          .agg-item .swatch.pi90 {{ background: rgba(255,0,0,0.15); }}  /* light red (90%)  */
          .agg-item .swatch.pi50 {{ background: rgba(255,0,0,0.30); }}  /* darker red (50%) */
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


def render_predictions(data: pd.DataFrame, col: str):
    """
    Build two frames:
      - line_df  : ['Timestamp','median'] includes last observed + future median.
      - bands_df : ['Timestamp','lo50','hi50','lo90','hi90'] for FUTURE steps only.
    Returns (line_df, bands_df) or (None, None) if unavailable.
    """
    max_data = data[data["Aggregation"] == "Max"].copy()
    if max_data.empty or len(max_data) < 2:
        return None, None

    # select timestamp + numeric column
    max_values_numeric = max_data[["Timestamp (GMT+7)", col]].copy()

    # last observed time & value in original units
    last_timestamp = pd.to_datetime(max_data["Timestamp (Rounded)"].iloc[-1])
    last_value_orig = float(max_data[col].iloc[-1])

    # rename to NeuralForecast expected names
    max_values_numeric.rename(columns={"Timestamp (GMT+7)": "ds", col: "y"}, inplace=True)
    max_values_numeric["ds"] = pd.to_datetime(max_values_numeric["ds"])

    # if the model expects a scaled unit for g/l, convert y only
    if col == "EC Value (g/l)":
        max_values_numeric["y"] = max_values_numeric["y"] * 2000

    # required by NeuralForecast
    max_values_numeric["unique_id"] = "Baswap station"
    nf_input = max_values_numeric[["unique_id", "ds", "y"]]

    preds = make_predictions(nf_input)

    needed = [
        "AutoNBEATS-median",
        "AutoNBEATS-lo-50",
        "AutoNBEATS-hi-50",
        "AutoNBEATS-lo-90",
        "AutoNBEATS-hi-90",
    ]
    missing = [c for c in needed if c not in preds.columns]
    if missing:
        st.caption(f"⚠️ Missing prediction columns: {', '.join(missing)}")
        return None, None

    preds_df = preds[needed].astype(float).reset_index(drop=True)

    # convert back to original units if needed
    if col == "EC Value (g/l)":
        preds_df = preds_df / 2000.0

    # timestamps for future (hourly ahead)
    pred_times = [last_timestamp + pd.Timedelta(hours=i + 1) for i in range(len(preds_df))]

    # line df includes last observed + future median
    line_df = pd.DataFrame({
        "Timestamp": [last_timestamp] + pred_times,
        "median":    [last_value_orig] + preds_df["AutoNBEATS-median"].tolist(),
    })

    # bands df includes ONLY future steps (no NaNs)
    bands_df = pd.DataFrame({
        "Timestamp": pred_times,
        "lo50": preds_df["AutoNBEATS-lo-50"].values,
        "hi50": preds_df["AutoNBEATS-hi-50"].values,
        "lo90": preds_df["AutoNBEATS-lo-90"].values,
        "hi90": preds_df["AutoNBEATS-hi-90"].values,
    })

    return line_df, bands_df


def plot_line_chart(df: pd.DataFrame, col: str, resample_freq: str = "None") -> None:
    if col not in df.columns:
        st.error(f"Column '{col}' not found in DataFrame.")
        return

    df_filtered = df.copy()

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

    # Normalize timestamps
    df_filtered["Timestamp (GMT+7)"] = _coerce_naive_datetime(df_filtered["Timestamp (GMT+7)"])
    df_filtered["Timestamp (Rounded)"] = _coerce_naive_datetime(df_filtered["Timestamp (Rounded)"])
    df_filtered["Timestamp (Rounded Display)"] = pd.to_datetime(
        df_filtered["Timestamp (Rounded)"]
    ).dt.strftime(disp_fmt)

    cat_col = "Aggregation" if "Aggregation" in df_filtered.columns else None

    # Break the line across long gaps
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
    show_pred = (resample_freq == "Hour" and col in ["EC Value (us/cm)", "EC Value (g/l)"])
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

    # Prediction overlays (only for Hourly EC)
    if show_pred:
        line_df, bands_df = render_predictions(df_filtered, col)
        if line_df is not None and bands_df is not None and not bands_df.empty:
            # 90% band (light red)
            band90 = (
                alt.Chart(bands_df)
                .mark_area(opacity=0.15, color="red")  # <-- original style
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

            # 50% band (darker red)
            band50 = (
                alt.Chart(bands_df)
                .mark_area(opacity=0.30, color="red")  # <-- original style
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

            # Median dashed line (connects to last observed)
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

            chart = alt.layer(band90, band50, pred_line, main_chart)  # <-- no legend layer
            st.altair_chart(chart, use_container_width=True)
            return

    # Fallback: observed only
    st.altair_chart(main_chart, use_container_width=True)



def display_statistics(df: pd.DataFrame, target_col: str) -> None:
    # translate via session (uses your existing _t helper)
    t_max = _t("stats_max", "Maximum")
    t_min = _t("stats_min", "Minimum")
    t_avg = _t("stats_avg", "Average")
    t_std = _t("stats_std", "Std Dev")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label=t_max, value=f"{df[target_col].max():.2f}")
    col2.metric(label=t_min, value=f"{df[target_col].min():.2f}")
    col3.metric(label=t_avg, value=f"{df[target_col].mean():.2f}")
    col4.metric(label=t_std, value=f"{df[target_col].std():.2f}")
