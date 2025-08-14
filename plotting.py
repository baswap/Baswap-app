# plotting.py
from __future__ import annotations

import streamlit as st
import altair as alt
import pandas as pd
import numpy as np
from typing import Optional

# keep model imports (used for predictions)
from model import LITModel, LSTMTimeseries, make_predictions  # noqa: F401
import pytorch_lightning as pl  # noqa: F401
import torch  # noqa: F401
from config import APP_TEXTS, TIMESTAMP_COL

# ----------------------------------------------------------------------
# Responsive custom legend (outside the chart so it doesn't shrink plots)
# ----------------------------------------------------------------------
_COLOR_MAP = {"Max": "red", "Min": "blue", "Median": "green"}  # no Raw here

def _render_aggregation_legend(observed_label: str, *, show_predicted: bool = False, predicted_label: str = "Predicted") -> None:
    pred_html = f"<div class='agg-item'><span class='dash'></span>{predicted_label}</div>" if show_predicted else ""
    st.markdown(
        f"""
        <style>
          .agg-legend {{ display:flex; flex-wrap:wrap; gap:.6rem 1rem; align-items:center; margin:.25rem 0 .5rem 0; font-weight:600; }}
          .agg-item {{ display:inline-flex; align-items:center; gap:.45rem; }}
          .agg-item .dot {{ width:12px; height:12px; border-radius:999px; display:inline-block; background:steelblue; }}
          .agg-item .dash {{ width:18px; height:0; border-top:2px dashed red; display:inline-block; }}
        </style>
        <div class="agg-legend">
          <div class='agg-item'><span class='dot'></span>{observed_label}</div>
          {pred_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

# ------------------------ Gap handling (robust) ------------------------ #
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
# ---------------------------------------------------------------------- #


def plot_line_chart(df: pd.DataFrame, col: str, resample_freq: str = "None", *, lang: str = "en") -> None:
    # guardrails
    if df is None or df.empty:
        st.info("No data to plot.")
        return
    if col not in df.columns:
        st.error(f"Column '{col}' not found in DataFrame.")
        return

    texts = APP_TEXTS.get(lang, APP_TEXTS["en"])
    observed_label = texts.get("observed_label", "Observed")
    predicted_label = texts.get("predicted_label", "Predicted")
    x_title = texts.get("axis_timestamp", "Timestamp")
    y_title = texts.get("axis_value", "Value")

    df_filtered = df.copy()

    # ---- rounding & gap thresholds (unchanged behavior) ----
    freq = (resample_freq or "").strip().lower()
    if freq == "hour":
        df_filtered["Timestamp (Rounded)"] = pd.to_datetime(df_filtered[TIMESTAMP_COL], errors="coerce").dt.floor("h")
        gap = pd.Timedelta(hours=3)
        disp_fmt = "%H:%M:%S"
    elif freq == "day":
        df_filtered["Timestamp (Rounded)"] = pd.to_datetime(df_filtered[TIMESTAMP_COL], errors="coerce").dt.floor("d")
        gap = pd.Timedelta(days=3)
        disp_fmt = "%d/%m/%Y"
    else:
        df_filtered["Timestamp (Rounded)"] = _coerce_naive_datetime(df_filtered[TIMESTAMP_COL])
        gap = pd.Timedelta(hours=1)
        disp_fmt = "%d/%m/%Y %H:%M:%S"

    df_filtered[TIMESTAMP_COL] = _coerce_naive_datetime(df_filtered[TIMESTAMP_COL])
    df_filtered["Timestamp (Rounded)"] = _coerce_naive_datetime(df_filtered["Timestamp (Rounded)"])
    df_filtered["Timestamp (Rounded Display)"] = pd.to_datetime(df_filtered["Timestamp (Rounded)"]).dt.strftime(disp_fmt)

    # ---- keep ONLY Max, and DISPLAY it as Observed (localized) ----
    has_cat = "Aggregation" in df_filtered.columns
    if has_cat:
        df_filtered = df_filtered[df_filtered["Aggregation"] == "Max"].copy()
        # for legend/tooltip only
        df_filtered["AggDisplay"] = observed_label

    # NaN injection for gaps
    df_broken = _inject_nans_for_gaps(
        df_filtered,
        time_col="Timestamp (Rounded)",
        value_col=col,
        cat_col=("AggDisplay" if has_cat else None),
        max_gap=gap,
        display_col="Timestamp (Rounded Display)",
        display_fmt=disp_fmt,
    )

    # legend: just Observed (+ Predicted if applicable)
    _render_aggregation_legend(
        observed_label,
        show_predicted=(freq == "hour" and col in ["EC Value (us/cm)", "EC Value (g/l)"]),
        predicted_label=predicted_label,
    )

    tooltips = [
        alt.Tooltip("Timestamp (Rounded Display):N", title="Rounded Time"),
        alt.Tooltip(f"{TIMESTAMP_COL}:T", title="Exact Time", format="%d/%m/%Y %H:%M:%S"),
        alt.Tooltip(f"{col}:Q", title=y_title),
    ]
    if has_cat:
        tooltips.append(alt.Tooltip("AggDisplay:N", title=texts.get("legend_aggregation", "Aggregation")))

    # main chart: single observed series in steelblue
    main_chart = (
        alt.Chart(df_broken)
        .mark_line(point=True)
        .encode(
            x=alt.X("Timestamp (Rounded):T", title=x_title),
            y=alt.Y(f"{col}:Q", title=y_title),
            color=(alt.Value("steelblue")),  # single series color
            tooltip=tooltips,
        )
        .interactive()
    )

    # predictions overlay (Hourly EC only) — unchanged logic, localized tooltip label
    if freq == "hour" and col in ["EC Value (us/cm)", "EC Value (g/l)"] and "Aggregation" in df.columns:
        # lazy import to avoid heavy deps when not needed
        from model import make_predictions
        max_data = df_filtered.copy()  # already filtered to Aggregation == "Max"
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
            predictions_line_df = pd.DataFrame(
                {"Timestamp": [last_timestamp] + pred_times, col: [last_value] + preds, "AggDisplay": predicted_label}
            )
            predictions_chart = (
                alt.Chart(predictions_line_df)
                .mark_line(color="red", strokeDash=[5, 5], point=alt.OverlayMarkDef(color="red"))
                .encode(
                    x=alt.X("Timestamp:T", title=x_title),
                    y=alt.Y(f"{col}:Q", title=y_title),
                    tooltip=[
                        alt.Tooltip("Timestamp:T", title=f"{predicted_label} Time", format="%d/%m/%Y %H:%M:%S"),
                        alt.Tooltip(f"{col}:Q", title=f"{predicted_label} {y_title}"),
                        alt.Tooltip("AggDisplay:N", title=texts.get("legend_aggregation", "Aggregation")),
                    ],
                )
            )
            st.altair_chart(alt.layer(predictions_chart, main_chart).resolve_scale(color="independent"), use_container_width=True)
            return

    st.altair_chart(main_chart, use_container_width=True)


def display_statistics(df: pd.DataFrame, target_col: str) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="Maximum", value=f"{df[target_col].max():.2f}")
    col2.metric(label="Minimum", value=f"{df[target_col].min():.2f}")
    col3.metric(label="Average", value=f"{df[target_col].mean():.2f}")
    col4.metric(label="Std Dev", value=f"{df[target_col].std():.2f}")
