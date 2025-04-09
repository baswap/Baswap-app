import streamlit as st
from data import combined_data_retrieve, thingspeak_retrieve
from sidebar import sidebar_inputs
from aggregation import filter_data, apply_aggregation
from plotting import plot_line_chart, display_statistics
from config import COL_NAMES

def display_view(df, target_col, view_title, resample_freq, selected_cols, agg_functions):
    st.subheader(view_title)
    if resample_freq == "None":
        view_df = df.copy()
    else:
        view_df = apply_aggregation(df, selected_cols, target_col, resample_freq, agg_functions)
    plot_line_chart(view_df, target_col, resample_freq)

def main():
    st.set_page_config(page_title="BASWAP-APP", page_icon="💧", layout="wide")
    st.title("BASWAP APP")
    st.markdown("""
    This app retrieves water quality data from a buoy-based monitoring system in Vinh Long, Vietnam.
    * **Data source:** [Thingspeak](https://thingspeak.mathworks.com/channels/2652379).
    """)

    # Data retrieval
    df = combined_data_retrieve()
    df = thingspeak_retrieve(df)

    col_names = COL_NAMES

    # Sidebar inputs
    date_from, date_to, target_col, agg_functions = sidebar_inputs(df)
    filtered_df = filter_data(df, date_from, date_to)

    # Display statistics
    display_statistics(filtered_df, target_col)

    # Display views: Raw, Hourly, Daily
    display_view(filtered_df, target_col, f"Raw Data View of {target_col}", resample_freq="None", selected_cols=col_names, agg_functions=agg_functions)
    display_view(filtered_df, target_col, f"Hourly Data View of {target_col}", resample_freq="Hour", selected_cols=col_names, agg_functions=agg_functions)
    display_view(filtered_df, target_col, f"Daily Data View of {target_col}", resample_freq="Day", selected_cols=col_names, agg_functions=agg_functions)

    # Data table section with column selector
    st.subheader("🔍 Data Table")

    # Column selection for plotting or viewing
    selected_table_cols = st.multiselect(
        "Select columns to display in the table:",
        options=col_names,
        default=col_names
    )

    st.write(f"Data Dimension: {filtered_df.shape[0]} rows and {len(selected_table_cols)} columns.")
    # Show the filtered table
    st.dataframe(filtered_df[selected_table_cols], use_container_width=True)

    st.button("Clear Cache", help="This clears all cached data, ensuring the app fetches the latest available information.", on_click=st.cache_data.clear)

if __name__ == "__main__":
    main()
