SITES = [
    {"id": "shackleton", "name": "Shackleton Rim", "lat": -89.66, "lon": 129.2, "region": "south_pole",
     "note": "High illumination rim near permanently shadowed floor"},
    {"id": "shackleton_crater", "name": "Shackleton Crater", "lat": -89.90, "lon": 0.0, "region": "south_pole",
     "note": "Type locality for polar volatiles"},
    {"id": "connecting_ridge", "name": "Connecting Ridge", "lat": -89.45, "lon": -137.5, "region": "south_pole",
     "note": "Candidate for near-continuous illumination"},
    {"id": "malapert", "name": "Malapert Massif", "lat": -86.00, "lon": 0.0, "region": "south_pole",
     "note": "Tall massif with long Earth views"},
    {"id": "haworth", "name": "Haworth Crater", "lat": -87.40, "lon": -4.1, "region": "south_pole",
     "note": "Rim terrain adjacent to Shackleton"},
    {"id": "de_gerlache", "name": "de Gerlache", "lat": -88.50, "lon": -87.1, "region": "south_pole",
     "note": "Deep polar crater with intervening ridges"},
    {"id": "cabeus", "name": "Cabeus", "lat": -85.28, "lon": -42.13, "region": "south_pole",
     "note": "LCROSS impact target, volatile rich"},
    {"id": "nobile", "name": "Nobile", "lat": -85.20, "lon": 53.5, "region": "south_pole",
     "note": "Large ancient polar crater"},
    {"id": "amundsen", "name": "Amundsen", "lat": -84.50, "lon": 82.8, "region": "south_pole",
     "note": "Flat floor with moderate illumination"},
    {"id": "shoemaker", "name": "Shoemaker", "lat": -88.10, "lon": 44.9, "region": "south_pole",
     "note": "Fossil crater within South Pole basin"},
    {"id": "faustini", "name": "Faustini", "lat": -87.20, "lon": 84.3, "region": "south_pole",
     "note": "Permanently shadowed floor, raised rim"},
    {"id": "sverdrup", "name": "Sverdrup", "lat": -88.50, "lon": -152.0, "region": "south_pole",
     "note": "Far-side polar crater"},
    {"id": "rozhdestvensky", "name": "Rozhdestvensky", "lat": -85.20, "lon": -155.8, "region": "south_pole",
     "note": "Far-side polar terrain"},
    {"id": "leibnitz_beta", "name": "Leibnitz Beta", "lat": -85.00, "lon": -30.0, "region": "south_pole",
     "note": "Elevated polar plateau"},
    {"id": "apollo11", "name": "Apollo 11", "lat": 0.674, "lon": 23.473, "region": "historic",
     "note": "Sea of Tranquillity"},
    {"id": "apollo12", "name": "Apollo 12", "lat": -3.013, "lon": -23.422, "region": "historic",
     "note": "Oceanus Procellarum"},
    {"id": "apollo14", "name": "Apollo 14", "lat": -3.646, "lon": -17.472, "region": "historic",
     "note": "Fra Mauro"},
    {"id": "apollo15", "name": "Apollo 15", "lat": 26.132, "lon": 3.633, "region": "historic",
     "note": "Hadley-Apennine"},
    {"id": "apollo16", "name": "Apollo 16", "lat": -8.973, "lon": 15.501, "region": "historic",
     "note": "Descartes Highlands"},
    {"id": "apollo17", "name": "Apollo 17", "lat": 20.191, "lon": 30.772, "region": "historic",
     "note": "Taurus-Littrow"},
    {"id": "change4", "name": "Chang'e 4", "lat": -45.457, "lon": 177.589, "region": "historic",
     "note": "Von Karman crater, far side"},
    {"id": "change5", "name": "Chang'e 5", "lat": -43.058, "lon": -51.916, "region": "historic",
     "note": "Mons Rumker, sample return"},
    {"id": "change6", "name": "Chang'e 6", "lat": -41.64, "lon": -153.99, "region": "historic",
     "note": "Apollo basin, far-side sample return"},
    {"id": "luna9", "name": "Luna 9", "lat": 7.13, "lon": -64.37, "region": "historic",
     "note": "First survivable soft landing"},
    {"id": "surveyor3", "name": "Surveyor 3", "lat": -3.016, "lon": -23.418, "region": "historic",
     "note": "Visited by Apollo 12"},
]


def catalogue():
    return SITES


def resolve(site_id=None, lat=None, lon=None, name=None):
    if site_id:
        for s in SITES:
            if s["id"] == site_id:
                return dict(s)
        raise KeyError(site_id)
    if lat is None or lon is None:
        raise ValueError("lat and lon required for custom site")
    lat = float(lat)
    lon = float(lon)
    if not -90.0 <= lat <= 90.0:
        raise ValueError("lat out of range")
    lon = ((lon + 180.0) % 360.0) - 180.0
    return {"id": "custom", "name": name or f"Custom {lat:.3f}, {lon:.3f}",
            "lat": lat, "lon": lon, "region": "custom", "note": "User supplied coordinates"}
