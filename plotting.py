import streamlit as st
import altair as alt
import pandas as pd
from model import LITModel, LSTMTimeseries
import pytorch_lightning as pl
import numpy as np
import torch
from model import make_predictions


# -------- NEW: break the line across large time gaps by injecting NaNs --------
def _inject_nans_for_gaps(
    df: pd.DataFrame,
    time_col: str,
    value_col: str,
    *,
    cat_col: str | None,                 # e.g. "Aggregation" (series)
    max_gap: pd.Timedelta,               # e.g. pd.Timedelta(hours=3)
    display_col: str | None = None,      # optional label column used in tooltip
    display_fmt: str | None = None
) -> pd.DataFrame:
    """
    Return df with extra rows (value = NaN) inserted at the midpoint of any
    time gap larger than `max_gap`. Altair stops drawing a line at NaNs.
    Gaps are computed per `cat_col` (series), if provided.
    """
    d = df.copy()
    d[time_col] = pd.to_datetime(d[time_col])

    groups = [(None, d)] if not cat_col else d.groupby(cat_col, dropna=False)
    pieces = []

    for key, g in groups:
        g = g.sort_values(time_col)
        deltas = g[time_col].diff()
        gap_mask = deltas > max_gap
        if gap_mask.any():
            prev_times = g[time_col].shift(1)[gap_mask]
            next_times = g[time_col][gap_mask]
            mid_times = prev_times + (next_times - prev_times) / 2

            fill = pd.DataFrame({
                time_col: mid_times.values,
                value_col: np.nan
            })
            if cat_col:
                fill[cat_col] = key
            # optional display label for tooltips (not strictly required)
            if display_col and display_fmt:
                fill[display_col] = pd.to_datetime(fill[time_col]).dt.strftime(display_fmt)

            pieces.append(pd.concat([g, fill], ignore_index=True))
        else:
            pieces.append(g)

    out = pd.concat(pieces, ignore_index=True).sort_values(time_col)
    return out
# -----------------------------------------------------------------------------


def plot_line_chart(df, col, resample_freq="None"):
    if col not in df.columns:
        st.error(f"Column '{col}' not found in DataFrame.")
        return

    df_filtered = df.copy()

    color_scale = alt.Scale(
        domain=["Raw", "Max", "Min", "Median"],
        range=["orange", "red", "blue", "green"]
    )

    if resample_freq == "None":
        # (You may not be using the Raw view anymore, but this keeps it safe.)
        df_filtered["Aggregation"] = "Raw"

        # --- NEW: break raw line across gaps (>30 min) ---
        df_broken = _inject_nans_for_gaps(
            df_filtered,
            time_col="Timestamp (GMT+7)",
            value_col=col,
            cat_col="Aggregation",
            max_gap=pd.Timedelta(minutes=30)
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
                    alt.Tooltip(f"{col}:Q", title="Value")
                ],
            )
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)

    else:
        # Create a rounded timestamp based on resample frequency.
        if resample_freq == "Hour":
            df_filtered["Timestamp (Rounded)"] = df_filtered["Timestamp (GMT+7)"].dt.floor('h')
        elif resample_freq == "Day":
            df_filtered["Timestamp (Rounded)"] = df_filtered["Timestamp (GMT+7)"].dt.floor('d')
        else:
            df_filtered["Timestamp (Rounded)"] = df_filtered["Timestamp (GMT+7)"]

        df_filtered["Timestamp (Rounded Display)"] = df_filtered["Timestamp (Rounded)"].dt.strftime(
            r"%H:%M:%S" if resample_freq == "Hour" else "%d/%m/%Y"
        )

        # --- NEW: choose a gap threshold and inject NaNs so the line breaks ---
        if resample_freq == "Hour":
            gap = pd.Timedelta(hours=3)
            disp_fmt = "%H:%M:%S"
        elif resample_freq == "Day":
            gap = pd.Timedelta(days=3)
            disp_fmt = "%d/%m/%Y"
        else:
            gap = pd.Timedelta(hours=1)
            disp_fmt = "%d/%m/%Y %H:%M:%S"

        df_broken = _inject_nans_for_gaps(
            df_filtered,
            time_col="Timestamp (Rounded)",
            value_col=col,
            cat_col="Aggregation" if "Aggregation" in df_filtered.columns else None,
            max_gap=gap,
            display_col="Timestamp (Rounded Display)",
            display_fmt=disp_fmt,
        )

        # Build the main chart for all data (with gaps broken).
        main_chart = (
            alt.Chart(df_broken)
            .mark_line(point=True)
            .encode(
                x=alt.X("Timestamp (Rounded):T", title="Timestamp"),
                y=alt.Y(f"{col}:Q", title="Value"),
                color=alt.Color("Aggregation:N", title="Aggregation", scale=color_scale),
                tooltip=[
                    alt.Tooltip("Timestamp (Rounded Display):N", title="Rounded Time"),
                    alt.Tooltip("Timestamp (GMT+7):T", title="Exact Time", format="%d/%m/%Y %H:%M:%S"),
                    alt.Tooltip(f"{col}:Q", title="Value"),
                    alt.Tooltip("Aggregation:N", title="Aggregation")
                ]
            )
            .interactive()
        )

        if resample_freq == "Hour" and col in ["EC Value (us/cm)", "EC Value (g/l)"]:
            # Filter the "Max" aggregation points.
            max_data = df_filtered[df_filtered["Aggregation"] == "Max"]

            # Extract only the numeric values from the last 7 points.
            max_values_numeric = max_data[[col]].iloc[-7:]

            # Get the last timestamp and last value from the max data.
            last_timestamp = max_data["Timestamp (Rounded)"].iloc[-1]
            last_value = max_values_numeric.iloc[-1][col]

            if (col == "EC Value (g/l)"):
                max_values_numeric = max_values_numeric * 2000

            # Predictions (external function)
            predictions_list = make_predictions(max_values_numeric, mode="Max")

            if (col == "EC Value (g/l)"):
                predictions_list = [x/2000 for x in predictions_list]

            # Timestamps for predictions
            prediction_timestamps = [
                last_timestamp + pd.Timedelta(hours=i+1) for i in range(len(predictions_list))
            ]

            # Connect from last max point to predictions
            combined_timestamps = [last_timestamp] + prediction_timestamps
            combined_values = [last_value] + predictions_list

            predictions_line_df = pd.DataFrame({
                "Timestamp": combined_timestamps,
                col: combined_values,
                "Aggregation": "Predicted"
            })

            predictions_chart = (
                alt.Chart(predictions_line_df)
                .mark_line(color='red', strokeDash=[5, 5], point=alt.OverlayMarkDef(color="red"))
                .encode(
                    x=alt.X("Timestamp:T", title="Timestamp"),
                    y=alt.Y(f"{col}:Q", title="Value"),
                    tooltip=[
                        alt.Tooltip("Timestamp:T", title="Predicted Time", format="%d/%m/%Y %H:%M:%S"),
                        alt.Tooltip(f"{col}:Q", title="Predicted Value"),
                        alt.Tooltip("Aggregation:N", title="Aggregation")
                    ]
                )
            )

            combined_chart = alt.layer(predictions_chart, main_chart).resolve_scale(
                color='independent'
            )
            st.altair_chart(combined_chart, use_container_width=True)
        else:
            st.altair_chart(main_chart, use_container_width=True)


def display_statistics(df, target_col):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="Maximum", value=f"{df[target_col].max():.2f}")
    col2.metric(label="Minimum", value=f"{df[target_col].min():.2f}")
    col3.metric(label="Average", value=f"{df[target_col].mean():.2f}")
    col4.metric(label="Std Dev", value=f"{df[target_col].std():.2f}")
