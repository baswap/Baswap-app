import streamlit as st
import pandas as pd

st.title('BASWAP App')

st.markdown("""
This app retrieves the water quality from a buoy-based monitoring system in Vinh Long, Vietnam.
* **Data source:** [Thingspeak](https://thingspeak.mathworks.com/channels/2652379).
""")

file_path = "/workspaces/Baswap-app/combined_2025-03-02.csv"
df = pd.read_csv(file_path, parse_dates=["Timestamp (GMT+7)"])

st.sidebar.header('User Input Features')
# Sidebar column selector
col_names = list(df.columns)
col_names.remove("Timestamp (GMT+7)")
selected_cols = list(st.sidebar.multiselect('Columns', col_names, col_names))
selected_cols.insert(0, "Timestamp (GMT+7)")

# Sidebar date selector
min_date = df["Timestamp (GMT+7)"].min().date()
max_date = df["Timestamp (GMT+7)"].max().date()
date_from = st.sidebar.date_input("Date from:", min_value=min_date, max_value=max_date, value=max_date)
date_to = st.sidebar.date_input("Date to:", min_value=min_date, max_value=max_date, value=max_date)

# Filtering data
filtered_df = df[selected_cols]
filtered_df = filtered_df[(filtered_df["Timestamp (GMT+7)"].dt.date >= date_from) & 
                          (filtered_df["Timestamp (GMT+7)"].dt.date <= date_to)]


st.header('Display Values in Selected Columns and Time Range')
st.write('Data Dimension: ' + str(filtered_df.shape[0]) + ' rows and ' + str(filtered_df.shape[1]) + ' columns.')
st.dataframe(filtered_df)





