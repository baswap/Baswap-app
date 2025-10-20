import streamlit as st
import pandas as pd
from datetime import timedelta
import base64, mimetypes
from pathlib import Path

from config import get_about_html
from aggregation import filter_data, apply_aggregation
from plotting import plot_line_chart, display_statistics

def settings_panel(side_texts, first_date, last_date, default_from, default_to, COL_NAMES):
    st.markdown(side_texts["sidebar_header"])
    st.markdown(side_texts["sidebar_description"])
    st.selectbox(side_texts["sidebar_choose_column"], COL_NAMES, key="target_col")

    c1, c2 = st.columns(2)
    if c1.button(side_texts["sidebar_first_day"]):
        st.session_state.date_from = first_date
    if c2.button(side_texts["sidebar_today"]):
        st.session_state.date_from = default_to
        st.session_state.date_to = default_to

    if st.session_state.get("date_from") is None:
        st.session_state.date_from = default_from
    if st.session_state.get("date_to") is None:
        st.session_state.date_to = last_date

    st.date_input(
        side_texts["sidebar_start_date"],
        min_value=first_date, max_value=last_date, key="date_from"
    )
    st.date_input(
        side_texts["sidebar_end_date"],
        min_value=first_date, max_value=last_date, key="date_to"
    )

    # set default only once; do NOT reset every rerun
    if "agg_stats" not in st.session_state:
        st.session_state.agg_stats = ["Max"]

def show_dash_metrics(t_max, t_min, t_avg, t_std):
    c1, c2, c3, c4 = st.columns(4)
    for c, lab in zip((c1, c2, c3, c4), (t_max, t_min, t_avg, t_std)):
        c.metric(label=lab, value="-")

def overview_page(
    texts, side_texts, COL_NAMES, df, dm, 
    BASWAP_NAME, STATION_LOOKUP, OTHER_STATIONS,
    MAP_HEIGHT, TABLE_HEIGHT,
    lang
):
    from station_data import norm_name, resolve_cols, pick_ec_col, get_station_list
    from map_handler import add_layers, create_map, render_map

    col_left, col_right = st.columns([7, 3], gap="small")
    with col_right:
        st.markdown(f'<div class="info-title">{texts["info_panel_title"]}</div>', unsafe_allow_html=True)

        # Use unified list that includes BASWAP and all others
        station_list = get_station_list(texts)

        station_options_display = [texts["picker_none"]] + [s["name"] for s in station_list]
        current_sel = st.session_state.get("selected_station")
        default_label = current_sel if current_sel in station_options_display else texts["picker_none"]

        picked_label = st.selectbox(
            label=texts["picker_label"],
            options=station_options_display,
            index=station_options_display.index(default_label),
        )
        st.session_state.selected_station = None if picked_label == texts["picker_none"] else picked_label

        latest_values = {}
        try:
            file_id = st.secrets.get("STATIONS_FILE_ID")
            if file_id:
                df_all = dm.read_csv_file(file_id)
                stn_col, time_col, ec_col = resolve_cols(df_all.columns)
                d = df_all.copy()
                d[time_col] = pd.to_datetime(d[time_col], errors="coerce")
                d = d.dropna(subset=[time_col])
                idx = d.groupby(stn_col)[time_col].idxmax()
                latest = d.loc[idx, [stn_col, ec_col]].copy()
                latest["key"] = latest[stn_col].map(norm_name)
                latest["val"] = pd.to_numeric(latest[ec_col], errors="coerce") * 2000.0
                latest_values = dict(zip(latest["key"], latest["val"]))
        except Exception:
            latest_values = {}

        # Fallback current value for BASWAP buoy using the local df if it isn't present in the stations file
        def _baswap_current_from_df(local_df: pd.DataFrame):
            for col, mult in [("EC Value (g/l)", 2000.0), ("EC Value (us/cm)", 1.0)]:
                if col in local_df.columns:
                    s = pd.to_numeric(local_df[col], errors="coerce").dropna()
                    if not s.empty:
                        return float(s.iloc[-1]) * mult
            return None

        baswap_fallback_val = _baswap_current_from_df(df)

        # Build table rows from unified list so map/table stay in sync
        rows = []
        for s in station_list:
            name = s["name"]
            key = norm_name(name)
            val = latest_values.get(key)
            if name == BASWAP_NAME and (val is None or pd.isna(val)):
                val = baswap_fallback_val
            display_val = "-" if val is None or pd.isna(val) else f"{val:.1f}"
            rows.append({
                texts["table_station"]: name,
                texts["current_measurement"]: display_val,
                texts["table_warning"]: "-",
            })
        table_df = pd.DataFrame(rows)
        st.dataframe(table_df, use_container_width=True, hide_index=True, height=TABLE_HEIGHT)

    with col_left:
        map_title = texts.get("map_title", "🗺️ Station Map")
        st.markdown(f"""<div class="map-title">{map_title}</div>""", unsafe_allow_html=True)
        center = [10.2, 106.0]; zoom = 8; highlight_location = None
        sel = st.session_state.get("selected_station")
        if sel and sel in STATION_LOOKUP:
            lat, lon = STATION_LOOKUP[sel]
            center = [lat, lon]; zoom = 12; highlight_location = (lat, lon)
        m = create_map(center, zoom, highlight_location, sel)
        add_layers(m, texts, BASWAP_NAME, STATION_LOOKUP[BASWAP_NAME], OTHER_STATIONS)
        map_out = render_map(m, MAP_HEIGHT)
    clicked_label = map_out.get("last_object_clicked_tooltip") if isinstance(map_out, dict) else None
    if clicked_label and clicked_label in STATION_LOOKUP and st.session_state.get("selected_station") != clicked_label:
        st.session_state.selected_station = clicked_label
        st.rerun()

    first_date = df["Timestamp (GMT+7)"].min().date()
    last_date = df["Timestamp (GMT+7)"].max().date()
    one_month_ago = max(first_date, last_date - timedelta(days=30))
    if st.session_state.get("date_from") is None:
        st.session_state.date_from = one_month_ago
    if st.session_state.get("date_to") is None:
        st.session_state.date_to = last_date

    sh_left, sh_right = st.columns([8, 1], gap="small")
    with sh_left:
        st.markdown(f"### 📊 {texts['overall_stats_title']}")
    with sh_right:
        st.empty()

    scope_label = texts.get("scope_label") or ("Station" if lang == "en" else "Trạm")
    none_label = "None" if lang == "en" else "Chưa chọn trạm"
    selected_station = st.session_state.get("selected_station")
    station_name_label = selected_station if selected_station else none_label

    c_label, c_btn = st.columns([8, 1], gap="small")
    with c_label:
        st.markdown(
            f'<div class="stats-scope"><span class="k">{scope_label}:</span> '
            f'<span class="v">{station_name_label}</span></div>',
            unsafe_allow_html=True,
        )
    with c_btn:
        if st.button(
            texts["clear_cache"],
            key="clear_cache_btn",
            help=texts.get("clear_cache_tooltip", "Clear cached data and fetch the latest data."),
            type="primary",
            use_container_width=True,
        ):
            st.cache_data.clear()
            st.rerun()

    t_max = texts.get("stats_max", "Maximum")
    t_min = texts.get("stats_min", "Minimum")
    t_avg = texts.get("stats_avg", "Average")
    t_std = texts.get("stats_std", "Std Dev")

    if not selected_station:
        show_dash_metrics(t_max, t_min, t_avg, t_std)
    elif selected_station == BASWAP_NAME:
        stats_df = filter_data(df, st.session_state.date_from, st.session_state.date_to)
        display_statistics(stats_df, st.session_state.target_col)
    else:
        try:
            file_id = st.secrets.get("STATIONS_FILE_ID")
            if not file_id:
                show_dash_metrics(t_max, t_min, t_avg, t_std)
            else:
                df_all = dm.read_csv_file(file_id)
                def _norm_col2(col: str) -> str:
                    import re
                    return re.sub(r"[^a-z0-9]", "", str(col).lower())
                norm_map = {_norm_col2(c): c for c in df_all.columns}
                stn_col = next((norm_map[k] for k in ["stationname", "station", "stationid", "name"] if k in norm_map), None)
                time_col = next((norm_map[k] for k in ["measdate", "datetime", "timestamp", "time", "date"] if k in norm_map), None)
                ec_col = pick_ec_col(df_all.columns)
                if not (stn_col and time_col and ec_col):
                    show_dash_metrics(t_max, t_min, t_avg, t_std)
                else:
                    d = df_all[[stn_col, time_col, ec_col]].copy()
                    d[time_col] = pd.to_datetime(d[time_col], errors="coerce")
                    d[ec_col] = pd.to_numeric(d[ec_col], errors="coerce")
                    d = d.dropna(subset=[time_col, ec_col])
                    sel_key = norm_name(selected_station)
                    mask = d[stn_col].map(norm_name) == sel_key
                    sd = d.loc[mask].sort_values(time_col, ascending=False).head(1000)
                    if sd.empty:
                        show_dash_metrics(t_max, t_min, t_avg, t_std)
                    else:
                        vals = sd[ec_col] * 2000.0
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric(label=t_max, value=f"{vals.max():.2f}")
                        c2.metric(label=t_min, value=f"{vals.min():.2f}")
                        c3.metric(label=t_avg, value=f"{vals.mean():.2f}")
                        c4.metric(label=t_std, value=f"{vals.std(ddof=1):.2f}")
        except Exception:
            show_dash_metrics(t_max, t_min, t_avg, t_std)

    st.divider()
    chart_container = st.container()
    settings_label = side_texts["sidebar_header"].lstrip("# ").strip()
    with st.expander(settings_label, expanded=False):
        settings_panel(side_texts, first_date, last_date, one_month_ago, last_date, COL_NAMES)
    date_from = st.session_state.date_from
    date_to = st.session_state.date_to
    target_col = st.session_state.target_col
    agg_funcs = st.session_state.agg_stats
    filtered_df = filter_data(df, date_from, date_to)
    with chart_container:
        st.subheader(f"📈 {target_col}")
        tabs = st.tabs([texts["hourly_view"], texts["daily_view"]])
        with tabs[0]:
            hourly = apply_aggregation(filtered_df, COL_NAMES, target_col, "Hour", agg_funcs)
            plot_line_chart(hourly, target_col, "Hour")
        with tabs[1]:
            daily = apply_aggregation(filtered_df, COL_NAMES, target_col, "Day", agg_funcs)
            plot_line_chart(daily, target_col, "Day")
    st.divider()
    st.subheader(texts["data_table"])
    table_cols_sel = st.multiselect(
        texts["columns_select"],
        options=COL_NAMES,
        default=st.session_state.get("table_cols", [COL_NAMES[0]]),
        key="table_cols_picker",
    )
    st.session_state.table_cols = list(table_cols_sel)
    show_cols = ["Timestamp (GMT+7)"] + st.session_state.table_cols
    existing = [c for c in show_cols if c in filtered_df.columns]
    st.write(f"{texts['data_dimensions']} ({filtered_df.shape[0]}, {len(existing)}).")
    st.dataframe(filtered_df[existing], use_container_width=True)


def about_page(lang):
    def _img_src(path: str) -> str:
        p = Path(path)
        if not p.exists():
            return ""  # no image; the alt text will show nothing
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        b64 = base64.b64encode(p.read_bytes()).decode()
        return f"data:{mime};base64,{b64}"
    html = get_about_html(lang)
    html = html.replace("__IMG1__", _img_src("img/1.jpg")).replace("__IMG2__", _img_src("img/2.jpg"))
    st.markdown(html, unsafe_allow_html=True)
