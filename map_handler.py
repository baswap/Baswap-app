import folium
from folium.plugins import MarkerCluster, FeatureGroupSubGroup, BeautifyIcon

from streamlit_folium import st_folium

def add_layers(m, texts, BASWAP_NAME, BASWAP_LATLON, OTHER_STATIONS, station_warnings=None):
    """
    Shared clustering across BASWAP + Other, with separate toggles.
    Marker color depends on warning level (0..4).
    """
    station_warnings = station_warnings or {}

    def _color_for(level):
        try:
            lv = int(level)
        except Exception:
            lv = None
        if lv == 0:
            return "#1976d2"   # blue
        if lv == 1:
            return "#fff59d"   # light yellow
        if lv == 2:
            return "#ffeb3b"   # yellow
        if lv == 3:
            return "#ff9800"   # orange
        if lv == 4:
            return "#f44336"   # red
        return "#9e9e9e"       # fallback gray

    # One shared clusterer (hidden from LayerControl)
    shared_cluster = MarkerCluster(name="All stations (clusterer)", control=False)
    shared_cluster.add_to(m)

    # Two togglable sub-groups that share the clusterer — names are localized
    baswap_sub = FeatureGroupSubGroup(shared_cluster, name=texts["layer_baswap"], show=True)
    other_sub  = FeatureGroupSubGroup(shared_cluster, name=texts["layer_other"],  show=True)
    m.add_child(baswap_sub)
    m.add_child(other_sub)

    # BASWAP marker
    b_color = _color_for(station_warnings.get(BASWAP_NAME, 0))
    folium.Marker(
        BASWAP_LATLON,
        tooltip=BASWAP_NAME,
        icon=BeautifyIcon(
            icon="tint", prefix="fa",
            icon_shape="marker",
            background_color=b_color,
            border_color="#2c3e50"
        ),
    ).add_to(baswap_sub)

    # Other stations
    for s in OTHER_STATIONS:
        name = s["name"]
        o_color = _color_for(station_warnings.get(name, 0))
        folium.Marker(
            [float(s["lat"]), float(s["lon"])],
            tooltip=name,
            icon=BeautifyIcon(
                icon="life-ring", prefix="fa",
                icon_shape="marker",
                background_color=o_color,
                border_color="#2c3e50"
            ),
        ).add_to(other_sub)

    # Exactly two checkboxes (localized group names)
    folium.LayerControl(collapsed=False).add_to(m)


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
