import pytz
import streamlit as st

# Timezone constants
GMT7 = pytz.timezone("Asia/Bangkok")
UTC = pytz.utc

# API URLs and filenames
THINGSPEAK_URL = "https://api.thingspeak.com/channels/2652379/feeds.json"
COMBINED_FILENAME = "combined_data.csv"

# Secrets from Streamlit's secrets management
COMBINED_ID = st.secrets["FILE_ID"]
SECRET_ACC = st.secrets["SERVICE_ACCOUNT"]

COL_NAMES = [
    "EC Value (us/cm)",
    "EC Value (g/l)",
    "EC Temperature",
    "Battery Voltage"
]

APP_TEXTS = {
    "en": {
        "toggle_button": "Tiếng Việt",
        "toggle_tooltip": "Nhấn để chuyển sang tiếng Việt",
        "app_title": "BASWAP APP",
        "description": """
            This app retrieves water quality data from a buoy-based monitoring system in Vinh Long, Vietnam.
            * **Data source:** [Thingspeak](https://thingspeak.mathworks.com/channels/2652379).
        """,
        "measurement_label": "Measurement",
        "first_day_button": "First Recorded Day",
        "today_button": "Latest Recorded Day",
        "start_date_label": "Start Date",
        "end_date_label": "End Date",
        "summary_stats_label": "Summary Statistics",
        "graph_settings_title": "⚙️ Graph Settings",
        "raw_tab": "Raw",
        "hourly_tab": "Hourly",
        "daily_tab": "Daily",
        "chart_header_prefix": "📈",
        "data_table": "🔍 Data Table",
        "columns_select": "Select columns to display in the table:",
        "data_dimensions": "Data Dimensions (rows, columns):",
        "clear_cache": "Clear Cache",
        "marker_tooltip": "BASWAP Buoy"
    },
    "vi": {
        "toggle_button": "English",
        "toggle_tooltip": "Click to switch to English",
        "app_title": "ỨNG DỤNG BASWAP",
        "description": """
            Ứng dụng này truy xuất dữ liệu chất lượng nước từ hệ thống theo dõi trên phao ở Vĩnh Long, Việt Nam.
            * **Nguồn dữ liệu:** [Thingspeak](https://thingspeak.mathworks.com/channels/2652379).
        """,
        "measurement_label": "Chỉ số",
        "first_day_button": "Ngày đo đầu tiên",
        "today_button": "Ngày đo gần nhất",
        "start_date_label": "Ngày bắt đầu",
        "end_date_label": "Ngày kết thúc",
        "summary_stats_label": "Thống kê tóm tắt",
        "graph_settings_title": "⚙️ Điều chỉnh biểu đồ",
        "raw_tab": "Gốc",
        "hourly_tab": "Theo giờ",
        "daily_tab": "Theo ngày",
        "chart_header_prefix": "📈",
        "data_table": "🔍 Bảng Dữ Liệu",
        "columns_select": "Chọn các cột để hiển thị trong bảng:",
        "data_dimensions": "Kích thước dữ liệu (hàng, cột):",
        "clear_cache": "Xóa Bộ Nhớ Cache",
        "marker_tooltip": "Phao BASWAP"
    }
}

SIDE_TEXTS = {
    "en": {
        "sidebar_header": "## ⚙️ Graph Settings",
        "sidebar_description": (
            "Use the options below to customize how the data is shown in the charts.\n\n"
            "You can choose what measurement to analyze, set a date range, and select which summary statistics to display in the hourly and daily view."
        ),
        "sidebar_choose_column": "Choose a column to plot:",
        "sidebar_first_day": "First Recorded Day",
        "sidebar_today": "Latest Recorded Day",
        "sidebar_start_date": "Start Date (From):",
        "sidebar_end_date": "End Date (To):",
        "sidebar_summary_stats": "Choose summary statistics to calculate (applied in Hourly and Daily views):"
    },
    "vi": {
        "sidebar_header": "## ⚙️ Điều chỉnh biểu đồ",
        "sidebar_description": (
            "Sử dụng các tùy chọn bên dưới để tùy chỉnh cách dữ liệu được hiển thị trong các biểu đồ.\n\n"
            "Bạn có thể chọn chỉ số cần phân tích, khoảng thời gian, và chọn các thống kê để hiển thị trong biểu đồ theo giờ và theo ngày."
        ),
        "sidebar_choose_column": "Chọn cột để lập biểu đồ:",
        "sidebar_first_day": "Ngày đo đầu tiên",
        "sidebar_today": "Ngày đo gần nhất",
        "sidebar_start_date": "Ngày bắt đầu (Từ):",
        "sidebar_end_date": "Ngày kết thúc (Đến):
