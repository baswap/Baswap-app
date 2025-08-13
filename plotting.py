# plotting.py
from __future__ import annotations

import streamlit as st
import altair as alt
import pandas as pd
import numpy as np
from typing import Optional

# keep your model imports (even if unused in this file by default)
from model import LITModel, LSTMTimeseries, make_predictions  # noqa: F401
import pytorch_lightning as pl  # noqa: F401
import torch  # noqa: F401


# ------------------------ Gap handling (robust) ------------------------ #
def _coerce_naive_datetime(s: pd.Series) -> pd.Series:
    """
    Coerce any datetime-like series to tz-naive datetime64[ns].
    Prevents sort/compare errors when a column mixes tz-aware & tz-naive values.
    """
    s = pd.to_datetime(s, errors="coerce")
    try:
        tz = getattr(s.dt, "tz", None)
        if tz is not None:
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
    If cat_col is provided (e.g., 'Aggregation'), gaps are computed per category.
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
# ---------------------------------------------------------------------- #


def plot_line_chart(df: pd.DataFrame, col: str, resample_freq: str = "None") -> None:
    """
    Draws a line chart (Altair), breaking the line across missing intervals.
    - For 'Hour' view, a gap > 3 hours is considered missing.
    - For 'Day'  view, a gap > 3 days  is considered missing.
    Raw view is kept for completeness (uses 30-minute gap).
    """
    if col not in df.columns:
        st.error(f"Column '{col}' not found in DataFrame.")
        return

    df_filtered = df.copy()

    color_scale = alt.Scale(
        domain=["Raw", "Max", "Min", "Median"],
        range=["orange", "red", "blue", "green"],
    )

    # ---------------------- Raw (optional) ---------------------- #
    if resample_freq == "None":
        df_filtered["Timestamp (GMT+7)"] = _coerce_naive_datetime(df_filtered["Timestamp (GMT+7)"])
        df_filtered["Aggregation"] = "Raw"

        df_broken = _inject_nans_for_gaps(
            df_filtered,
            time_col="Timestamp (GMT+7)",
            value_col=col,
            cat_col="Aggregation",
            max_gap=pd.Timedelta(minutes=30),
        )

        chart = (
            alt.Chart(df_broken)
            .mark_line(point=True)
            .encode(
                x=alt.X("Timestamp (GMT+7):T", title="Timestamp"),
                y=alt.Y(f"{col}:Q", title="Value"),
                color=alt.Color("Aggregation:N", title="Aggregation", scale=color_scale),
                tooltip=[
                    alt.Tooltip("Timestamp (GMT+7):T", title="Exact Time", format="%d/%m/%Y %H:%M:%S"),
                    alt.Tooltip(f"{col}:Q", title="Value"),
                ],
            )
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)
        return

    # -------------------- Hour / Day views --------------------- #
    # Round timestamps for display/grouping
    if resample_freq == "Hour":
        df_filtered["Timestamp (Rounded)"] = pd.to_datetime(df_filtered["Timestamp (GMT+7)"], errors="coerce").dt.floor("h")
        gap = pd.Timedelta(hours=3)
        disp_fmt = "%H:%M:%S"
    elif resample_freq == "Day":
        df_filtered["Timestamp (Rounded)"] = pd.to_datetime(df_filtered["Timestamp (GMT+7)"], errors="coerce").dt.floor("d")
        gap = pd.Timedelta(days=3)
        disp_fmt = "%d/%m/%Y"
    else:
        df_filtered["Timestamp (Rounded)"] = _coerce_naive_datetime(df_filtered["Timestamp (GMT+7)"])
        gap = pd.Timedelta(hours=1)
        disp_fmt = "%d/%m/%Y %H:%M:%S"

    df_filtered["Timestamp (GMT+7)"] = _coerce_naive_datetime(df_filtered["Timestamp (GMT+7)"])
    df_filtered["Timestamp (Rounded)"] = _coerce_naive_datetime(df_filtered["Timestamp (Rounded)"])
    df_filtered["Timestamp (Rounded Display)"] = pd.to_datetime(df_filtered["Timestamp (Rounded)"]).dt.strftime(disp_fmt)

    # Break lines across gaps, per Aggregation (if present)
    cat_col = "Aggregation" if "Aggregation" in df_filtered.columns else None
    df_broken = _inject_nans_for_gaps(
        df_filtered,
        time_col="Timestamp (Rounded)",
        value_col=col,
        cat_col=cat_col,
        max_gap=gap,
        display_col="Timestamp (Rounded Display)",
        display_fmt=disp_fmt,
    )

    # Main chart
    main_chart = (
        alt.Chart(df_broken)
        .mark_line(point=True)
        .encode(
            x=alt.X("Timestamp (Rounded):T", title="Timestamp"),
            y=alt.Y(f"{col}:Q", title="Value"),
            color=alt.Color("Aggregation:N", title="Aggregation", scale=color_scale) if cat_col else alt.value("steelblue"),
            tooltip=[
                alt.Tooltip("Timestamp (Rounded Display):N", title="Rounded Time"),
                alt.Tooltip("Timestamp (GMT+7):T", title="Exact Time", format="%d/%m/%Y %H:%M:%S"),
                alt.Tooltip(f"{col}:Q", title="Value"),
                alt.Tooltip("Aggregation:N", title="Aggregation") if cat_col else alt.TooltipValue(""),
            ],
        )
        .interactive()
    )

    # Optional: Predictions overlay for Hour view + EC columns
    if resample_freq == "Hour" and col in ["EC Value (us/cm)", "EC Value (g/l)"] and "Aggregation" in df_filtered.columns:
        max_data = df_filtered[df_filtered["Aggregation"] == "Max"].copy()
        if not max_data.empty and len(max_data) >= 2:
            max_values_numeric = max_data[[col]].iloc[-7:].copy()
            last_timestamp = max_data["Timestamp (Rounded)"].iloc[-1]
            last_value = float(max_values_numeric.iloc[-1][col])

            if col == "EC Value (g/l)":
                max_values_numeric = max_values_numeric * 2000

            preds = make_predictions(max_values_numeric, mode="Max")

            if col == "EC Value (g/l)":
                preds = [x / 2000 for x in preds]

            pred_times = [last_timestamp + pd.Timedelta(hours=i + 1) for i in range(len(preds))]
            combined_timestamps = [last_timestamp] + pred_times
            combined_values = [last_value] + preds

            predictions_line_df = pd.DataFrame(
                {"Timestamp": combined_timestamps, col: combined_values, "Aggregation": "Predicted"}
            )

            predictions_chart = (
                alt.Chart(predictions_line_df)
                .mark_line(color="red", strokeDash=[5, 5], point=alt.OverlayMarkDef(color="red"))
                .encode(
                    x=alt.X("Timestamp:T", title="Timestamp"),
                    y=alt.Y(f"{col}:Q", title="Value"),
                    tooltip=[
                        alt.Tooltip("Timestamp:T", title="Predicted Time", format="%d/%m/%Y %H:%M:%S"),
                        alt.Tooltip(f"{col}:Q", title="Predicted Value"),
                        alt.Tooltip("Aggregation:N", title="Aggregation"),
                    ],
                )
            )

            chart = alt.layer(predictions_chart, main_chart).resolve_scale(color="independent")
            st.altair_chart(chart, use_container_width=True)
            return

    st.altair_chart(main_chart, use_container_width=True)


def display_statistics(df: pd.DataFrame, target_col: str) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="Maximum", value=f"{df[target_col].max():.2f}")
    col2.metric(label="Minimum", value=f"{df[target_col].min():.2f}")
    col3.metric(label="Average", value=f"{df[target_col].mean():.2f}")
    col4.metric(label="Std Dev", value=f"{df[target_col].std():.2f}")
