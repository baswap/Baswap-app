# Station definitions and data handling
OTHER_STATIONS = [
    {"name":"An Thuận","lon":106.6050222,"lat":9.976388889},
    {"name":"Trà Kha","lon":106.2498341,"lat":9.623059755},
    {"name":"Cầu Quan","lon":106.1139858,"lat":9.755832963},
    {"name":"Trà Vinh","lon":106.3554593,"lat":9.976579766},
    {"name":"Hưng Mỹ","lon":106.4509515,"lat":9.885625852},
    {"name":"Bến Trại","lon":106.5241047,"lat":9.883471894},
    {"name":"Lộc Thuận","lon":106.6030561,"lat":10.24436142},
    {"name":"Sơn Đốc","lon":106.4638095,"lat":10.05325888},
    {"name":"Bình Đại","lon":106.7077466,"lat":10.20537343},
    {"name":"An Định","lon":106.4292222,"lat":10.3122585},
    {"name":"Hòa Bình","lon":106.5923811,"lat":10.28936244},
    {"name":"Vàm Kênh","lon":106.7367911,"lat":10.27264736},
    {"name":"Đồng Tâm","lon":106.334365,"lat":10.329834},
    {"name":"Hương Mỹ","lon":106.383335,"lat":9.983307},
    {"name":"Tân An","lon":106.4157942,"lat":10.54178782},
    {"name":"Tuyên Nhơn","lon":106.1937576,"lat":10.65884433},
    {"name":"Bến Lức","lon":106.4744215,"lat":10.63677295},
    {"name":"Cầu Nối","lon":106.5723735,"lat":10.41872922},
    {"name":"Xuân Khánh","lon":106.3507418,"lat":10.8419521},
    {"name":"Mỹ Tho","lon":106.3469893,"lat":10.34689161},
    {"name":"Thạnh Phú","lon":105.857877,"lat":9.498933823},
    {"name":"Đại Ngãi","lon":106.0779384,"lat":9.733924226},
    {"name":"Trần Đề","lon":106.2048576,"lat":9.528517406},
    {"name":"Sóc Trăng","lon":105.9683935,"lat":9.60610964},
    {"name":"Long Phú","lon":106.1514227,"lat":9.61341221},
    {"name":"An Lạc Tây","lon":105.9790505,"lat":9.853617387},
    {"name":"Mỹ Hòa","lon":106.3454055,"lat":10.22267205},
    {"name":"Rạch Giá","lon":105.0840604,"lat":10.01215053},
    {"name":"Xẻo Rô","lon":105.1129466,"lat":9.86417299},
    {"name":"Gò Quao","lon":105.2774089,"lat":9.722549732},
    {"name":"An Ninh","lon":105.1245146,"lat":9.87196146},
    {"name":"Phước Long","lon":105.4609733,"lat":9.43721774},
    {"name":"Gành Hào","lon":105.4183437,"lat":9.032165591},
    {"name":"Cà Mau","lon":105.1497391,"lat":9.171865534},
    {"name":"Sông Đốc","lon":104.8336191,"lat":9.040111339},
    {"name":"Vũng Liêm","lon":106.2329204,"lat":10.08355046},
    {"name":"Chù Chí","lon":105.318965,"lat":9.303196225},
    {"name":"Bạc Liêu","lon":105.7212312,"lat":9.281556339},
    {"name":"Thới Bình","lon":105.0868866,"lat":9.3479814},
    {"name":"Luyến Quỳnh","lon":104.9466043,"lat":10.16807224},
    {"name":"Măng Thít","lon":106.1562281,"lat":10.16149561},
    {"name":"Tám Ngàn","lon":104.8420667,"lat":10.32105},
]

# BASWAP coordinates
BASWAP_LATLON = (10.099833, 106.208306)

BASWAP_STATIONS = [
    {"name":"Vĩnh Long","lon":106.208306,"lat":10.099833},
    {"name":"Cần Giờ","lon":106.807946,"lat":10.598092}, 
    {"name":"VGU","lon":106.613894203,"lat":11.108438972}
]

def get_station_lookup(texts: dict):
    """
    Create a lookup dictionary mapping station name -> (lat, lon).
    Returns (station_lookup, baswap_layer_label).

    - OTHER_STATIONS and BASWAP_STATIONS are expected to be available in the module scope.
    - texts['baswap_name'] is used as the (localized) layer name for the BASWAP group.
    """
    station_lookup = {}

    # Add other stations (skip invalid entries)
    for s in OTHER_STATIONS:
        try:
            name = s["name"]
            lat = float(s["lat"])
            lon = float(s["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        station_lookup[name] = (lat, lon)

    # Add all BASWAP stations (supports multiple)
    for s in BASWAP_STATIONS:
        try:
            name = s["name"]
            lat = float(s["lat"])
            lon = float(s["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        station_lookup[name] = (lat, lon)

    return station_lookup

def norm_name(name: str) -> str:
    """Normalize station name for comparison"""
    import unicodedata, re
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")  # strip accents
    s = re.sub(r"[\W_]+", "", s)  # remove spaces/punct
    return s.lower()

def norm_name_capitalize(name: str) -> str:
    """Normalize station name for comparison, keeping capitalization"""
    import unicodedata, re
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")  # strip accents
    s = re.sub(r"[\W_]+", "", s)  # remove spaces/punct
    return s  # keep original capitalization

def norm_col(col: str) -> str:
    """Normalize column name for comparison"""
    import re
    return re.sub(r"[^a-z0-9]", "", str(col).lower())

def resolve_cols(df_cols):
    """Return (station_col, time_col, ec_col) by flexible matching"""
    norm_map = {norm_col(c): c for c in df_cols}
    stn_candidates = ["station_name", "station", "name"]
    time_candidates = ["measdate", "datetime", "timestamp", "time", "date", "ds"]
    ec_candidates = ["EC Value (g/l)", "EC[g/l]"]  # matches EC(g/l) or EC[g/l]

    def pick(cands):
        for k in cands:
            if k in df_cols:
                return k
        return None

    stn = pick(stn_candidates)
    tcol = pick(time_candidates)
    ecol = pick(ec_candidates)
    print(stn, tcol, ecol)
    if not (stn and tcol and ecol):
        raise ValueError("Required columns not found.")
    return stn, tcol, ecol

def pick_ec_col(cols):
    """Flexible EC(g/l) resolver for both datasets"""
    import re
    def norm(s): return re.sub(r"[^a-z0-9]", "", s.lower())
    norm_map = {norm(c): c for c in cols}
    for key in ["ecgl", "ecvaluegl", "ecgperl", "ecg_l", "ecglvalue", "ecg"]:
        if key in norm_map:
            return norm_map[key]
    if "EC Value (g/l)" in cols:  # exact known BASWAP column
        return "EC Value (g/l)"
    return None
