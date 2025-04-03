import streamlit as st
import altair as alt
import pandas as pd

def plot_line_chart(df, col, resample_freq="None"):
    if col not in df.columns:
        st.error(f"Column '{col}' not found in DataFrame.")
        return
    
    df_filtered = df.copy()

    if resample_freq == "None":
        df_filtered["Aggregation"] = "Raw"
        chart = (
            alt.Chart(df_filtered)
            .mark_line(point=True)
            .encode(
                x=alt.X("Timestamp (GMT+7):T", title="Timestamp"),
                y=alt.Y(f"{col}:Q", title="Value"),
                color=alt.Color("Aggregation:N", title="Aggregation"),
                tooltip=[
                    alt.Tooltip("Timestamp (GMT+7):T", title="Exact Time", format="%d/%m/%Y %H:%M:%S"),
                    alt.Tooltip(f"{col}:Q", title="Value")
                ],
            )
            .interactive()
        )
    else:
        if resample_freq == "Hour":
            df_filtered["Timestamp (Rounded)"] = df_filtered["Timestamp (GMT+7)"].dt.floor('h')
        elif resample_freq == "Day":
            df_filtered["Timestamp (Rounded)"] = df_filtered["Timestamp (GMT+7)"].dt.floor('d')
        else:
            df_filtered["Timestamp (Rounded)"] = df_filtered["Timestamp (GMT+7)"]

        df_filtered["Timestamp (Rounded Display)"] = df_filtered["Timestamp (Rounded)"].dt.strftime(
            r"%H:%M:%S" if resample_freq == "Hour" else "%d/%m/%Y"
        )

        chart = (
            alt.Chart(df_filtered)
            .mark_line(point=True)
            .encode(
                x=alt.X("Timestamp (Rounded):T", title="Timestamp"),
                y=alt.Y(f"{col}:Q", title="Value"),
                color=alt.Color("Aggregation:N", title="Aggregation"),
                tooltip=[
                    alt.Tooltip("Timestamp (Rounded Display):N", title="Rounded Time"),
                    alt.Tooltip("Timestamp (GMT+7):T", title="Exact Time", format="%d/%m/%Y %H:%M:%S"),
                    alt.Tooltip(f"{col}:Q", title="Value"),
                    alt.Tooltip("Aggregation:N", title="Aggregation")
                ]
            )
            .interactive()
        )

    st.altair_chart(chart, use_container_width=True)

def display_statistics(df, target_col):
    st.subheader("**📊 Overall Statistics (Raw Data)**")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="Maximum", value=f"{df[target_col].max():.2f}")
    col2.metric(label="Minimum", value=f"{df[target_col].min():.2f}")
    col3.metric(label="Average", value=f"{df[target_col].mean():.2f}")
    col4.metric(label="Std Dev", value=f"{df[target_col].std():.2f}")
