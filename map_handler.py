import folium
from folium.plugins import MarkerCluster, FeatureGroupSubGroup, BeautifyIcon

from streamlit_folium import st_folium


def add_layers(m, texts, BASWAP_STATIONS, OTHER_STATIONS, station_warnings=None):
    """
    Shared clustering across BASWAP + Other, with separate toggles.
    Marker color depends on warning level (0..4). Centers FA glyph horizontally and nudges it upward.
    """
    from folium.plugins import MarkerCluster, FeatureGroupSubGroup, BeautifyIcon
    import folium
    from branca.element import MacroElement, Template

    station_warnings = station_warnings or {}

    def _color_for(level):
        try:
            lv = int(level)
        except Exception:
            lv = None
        if lv == 0:
            return "#a5d6a7"  
        if lv == 1:
            return "#fff59d"   # light yellow
        if lv == 2:
            return "#ffeb3b"   # yellow
        if lv == 3:
            return "#ff9800"   # orange
        if lv == 4:
            return "#f44336"   # red
        return "#9e9e9e"       # fallback gray

    NUDGE_X = -1.8  # px to the right
    NUDGE_Y = 1.8   # px upward
    INNER_ICON_STYLE = f"margin-left: {NUDGE_X}px; transform: translateY(-{NUDGE_Y}px);"

    # One shared clusterer (hidden from LayerControl)
    shared_cluster = MarkerCluster(name="All stations (clusterer)", control=False)
    shared_cluster.add_to(m)

    # Two togglable sub-groups that share the clusterer — names are localized
    baswap_sub = FeatureGroupSubGroup(shared_cluster, name=texts["layer_baswap"], show=True)
    other_sub = FeatureGroupSubGroup(shared_cluster, name=texts["layer_other"], show=True)
    m.add_child(baswap_sub)
    m.add_child(other_sub)

    # --- BASWAP markers (multiple) ---
    for s in BASWAP_STATIONS:
        name = s["name"]
        try:
            lat = float(s["lat"])
            lon = float(s["lon"])
        except (KeyError, ValueError, TypeError):
            # skip invalid entries
            continue

        b_color = _color_for(station_warnings.get(name, 0))
        folium.Marker(
            [lat, lon],
            tooltip=name,
            icon=BeautifyIcon(
                icon="tint", prefix="fa",
                icon_shape="marker",
                background_color=b_color,
                border_color="#2c3e50",
                inner_icon_style=INNER_ICON_STYLE,
            ),
        ).add_to(baswap_sub)

    # --- Other stations ---
    for s in OTHER_STATIONS:
        name = s["name"]
        try:
            lat = float(s["lat"])
            lon = float(s["lon"])
        except (KeyError, ValueError, TypeError):
            continue

        o_color = _color_for(station_warnings.get(name, 0))
        folium.Marker(
            [lat, lon],
            tooltip=name,
            icon=BeautifyIcon(
                icon="life-ring", prefix="fa",
                icon_shape="marker",
                background_color=o_color,
                border_color="#2c3e50",
                inner_icon_style=INNER_ICON_STYLE,
            ),
        ).add_to(other_sub)

    # Exactly two checkboxes (localized group names)
    folium.LayerControl(collapsed=False).add_to(m)

    # ---------- Color legend on the right side ----------
    legend_items = [
        (0, "<= 0.5 g/l"),
        (1, "0.5 – 1 g/l"),
        (2, "1 – 2 g/l"),
        (3, "2 – 4 g/l"),
        (4, "> 4 g/l"),
    ]

    rows_html = ""
    for level, label in legend_items:
        color = _color_for(level)
        rows_html += (
            f'<div style="display:flex;align-items:center;margin-bottom:2px;">'
            f'<span style="display:inline-block;width:12px;height:12px;'
            f'background:{color};border-radius:50%;margin-right:6px;'
            f'border:1px solid #555;"></span>'
            f'<span>{label}</span>'
            f'</div>'
        )

    legend_title = texts.get("legend_title", "EC warning levels")

    legend_template = f"""
    {{% macro html(this, kwargs) %}}
    <div style="
        position: absolute;
        top: 80px;              
        right: 10px;
        z-index: 9999;
        background-color: white;   
        padding: 8px 10px;
        border: 1px solid #ccc;          /* border around legend box */
        border-radius: 4px;
        box-shadow: 0 0 4px rgba(0,0,0,0.3);
        font-size: 12px;
        color: #000;                      /* text color black */
    ">
        <div style="font-weight: bold; margin-bottom: 4px;">{legend_title}</div>
        {rows_html}
    </div>
    {{% endmacro %}}
    """

    legend = MacroElement()
    legend._template = Template(legend_template)
    m.get_root().add_child(legend)



def create_map(center, zoom, highlight_location=None, selected_station=None):
    """Create the Folium map with all layers and markers"""
    m = folium.Map(location=center, zoom_start=zoom, tiles=None)
    folium.TileLayer("OpenStreetMap", name="Basemap", control=False).add_to(m)
    
    if highlight_location:
        folium.CircleMarker(
            location=highlight_location, radius=10, weight=3, fill=True, fill_opacity=0.2,
            color="#0077ff", tooltip=selected_station,
        ).add_to(m)
    
    return m

def render_map(m, MAP_HEIGHT, key="baswap_map"):
    """Render the map in streamlit and return the output"""
    return st_folium(m, width="100%", height=MAP_HEIGHT, key=key)
