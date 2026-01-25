import pytz
import streamlit as st

# Timezone constants
GMT7 = pytz.timezone("Asia/Bangkok")
UTC = pytz.utc

# API URLs and filenames
THINGSPEAK_URL = "https://api.thingspeak.com/channels/3040691/feeds.json"
COMBINED_FILENAME = "combined_data.csv"

# Secrets from Streamlit's secrets management
# COMBINED_ID = st.secrets["FILE_ID"]
# SECRET_ACC = st.secrets["SERVICE_ACCOUNT"]

COL_NAMES = [
    "EC Value (g/l)",
    "EC Value (g/l)",
    # "EC Temperature",
    # "Battery Voltage"
]

APP_TEXTS = {
    "en": {
        "app_title": " ",
        "description": """
            This app retrieves water quality data from a buoy-based monitoring system in Vinh Long, Vietnam.
            * **Data source:** [Thingspeak](https://thingspeak.mathworks.com/channels/2652379).
        """,
        "raw_view": "Raw Data",
        "hourly_view": "Hourly Data",
        "daily_view": "Daily Data",
        "data_table": "Data Table",
        "columns_select": "Select columns to display in the table:",
        "data_dimensions": "Data Dimension (row, column):",
        "clear_cache": "Refresh Data",
        "toggle_button": "English",  
        "toggle_tooltip": "Nhấn để thay đổi ngôn ngữ", 
        "nav_overview": "Overview",
        "nav_about":    "About",
        "overall_stats_title": "Statistics",
        "axis_value":    "Value",
        "axis_timestamp":"Timestamp",
        "info_panel_title": "Information",
        "picker_label": "Pick a station",
        "picker_none": "None",
        "baswap_name": "BASWAP stations",
        "layer_baswap": "VGU Rangers",
        "layer_other": "Other stations",
        "table_station": "Station",
        "table_warning": "Warning",
        "current_measurement": "Current Measurement (g/l)",
        "legend_observed": "Observed",
        "legend_predicted": "Predicted",
        "clear_cache_tooltip": "Clear cached data and fetch the latest data from Thingspeak.",
        "map_title": "Station Map",
        "stats_max": "Maximum",
        "stats_min": "Minimum",
        "stats_avg": "Average",
        "stats_std": "Std Dev",
        "legend_pi90": "90% prediction interval",
        "legend_pi50": "50% prediction interval",
        "legend_title": "EC warning levels",
        
    },
    "vi": {
        "app_title": " ",
        "description": """
            Ứng dụng này truy xuất dữ liệu chất lượng nước từ hệ thống theo dõi trên phao ở Vĩnh Long, Việt Nam.
            * **Nguồn dữ liệu:** [Thingspeak](https://thingspeak.mathworks.com/channels/2652379).
        """,
        "raw_view": "Biểu đồ dữ liệu gốc",
        "hourly_view": "Biểu đồ dữ liệu theo giờ",
        "daily_view": "Biểu đồ dữ liệu theo ngày",
        "data_table": "Bảng Dữ Liệu",
        "columns_select": "Chọn các cột để hiển thị trong bảng:",
        "data_dimensions": "Kích thước dữ liệu (hàng, cột):",
        "clear_cache": "Cập nhật dữ liệu",
        "toggle_button": "Tiếng Việt", 
        "toggle_tooltip": "Click to change language",
        "nav_overview": "Tổng quan",
        "nav_about":    "Giới thiệu",
        "overall_stats_title": "Thống kê",
        "axis_value":    "Giá trị",
        "axis_timestamp":"Thời gian",
        "info_panel_title": "Thông tin",
        "picker_label": "Chọn trạm",
        "picker_none": "Không chọn",
        "baswap_name": "Trạm BASWAP",
        "layer_baswap": "VGU Rangers",
        "layer_other": "Các trạm khác",
        "table_station": "Trạm",
        "table_warning": "Cảnh báo",
        "current_measurement": "Chỉ số hiện tại (g/l)",
        "legend_observed": "Dữ liệu thực đo",
        "legend_predicted": "Dự báo",
        "clear_cache_tooltip": "Xóa bộ nhớ đệm và tải lại dữ liệu mới nhất từ Thingspeak.",
        "map_title": "Bản đồ trạm đo mặn",
        "stats_max": "Giá trị lớn nhất",
        "stats_min": "Giá trị nhỏ nhất",
        "stats_avg": "Giá trị trung bình",
        "stats_std": "Độ lệch chuẩn",
        "legend_pi90": "Khoảng dự báo 90%",
        "legend_pi50": "Khoảng dự báo 50%",
        "legend_title": "Mức cảnh báo EC",
    }
}

SIDE_TEXTS = {
    "en": {
        "sidebar_header": "## Graph Settings",
        "sidebar_description": (
            "Use the options below to customize how the data is shown in the charts.\n\n"
            "You can choose what measurement to analyze, set a date range, and select which summary statistics to display in the hourly and daily view."
        ),
        "sidebar_choose_column": "Choose a column to plot:",
        "sidebar_first_day": "First Recorded Day",
        "sidebar_today": "Last Recorded Day",
        "sidebar_start_date": "Start Date (From):",
        "sidebar_end_date": "End Date (To):",
        "sidebar_summary_stats": "Choose summary statistics to calculate (applied in Hourly and Daily views):"
    },
    "vi": {
        "sidebar_header": "## Điều chỉnh biểu đồ",
        "sidebar_description": (
            "Sử dụng các tùy chọn bên dưới để tùy chỉnh cách dữ liệu được hiển thị trong các biểu đồ.\n\n"
            "Bạn có thể chọn chỉ số cần phân tích, khoảng thời gian, và chọn các thống kê để hiển thị trong biểu đồ theo giờ và theo ngày."
        ),
        "sidebar_choose_column": "Chọn cột để lập biểu đồ:",
        "sidebar_first_day": "Ngày đo đầu tiên",
        "sidebar_today": "Ngày đo gần nhất",
        "sidebar_start_date": "Ngày bắt đầu (Từ):",
        "sidebar_end_date": "Ngày kết thúc (Đến):",
        "sidebar_summary_stats": "Chọn các thống kê tóm tắt để tính (áp dụng cho chế độ theo giờ và ngày):"
    }
}



ABOUT_HTML_VI = r"""
<style>
.about { line-height: 1.6; }
.about h2 { font-size: 1.12rem; margin: 0 0 .45rem; }              /* default (Contact) */
.about h2.big { font-size: 1.55rem; line-height: 1.3;               /* bigger for 3 heads */
                margin: 1.2rem 0 .65rem; }
.about .section { margin-bottom: 1.35rem; }                          /* more space between sections */
.about ul { margin: .25rem 0 .9rem 1.1rem; }
.about li { margin: .2rem 0; }
.about .email { margin-top: .6rem; }
/* NEW: side-by-side images row */
.about .hero { display:flex; gap:12px; margin:.8rem 0 1.2rem; }
.about .hero img { width:50%; height:auto; border-radius:8px; }
@media (max-width: 640px){ .about .hero { flex-direction:column; } .about .hero img{ width:100%; } }
</style>

<div class="about">
  <div class="section">
    <h2 class="big">Giới thiệu chung</h2>
    <p>VGU Rangers được thành lập nhằm đáp ứng nhu cầu giám sát và quản lý chất lượng nước trong tự nhiên cũng như công nghiệp, đặc biệt tại Đồng bằng sông Cửu Long (ĐBSCL) – vùng trọng điểm sản xuất nông nghiệp, thủy sản và đồng thời là khu vực nhạy cảm trước biến đổi khí hậu và xâm nhập mặn. Hệ thống khai thác sức mạnh của IoT (Internet of Things) trong thu thập dữ liệu thời gian thực từ mạng lưới các trạm cảm biến thủy văn (sensor nodes), kết hợp với trí tuệ nhân tạo (AI) để xử lý, phân tích, và dự báo sớm các nguy cơ tiềm ẩn. Đây là bước tiến quan trọng trong việc chuyển đổi số quản lý tài nguyên nước, giúp nâng cao hiệu quả cảnh báo, giảm thiểu rủi ro và tối ưu hóa chi phí đầu tư cho hệ thống quan trắc.</p>
  </div>

  <!-- HERO IMAGES: placed right above 'Mục tiêu' -->
  <div class="hero">
    <img src="__IMG1__" alt="VGU Rangers image 1">
    <img src="__IMG2__" alt="VGU Rangers image 2">

  </div>

  <div class="section">
    <h2 class="big">Mục tiêu</h2>
    <ul>
      <li><b>Giám sát thông minh và liên tục:</b> Thu thập dữ liệu chất lượng nước (pH, độ đục, DO, nhiệt độ, amoni, nitrat…) theo thời gian thực, phục vụ đánh giá trạng thái môi trường nước.</li>
      <li><b>Dự báo và cảnh báo sớm:</b> Ứng dụng AI để dự báo chất lượng nước trong tương lai gần, từ đó phát tín hiệu cảnh báo kịp thời.</li>
      <li><b>Liên kết và mở rộng không gian:</b> Xây dựng mạng lưới trạm quan và liên kết dữ liệu để cung cấp bản đồ chất lượng nước theo vùng.</li>
    </ul>
  </div>

  <div class="section">
    <h2 class="big">Tầm nhìn</h2>
    <p>VGU Rangers hướng tới trở thành hệ thống giám sát – dự báo chất lượng nước thông minh cho toàn ĐBSCL, có khả năng nhân rộng ra các lưu vực khác. Với nền tảng AIoT, hệ thống không chỉ dừng ở thu thập và hiển thị dữ liệu, mà còn cung cấp giải pháp dự báo sớm, quản lý chủ động và tối ưu hóa tài nguyên nước. Đây là công cụ góp phần nâng cao khả năng chống chịu của con người trước các thách thức môi trường, biến đổi khí hậu và rủi ro nguồn nước trong tương lai.</p>
  </div>

  <div class="section">
    <h2>Kết nối với chúng tôi</h2>
    <p class="email">Địa chỉ email: <a href="mailto:baswapvgu2025@gmail.com">baswapvgu2025@gmail.com</a></p>
  </div>
</div>
"""

ABOUT_HTML_EN = r"""
<style>
.about { line-height: 1.6; }
.about h2 { font-size: 1.12rem; margin: 0 0 .45rem; }              /* default (Contact) */
.about h2.big { font-size: 1.55rem; line-height: 1.3;               /* bigger for 3 heads */
                margin: 1.2rem 0 .65rem; }
.about .section { margin-bottom: 1.35rem; }                          /* more space between sections */
.about ul { margin: .25rem 0 .9rem 1.1rem; }
.about li { margin: .2rem 0; }
.about .email { margin-top: .6rem; }
/* NEW: side-by-side images row */
.about .hero { display:flex; gap:12px; margin:.8rem 0 1.2rem; }
.about .hero img { width:50%; height:auto; border-radius:8px; }
@media (max-width: 640px){ .about .hero { flex-direction:column; } .about .hero img{ width:100%; } }
</style>

<div class="about">
  <div class="section">
    <h2 class="big">Overview</h2>
    <p>VGU Rangers was established to address the need for monitoring and managing water quality in both natural and industrial contexts, particularly in the Mekong Delta (VMD) – Vietnam’s key hub for agriculture and aquaculture, yet also a highly vulnerable region to climate change and salinity intrusion. The system leverages the power of a network of the Internet of Things (IoT) to collect real-time data from hydrological sensor stations, combined with Artificial Intelligence (AI) to process, analyze, and forecast potential risks at an early stage. This marks an important step in the digital transformation of water resource management, helping to improve early warning efficiency, reduce risks, and optimize investment costs for monitoring systems.</p>
  </div>

  <!-- HERO IMAGES: placed right above 'Objectives' -->
  <div class="hero">
    <img src="__IMG1__" alt="VGU Rangers image 1">
    <img src="__IMG2__" alt="VGU Rangers image 2">
  </div>

  <div class="section">
    <h2 class="big">Objectives</h2>
    <ul>
      <li><b>Intelligent and continuous monitoring:</b> Collect real-time water quality data (pH, turbidity, dissolved oxygen, temperature, ammonium, nitrate, etc.) to assess the state of aquatic environments.</li>
      <li><b>Forecasting and early warning:</b> Apply AI to predict near-future water quality measurements, and generate timely alerts.</li>
      <li><b>Data integration and spatial expansion:</b> Develop a network of monitoring stations and link data to provide regional water quality maps.</li>
    </ul>
  </div>

  <div class="section">
    <h2 class="big">Vision</h2>
    <p>VGU Rangers aims to become an intelligent water quality monitoring and forecasting system for the entire Mekong Delta, with the potential to be expanded to other river basins. Built on an AIoT foundation, the system goes beyond simple data collection and visualization, offering predictive insights, proactive management, and optimized water resource utilization. This serves as a tool to strengthen human resilience against environmental challenges, climate change, and water-related risks in the future.</p>
  </div>

  <div class="section">
    <h2>Contact us</h2>
    <p class="email">Email: <a href="mailto:baswapvgu2025@gmail.com">baswapvgu2025@gmail.com</a></p>
  </div>
</div>
"""



def get_about_html(lang: str) -> str:
    """Return localized About page HTML."""
    return ABOUT_HTML_EN if (lang or "").lower().startswith("en") else ABOUT_HTML_VI
