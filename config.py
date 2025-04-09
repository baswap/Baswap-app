import pytz
import streamlit as st

# Timezone constants
GMT7 = pytz.timezone("Asia/Bangkok")
UTC = pytz.utc

# API URLs and filenames
THINGSPEAK_URL = "https://api.thingspeak.com/channels/2652379/feeds.json"
COMBINED_FILENAME = "combined_data.csv"

# Secrets from Streamlit's secrets management
# COMBINED_ID = st.secrets["FILE_ID"]
# SECRET_ACC = st.secrets["SERVICE_ACCOUNT"]
SECRET_ACC = "ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsCiAgInByb2plY3RfaWQiOiAiYmFzd2FwIiwKICAicHJpdmF0ZV9rZXlfaWQiOiAiMThhMjVlNDRiNDIxMjQxMmYwMDQ0YzYyZTliNGY4ZWIzMmM5ZDdhNCIsCiAgInByaXZhdGVfa2V5IjogIi0tLS0tQkVHSU4gUFJJVkFURSBLRVktLS0tLVxuTUlJRXZnSUJBREFOQmdrcWhraUc5dzBCQVFFRkFBU0NCS2d3Z2dTa0FnRUFBb0lCQVFDWklnM3VwWHdoUWdRM1xuWFpzVnQzRCtXNHpYdFV3U1J1ejZVWFhlQUZIcDR5Wm8vbkpYRE5sRzdPaDdIWW1oSHlGeHlUc2N3b09hSVNQR1xuOER1R2w1R3Ewd0ZQcDJ6V3pTNXlYb3FMdEp3Q2QvU0xTbjc2cDJBRlZtZUg5cXJDcVkrUXhIYnlWMnlPTml0RFxuTEVqeVlPNEFCQ20rdU53UXZrTi9Sc1RDaHlOWEhlYUlPSUp1MEIrbHd4ejdhVGxWWkhOalMzT3BGaFgycE80Vlxub3VxMEh6eUdzQTZYQ3FVM3ZoOHlJeU1CbEd3THpSRUVIeUluMytpbHZkaS94OGYvSEZnODlHQll6VDlWQjNYWFxueU1UTksySU5IV2RxbW54WENSdUNXSEIxRmxObVd5STAyVElCb0Q3cXplYjBIb1lKTldYSWJzNVY0N2tKYmxOaFxuTkh6dU9sTFBBZ01CQUFFQ2dnRUFDQ0dleThWTnloWlBVd0ZOY3VIQ3hqN21RNjRFMUJPZ0VjcXhqNUJFeVQ2ZVxuazRTdlhaLzVDYU1hMVM3RVdDSG5ETHU2djlRMFdNTFp1MzZXS3BkeHpMaFhvWHNxZEYyQTBlSGpTWGZWc092ZFxudUdmRVJsc001anVvVTdmdGFWakhudEJQNEo1enpUbGpJclgvU1orTUE4UTAwMFBOcTdYdXI1dDZaem4xem5KYVxuNjY3eFhHMzQvV1dTQTB5THZ1K1RsWUZ0WFRpNmhLUlNQVnNSMVhwVk1BdWdEdzArdzVYUmQxY3lvUFJsY1dReFxuSDRrVDFPem9UT2htU1lCWHFrd2tVd3l5c291NldRY3ZEcUdaTldaeDY0WUthRUsremlyU3p2UUhweDlidkxiOFxuQW91NUkzbXlXR3JiNkd2V09hVXdHUGxFaUpWbmdhZ1lVUFNFbWVydGdRS0JnUURXUUROeTlDTFlRZDhsSTNSRFxua1RuejdPSldoK0lWN3IwQUQyK2ZGeXlldlZLNmExbXdIVlFnUkpoNkNCcHh6c2ZxU0hQcTZodkxuem1jcWZYb1xuZ2NEcTIrTDBMOTJTdkpyd2FyQTRFVnJKRUVxZ25tOHlSL2RGdk1tcGMzSkFOWDJDMjVJM2NGR1oyNXBCMEVpeFxucm82M1kyQ3hEcEhINHV3RTJiRm1wMTJUSndLQmdRQzIrUVhkeS9DTzhLWTM3VC9GUUs5UW1NT0lWazhYTFJFMVxuSEN4SysvcW95eEgrRFVtS2hjWUZCWjhjNWlDa2VyRm1CSHRNa3d1RzBxMHg4TmhDd01GWEUwOWhuMWQ2ejZGNlxuL21pWktucTV6SkdheU5qM21kWlMvaVBGbVBXcXVjbVBXTFZZeVpoZVNINFJMd2toQzRwT0E5bnJ0VHBsSjdjZ1xuakhQM00zbnNHUUtCZ1FETU9XcFJXeEdUM2taY1drMUswclhSSTY0a0dXYVN6WHp1LzhmQWVCQ2FSNUVDRGEzeVxuU0NLV2w0eFlWajBPMnJLSlNnTGttNzllK3ltcGdnRGJYa09NRzRsY2hmdkpFV3NIWEVzWlJzR3BBcFNBUWtWd1xuUWxVYjduYXp4VTNVa3FoUEFnbUFPdG90dEx4M201aVBkZnFvS0Z4VXFiU2dPbGdMejQ1Z2NZeXE1UUtCZ0ZESFxuNUtVbGt0RW93ZG5UTHVKaFNvVmt6SDcyeS9oSmQxMWhVTlRTSnJvNjNYaXlXUk9GT0FXams3bm9oK1RXSGxnU1xuQm5XcVBkNktTTmpSb2tqbVhQV2FtdU5ZdkFDR2hwNk1qNVYvd2FzaCsrN0FXYm9HK3k2czhSSWVFK2dLR2tqbFxuT3pzMTFjVmFiLzRhTEFlZzFyRFcxbkZRRTdYeE1OSjM4QUxsZ1NDUkFvR0JBTks2SnJFb0JhVzgrdCtnY3hQOVxuUXQvS0FFWW1xKy81d1YzOGJGbGhvSDhCS0swTURwVTZUUDc2VnR6aUVpcDFxSjY3VFg2bi9idVZ6aWJJai85SVxuZ1hJRFNlRDVWWHhHdkQ3cFArUm9kOTZ2cWNNREgycUF4aEs1WDk4S0FCRlZnR2tSQ2pxaXBhdStrOVpyOU1OL1xueHZieUU1Q3JqY1I5aEtMQndTSjJ3cDlJXG4tLS0tLUVORCBQUklWQVRFIEtFWS0tLS0tXG4iLAogICJjbGllbnRfZW1haWwiOiAiYmFzd2FwLWRyaXZlQGJhc3dhcC5pYW0uZ3NlcnZpY2VhY2NvdW50LmNvbSIsCiAgImNsaWVudF9pZCI6ICIxMTMzOTQ5MjM5MjM1ODY4Mjg3ODQiLAogICJhdXRoX3VyaSI6ICJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20vby9vYXV0aDIvYXV0aCIsCiAgInRva2VuX3VyaSI6ICJodHRwczovL29hdXRoMi5nb29nbGVhcGlzLmNvbS90b2tlbiIsCiAgImF1dGhfcHJvdmlkZXJfeDUwOV9jZXJ0X3VybCI6ICJodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9vYXV0aDIvdjEvY2VydHMiLAogICJjbGllbnRfeDUwOV9jZXJ0X3VybCI6ICJodHRwczovL3d3dy5nb29nbGVhcGlzLmNvbS9yb2JvdC92MS9tZXRhZGF0YS94NTA5L2Jhc3dhcC1kcml2ZSU0MGJhc3dhcC5pYW0uZ3NlcnZpY2VhY2NvdW50LmNvbSIsCiAgInVuaXZlcnNlX2RvbWFpbiI6ICJnb29nbGVhcGlzLmNvbSIKfQo="
COMBINED_ID = "19Ku74Co8_V-Y-Wwan5Qf6cfS4QlUCl72"

COL_NAMES = [
    "EC Value (us/cm)",
    "EC Value (g/l)",
    "EC Temperature",
    "Battery Voltage"
]

APP_TEXTS = {
    "en": {
        "app_title": "BASWAP APP",
        "description": """
            This app retrieves water quality data from a buoy-based monitoring system in Vinh Long, Vietnam.
            * **Data source:** [Thingspeak](https://thingspeak.mathworks.com/channels/2652379).
        """,
        "raw_view": "Raw Data View of",
        "hourly_view": "Hourly Data View of",
        "daily_view": "Daily Data View of",
        "data_table": "🔍 Data Table",
        "columns_select": "Select columns to display in the table:",
        "data_dimensions": "Data Dimension (row, column):",
        "clear_cache": "Clear Cache",
        "toggle_button": "Tiếng Việt",  # Label to switch language to Vietnamese.
        "toggle_tooltip": "Nhấn để thay đổi ngôn ngữ"  # Tooltip in Vietnamese.
    },
    "vi": {
        "app_title": "ỨNG DỤNG BASWAP",
        "description": """
            Ứng dụng này truy xuất dữ liệu chất lượng nước từ hệ thống theo dõi trên phao ở Vĩnh Long, Việt Nam.
            * **Nguồn dữ liệu:** [Thingspeak](https://thingspeak.mathworks.com/channels/2652379).
        """,
        "raw_view": "Biểu đồ dữ liệu gốc cho",
        "hourly_view": "Biểu đồ dữ liệu theo giờ cho",
        "daily_view": "Biểu đồ dữ liệu theo ngày cho",
        "data_table": "🔍 Bảng Dữ Liệu",
        "columns_select": "Chọn các cột để hiển thị trong bảng:",
        "data_dimensions": "Kích thước dữ liệu (hàng, cột):",
        "clear_cache": "Xóa Bộ Nhớ Cache",
        "toggle_button": "English",  # Label to switch language to English.
        "toggle_tooltip": "Click to change language"  # Tooltip in English.
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
        "sidebar_today": "Today",
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
        "sidebar_today": "Hôm nay",
        "sidebar_start_date": "Ngày bắt đầu (Từ):",
        "sidebar_end_date": "Ngày kết thúc (Đến):",
        "sidebar_summary_stats": "Chọn các thống kê tóm tắt để tính (áp dụng cho chế độ theo giờ và ngày):"
    }
}