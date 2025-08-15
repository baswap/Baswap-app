from __future__ import annotations

import streamlit as st
import altair as alt
import pandas as pd
import numpy as np
from typing import Optional

from model import LITModel, LSTMTimeseries, make_predictions  
import pytorch_lightning as pl 
import torch 


_COLOR_MAP = {"Max": "red", "Min": "blue", "Median": "green"}  

def _render_aggregation_legend(
    show_predicted: bool = False,
    *,
    show_observed: bool = False,
    agg_present: bool = True,
    texts: dict | None = None,
) -> None:
    """
    Renders a compact legend:
      - If agg_present=True: colored dots for Max/Min/Median
      - If agg_present=False: single 'Observed' dot
      - Optional dashed 'Predicted' item
    Localized via `texts` (optional).
    """
    texts = texts or {}
    obs_label = texts.get("legend_observed", "Observed")
    pred_label = texts.get("legend_predicted", "Predicted")

    if agg_present:
        items = "".join(
            f"<div class='agg-item'><span class='dot' style='background:{_COLOR_MAP[k]}'></span>{k}</div>"
            for k in ["Max", "Min", "Median"]
        )
    else:
        # Single observed swatch (steelblue to match main line)
        items = f"<div class='agg-item'><span class='dot' style='background:steelblue'></span>{obs_label}</div>"

    pred = (
        f"<div class='agg-item'><span class='dash'></span>{pred_label}</div>"
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
          }}
          .agg-item .dash {{
            width:18px; height:0; border-top:2px dashed red; display:inline-block;
          }}
          @media (max-width: 640px) {{
            .agg-legend {{ gap:.5rem .9rem; font-size:0.95rem; }}
          }}
        </style>
        <div class="agg-legend">
          {items}{pred}
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
# ---------------------------------------------------------------------- #


def plot_line_chart(df: pd.DataFrame, col: str, resample_freq: str = "None", texts: dict | None = None) -> None:
    """
    Draw a line chart with:
      - line breaks across missing intervals (NaN injection),
      - localized legend & tooltips,
      - optional predictions overlay for Hour + EC series.
    """
    texts = texts or {}
    ts_label       = texts.get("axis_timestamp", "Timestamp")
    val_label      = texts.get("axis_value", "Value")
    rounded_title  = texts.get("tooltip_time_rounded", ts_label)
    exact_title    = texts.get("tooltip_time_exact",   ts_label)
    pred_time_ttl  = texts.get("tooltip_pred_time",    f"{texts.get('legend_predicted','Predicted')} {ts_label}")
    pred_value_ttl = texts.get("tooltip_pred_value",   f"{texts.get('legend_predicted','Predicted')} {val_label}")

    if col not in df.columns:
        st.error(f"Column '{col}' not found in DataFrame.")
        return

    df_filtered = df.copy()

    color_scale = alt.Scale(
        domain=["Max", "Min", "Median"],
        range=[_COLOR_MAP["Max"], _COLOR_MAP["Min"], _COLOR_MAP["Median"]],
    )

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
        df_filtered["Timestamp (Rounded)"] = _coerce_naive_datetime(df_filtered["Timestamp (GMT+7)"])
        gap = pd.Timedelta(hours=1)
        disp_fmt = "%d/%m/%Y %H:%M:%S"

    df_filtered["Timestamp (GMT+7)"] = _coerce_naive_datetime(df_filtered["Timestamp (GMT+7)"])
    df_filtered["Timestamp (Rounded)"] = _coerce_naive_datetime(df_filtered["Timestamp (Rounded)"])
    df_filtered["Timestamp (Rounded Display)"] = pd.to_datetime(
        df_filtered["Timestamp (Rounded)"]
    ).dt.strftime(disp_fmt)

    # If aggregated data is present, we have an "Aggregation" category; otherwise it's the raw/observed series
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

    # Legend (localized)
    show_predicted = (resample_freq == "Hour" and col in ["EC Value (us/cm)", "EC Value (g/l)"])
    _render_aggregation_legend(
        show_predicted=show_predicted,
        show_observed=(cat_col is None),
        agg_present=(cat_col is not None),
        texts=texts,
    )

    # Main chart
    main_chart = (
        alt.Chart(df_broken)
        .mark_line(point=True)
        .encode(
            x=alt.X("Timestamp (Rounded):T", title=ts_label),
            y=alt.Y(f"{col}:Q", title=val_label),
            color=(
                alt.Color("Aggregation:N", scale=color_scale, legend=None)
                if cat_col else alt.value("steelblue")
            ),
            tooltip=[
                alt.Tooltip("Timestamp (Rounded Display):N", title=rounded_title),
                alt.Tooltip("Timestamp (GMT+7):T",           title=exact_title, format="%d/%m/%Y %H:%M:%S"),
                alt.Tooltip(f"{col}:Q",                      title=val_label),
                # Aggregation tooltip intentionally removed
            ],
        )
        .interactive()
    )

    # Optional predictions (only Hourly EC series, using last window of Max series)
    if show_predicted and cat_col:
        max_data = df_filtered[df_filtered["Aggregation"] == "Max"].copy()
        if not max_data.empty and len(max_data) >= 2:
            max_values_numeric = max_data[[col]].iloc[-7:].copy()
            last_timestamp = max_data["Timestamp (Rounded)"].iloc[-1]
            last_value = float(max_values_numeric.iloc[-1][col])

            # Maintain your original scale conversion behavior
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
                    x=alt.X("Timestamp:T", title=ts_label),
                    y=alt.Y(f"{col}:Q",    title=val_label),
                    tooltip=[
                        alt.Tooltip("Timestamp:T", title=pred_time_ttl, format="%d/%m/%Y %H:%M:%S"),
                        alt.Tooltip(f"{col}:Q",    title=pred_value_ttl),
                        # Aggregation tooltip intentionally removed
                    ],
                )
            )

            st.altair_chart(alt.layer(predictions_chart, main_chart).resolve_scale(color="independent"),
                            use_container_width=True)
            return

    st.altair_chart(main_chart, use_container_width=True)




def display_statistics(df: pd.DataFrame, target_col: str) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="Maximum", value=f"{df[target_col].max():.2f}")
    col2.metric(label="Minimum", value=f"{df[target_col].min():.2f}")
    col3.metric(label="Average", value=f"{df[target_col].mean():.2f}")
    col4.metric(label="Std Dev", value=f"{df[target_col].std():.2f}")
