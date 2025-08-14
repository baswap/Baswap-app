# plotting.py
from __future__ import annotations

import streamlit as st
import altair as alt
import pandas as pd
import numpy as np
from typing import Optional
from config import APP_TEXTS, TIMESTAMP_COL  # NEW

# --- Local helpers -----------------------------------------------------

def _get_lang() -> str:
    """Infer current UI language from query params (matches your app)."""
    try:
        qp = st.query_params  # newer API
    except Exception:
        qp = st.experimental_get_query_params()  # fallback
    val = qp.get("lang", "en")
    if isinstance(val, (list, tuple)):
        return val[0] if val else "en"
    return val or "en"

def _t(key: str, default: str) -> str:
    """Tiny i18n helper with safe fallback."""
    lang = _get_lang()
    return APP_TEXTS.get(lang, APP_TEXTS.get("en", {})).get(key, default)

# Color choice kept simple; one observed series + optional predicted overlay.
_OBS_COLOR = "steelblue"
_PRED_COLOR = "red"

def _render_aggregation_legend(show_predicted: bool = False) -> None:
    """Legend with only Observed (+ Predicted if shown). i18n-aware."""
    observed_lbl = _t("legend_observed", "Observed")
    predicted_lbl = _t("legend_predicted", "Predicted")
    st.markdown(
        f"""
        <style>
          .agg-legend {{
            display:flex; flex-wrap:wrap; gap:.6rem 1rem; align-items:center;
            margin:.25rem 0 .5rem 0; font-weight:600;
          }}
          .agg-item {{ display:inline-flex; align-items:center; gap:.45rem; }}
          .dot  {{ width:12px; height:12px; border-radius:999px; display:inline-block; }}
          .dash {{ width:18px; height:0; border-top:2px dashed {_PRED_COLOR}; display:inline-block; }}
          @media (max-width: 640px) {{ .agg-legend {{ gap:.5rem .9rem; font-size:0.95rem; }} }}
        </style>
        <div class="agg-legend">
          <div class='agg-item'><span class='dot' style='background:{_OBS_COLOR}'></span>{observed_lbl}</div>
          {("<div class='agg-item'><span class='dash'></span>" + predicted_lbl + "</div>") if show_predicted else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )

# ------------------------ Gap handling (unchanged) --------------------- #
def _coerce_naive_datetime(s: pd.Series) -> pd.Series:
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
    d = df.copy()
    d[time_col] = _coerce_naive_datetime(d[time_col])
    groups = [(None, d)] if not cat_col else d.groupby(cat_col, dropna=False)
    pieces = []
    for key, g in groups:
        g = g.sort_values(time_col)
        deltas = g[time_col].diff()
        gap_mask = deltas > max_gap
        if not gap_mask.any():
            pieces.append(g); continue
        prev_times = g[time_col].shift(1)[gap_mask]
        next_times = g[time_col][gap_mask]
        mid_times = prev_times + (next_times - prev_times) / 2
        mid_times = _coerce_naive_datetime(mid_times)
        fill = pd.DataFrame({time_col: mid_times, value_col: np.nan})
        if cat_col: fill[cat_col] = key
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
    Draw a line chart that:
      - shows ONLY the 'Max' aggregation, relabeled as 'Observed' (i18n),
      - hides Min/Median lines entirely,
      - keeps NaN gap breaks,
      - overlays predictions only for Hourly EC series.
    """
    if df is None or df.empty:
        st.info(_t("no_data_msg", "No data to plot."))
        return
    if col not in df.columns:
        st.error(f"Column '{col}' not found in DataFrame.")
        return

    df_filtered = df.copy()

    # ---- Resample context ----
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

    # ---- Keep only 'Max' and relabel to 'Observed' for display ----
    observed_lbl = _t("legend_observed", "Observed")
    if "Aggregation" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["Aggregation"] == "Max"].copy()
        # Optional: store a display label if you ever want to show it in tooltips.
        df_filtered["Series"] = observed_lbl

    # ---- Common time columns ----
    df_filtered[TIMESTAMP_COL] = _coerce_naive_datetime(df_filtered[TIMESTAMP_COL])
    df_filtered["Timestamp (Rounded)"] = _coerce_naive_datetime(df_filtered["Timestamp (Rounded)"])
    df_filtered["Timestamp (Rounded Display)"] = pd.to_datetime(df_filtered["Timestamp (Rounded)"]).dt.strftime(disp_fmt)

    # ---- Inject NaNs to break lines across gaps ----
    df_broken = _inject_nans_for_gaps(
        df_filtered,
        time_col="Timestamp (Rounded)",
        value_col=col,
        cat_col=None,  # single observed series only
        max_gap=gap,
        display_col="Timestamp (Rounded Display)",
        display_fmt=disp_fmt,
    )

    # ---- External legend (Observed + maybe Predicted) ----
    show_predicted = (freq == "hour" and col in ["EC Value (us/cm)", "EC Value (g/l)"])
    _render_aggregation_legend(show_predicted=show_predicted)

    # Axis titles from i18n (fallback safe)
    x_title = _t("axis_timestamp", "Timestamp")
    y_title = _t("axis_value", "Value")

    # ---- Main observed chart ----
    tooltips = [
        alt.Tooltip("Timestamp (Rounded Display):N", title="Rounded Time"),
        alt.Tooltip(f"{TIMESTAMP_COL}:T", title="Exact Time", format="%d/%m/%Y %H:%M:%S"),
        alt.Tooltip(f"{col}:Q", title="Value"),
    ]

    main_chart = (
        alt.Chart(df_broken)
        .mark_line(point=True, color=_OBS_COLOR)
        .encode(
            x=alt.X("Timestamp (Rounded):T", title=x_title),
            y=alt.Y(f"{col}:Q", title=y_title),
            tooltip=tooltips,
        )
        .interactive()
    )

    # ---- Optional predictions (Hourly EC only) ----
    if show_predicted and "Aggregation" in df.columns:
        # Lazy import so normal plots don't pay the cost.
        from model import make_predictions

        max_rows = df[df.get("Aggregation") == "Max"].copy()
        if not max_rows.empty and len(max_rows) >= 2:
            # last observed value/time from rounded series
            max_rows["Timestamp (Rounded)"] = pd.to_datetime(max_rows[TIMESTAMP_COL], errors="coerce").dt.floor("h")
            max_rows = max_rows.sort_values("Timestamp (Rounded)")
            series = max_rows[[col]].iloc[-7:].copy()

            last_timestamp = max_rows["Timestamp (Rounded)"].iloc[-1]
            last_value = float(series.iloc[-1][col])

            # model expects µS/cm; convert g/L <-> µS/cm if needed
            if col == "EC Value (g/l)":
                series = series * 2000
            preds = make_predictions(series, mode="Max")
            if col == "EC Value (g/l)":
                preds = [x / 2000 for x in preds]

            pred_times = [last_timestamp + pd.Timedelta(hours=i + 1) for i in range(len(preds))]
            combined_timestamps = [last_timestamp] + pred_times
            combined_values = [last_value] + preds

            predictions_line_df = pd.DataFrame({"Timestamp": combined_timestamps, col: combined_values})

            predicted_lbl = _t("legend_predicted", "Predicted")
            pred_tooltips = [
                alt.Tooltip("Timestamp:T", title=f"{predicted_lbl} Time", format="%d/%m/%Y %H:%M:%S"),
                alt.Tooltip(f"{col}:Q", title=f"{predicted_lbl} Value"),
            ]

            predictions_chart = (
                alt.Chart(predictions_line_df)
                .mark_line(color=_PRED_COLOR, strokeDash=[5, 5], point=alt.OverlayMarkDef(color=_PRED_COLOR))
                .encode(
                    x=alt.X("Timestamp:T", title=x_title),
                    y=alt.Y(f"{col}:Q", title=y_title),
                    tooltip=pred_tooltips,
                )
            )

            st.altair_chart(alt.layer(predictions_chart, main_chart), use_container_width=True)
            return

    st.altair_chart(main_chart, use_container_width=True)


def _fmt(v):
    try:
        if pd.isna(v): return "—"
        return f"{float(v):.2f}"
    except Exception:
        return "—"

def display_statistics(df: pd.DataFrame, target_col: str) -> None:
    col1, col2, col3, col4 = st.columns(4)
    if df is None or df.empty or target_col not in df.columns:
        for c, label in zip((col1, col2, col3, col4), ("Maximum","Minimum","Average","Std Dev")):
            c.metric(label=label, value="—")
        return
    s = df[target_col]
    col1.metric(label="Maximum", value=_fmt(s.max()))
    col2.metric(label="Minimum", value=_fmt(s.min()))
    col3.metric(label="Average", value=_fmt(s.mean()))
    col4.metric(label="Std Dev", value=_fmt(s.std()))
