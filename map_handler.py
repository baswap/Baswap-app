import folium
from folium.plugins import MarkerCluster, FeatureGroupSubGroup
from streamlit_folium import st_folium

def add_layers(m, texts, BASWAP_NAME, BASWAP_LATLON, OTHER_STATIONS):
    """
    Shared clustering across BASWAP + Other, with separate toggles.
    When zoomed out, markers from both layers merge into one cluster count.
    """
    # One shared clusterer (hidden from LayerControl)
    shared_cluster = MarkerCluster(name="All stations (clusterer)", control=False)
    shared_cluster.add_to(m)

    # Two togglable sub-groups that share the clusterer — names are localized
    baswap_sub = FeatureGroupSubGroup(shared_cluster, name=texts["layer_baswap"], show=True)
    other_sub  = FeatureGroupSubGroup(shared_cluster, name=texts["layer_other"],  show=True)
    m.add_child(baswap_sub)
    m.add_child(other_sub)

    # BASWAP marker — identical behavior, only icon differs; tooltip localized
    folium.Marker(
        BASWAP_LATLON,
        tooltip=BASWAP_NAME,
        icon=folium.Icon(icon="tint", prefix="fa", color="blue"),
    ).add_to(baswap_sub)

    # Other stations
    for s in OTHER_STATIONS:
        folium.Marker(
            [float(s["lat"]), float(s["lon"])],
            tooltip=s["name"],
            icon=folium.Icon(icon="life-ring", prefix="fa", color="gray"),
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
