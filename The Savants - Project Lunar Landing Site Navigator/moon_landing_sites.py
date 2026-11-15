from __future__ import annotations

import math
from dataclasses import dataclass, asdict

MOON_RADIUS_KM = 1737.4

_RAW = [
    # --- impacts -------------------------------------------------------
    ("Luna 2", "impact", "1959-09-14", 30.0, 0.0),
    ("Ranger 4", "impact", "1962-04-26", -15.5, -130.7),
    ("Ranger 6", "impact", "1964-02-02", 9.3864, 21.48),
    ("Ranger 7", "impact", "1964-07-31", -10.634, -20.68),
    ("Ranger 8", "impact", "1965-02-20", 2.6376, 24.7881),
    ("Ranger 9", "impact", "1965-03-24", -12.8281, -2.3884),
    ("Luna 5", "impact", "1965-05-12", -1.35, -25.48),
    ("Luna 7", "impact", "1965-10-07", 9.0, -49.0),
    ("Luna 8", "impact", "1965-12-06", 9.1, -63.3),
    ("Surveyor 2", "impact", "1966-09-23", 5.5, -12.0),
    ("Lunar Orbiter 1", "impact", "1966-10-29", 6.35, 160.71),
    ("Surveyor 5", "impact", "1967-09-11", 1.4551, 23.1943),
    ("Lunar Orbiter 3", "impact", "1967-10-09", 14.3, -92.7),
    ("Lunar Orbiter 2", "impact", "1967-10-11", 3.0, 119.1),
    ("Lunar Orbiter 5", "impact", "1968-01-31", -2.79, -83.04),
    ("Luna 15", "impact", "1969-07-21", 17.0, 60.0),
    ("Apollo 12 LM ascent stage", "impact", "1969-11-20", -3.94, -21.2),
    ("Apollo 13 S-IVB", "impact", "1970-04-15", -2.555, -27.8875),
    ("Apollo 14 S-IVB", "impact", "1971-02-04", -8.18, -26.0305),
    ("Apollo 14 LM ascent stage", "impact", "1971-02-07", -3.42, -19.67),
    ("Apollo 15 S-IVB", "impact", "1971-07-29", -1.2897, -11.8245),
    ("Apollo 15 LM ascent stage", "impact", "1971-08-03", 26.36, 0.25),
    ("Luna 18", "impact", "1971-09-11", 3.76, 56.66),
    ("Apollo 16 S-IVB", "impact", "1972-04-19", 1.921, -24.623),
    ("Apollo 16 subsatellite", "impact", "1972-05-29", 10.16, 111.9),
    ("Apollo 17 S-IVB", "impact", "1972-12-10", -4.1681, -12.3307),
    ("Apollo 17 LM ascent stage", "impact", "1972-12-15", 19.97, 30.49),
    ("Hiten", "impact", "1993-04-10", -34.0, 55.3),
    ("Lunar Prospector", "impact", "1999-07-31", -87.7, 42.0),
    ("SMART-1", "impact", "2006-09-03", -34.4, -46.2),
    ("Chandrayaan-1 MIP", "impact", "2008-11-14", -89.0, -30.0),
    ("Okina", "impact", "2009-02-12", 28.213, -159.033),
    ("Chang'e 1", "impact", "2009-03-01", -1.5, 52.36),
    ("Kaguya", "impact", "2009-06-10", -65.5, 80.4),
    ("LCROSS Centaur", "impact", "2009-10-09", -84.6796, -48.7093),
    ("LCROSS spacecraft", "impact", "2009-10-09", -84.719, -49.61),
    ("GRAIL A", "impact", "2012-12-17", 75.6088, -26.594),
    ("GRAIL B", "impact", "2012-12-17", 75.6508, -26.8341),
    ("LADEE", "impact", "2014-04-18", 11.8494, -93.2494),
    ("Beresheet", "impact", "2019-04-11", 32.5956, 19.3496),
    ("Longjiang 2", "impact", "2019-07-31", 16.6956, 159.517),
    ("Vikram", "impact", "2019-09-06", -70.881, 22.784),
    ("Chang'e 5 ascent craft", "impact", "2020-12-07", -30.0, 0.0),
    ("Spacecraft booster stage", "impact", "2022-03-04", 5.226, -125.514),
    # --- soft landings -------------------------------------------------
    ("Luna 9", "soft_landing", "1966-02-03", 7.13, -64.37),
    ("Surveyor 1", "soft_landing", "1966-06-02", -2.4745, -43.3398),
    ("Luna 13", "soft_landing", "1966-12-24", 18.87, -62.05),
    ("Surveyor 3", "soft_landing", "1967-04-20", -3.0162, -23.418),
    ("Surveyor 6", "soft_landing", "1967-11-10", 0.4742, -1.4275),
    ("Surveyor 7", "soft_landing", "1968-01-10", -40.9812, -11.5127),
    ("Luna 16", "soft_landing", "1970-09-20", -0.5137, 56.3638),
    ("Luna 17", "soft_landing", "1970-11-17", 38.23764, -35.00163),
    ("Luna 20", "soft_landing", "1972-02-21", 3.7863, 56.6242),
    ("Luna 21", "soft_landing", "1973-01-15", 25.9994, 30.4076),
    ("Luna 23", "soft_landing", "1974-11-06", 12.6667, 62.1511),
    ("Luna 24", "soft_landing", "1976-08-18", 12.7142, 62.2129),
    ("Chang'e 3", "soft_landing", "2013-12-14", 44.1214, -19.5117),
    ("Yutu rover", "soft_landing", "2013-12-14", 44.1208, -19.5122),
    ("Chang'e 4", "soft_landing", "2019-01-03", -45.457, 177.589),
    ("Yutu 2", "soft_landing", "2019-01-03", -45.46, 177.59),
    ("Chang'e 5", "soft_landing", "2020-12-01", -43.0576, -51.9161),
    # --- crewed (Apollo) -----------------------------------------------
    ("Apollo 11 LM descent stage", "crewed", "1969-07-20", 0.67416, 23.47314),
    ("Apollo 12 LM descent stage", "crewed", "1969-11-19", -3.0128, -23.4219),
    ("Apollo 14 LM descent stage", "crewed", "1971-02-05", -3.64589, -17.47194),
    ("Apollo 15 LM descent stage", "crewed", "1971-07-30", 26.13239, 3.6333),
    ("Apollo 16 LM descent stage", "crewed", "1972-04-21", -8.9734, 15.5011),
    ("Apollo 17 LM descent stage", "crewed", "1972-12-11", 20.1911, 30.7723),
    # --- rovers --------------------------------------------------------
    ("Lunokhod 1", "rover", "1970-11-17", 38.315, -35.0081),
    ("Lunokhod 2", "rover", "1973-01-15", 25.8323, 30.9222),
]


@dataclass(frozen=True)
class Site:
    name: str
    group: str
    date: str
    lat: float
    lon: float

    @property
    def lon_east(self) -> float:
        return self.lon % 360.0

    @property
    def lat_rad(self) -> float:
        return math.radians(self.lat)

    @property
    def lon_rad(self) -> float:
        return math.radians(self.lon)

    def xyz(self, radius_km: float = MOON_RADIUS_KM) -> tuple[float, float, float]:
        r = self.lat_rad
        c = math.cos(r)
        return (
            radius_km * c * math.cos(self.lon_rad),
            radius_km * c * math.sin(self.lon_rad),
            radius_km * math.sin(r),
        )


SITES: list[Site] = [Site(*row) for row in _RAW]

BY_NAME: dict[str, Site] = {s.name: s for s in SITES}

IMPACTS: list[Site] = [s for s in SITES if s.group == "impact"]
SOFT_LANDINGS: list[Site] = [s for s in SITES if s.group == "soft_landing"]
CREWED_LANDINGS: list[Site] = [s for s in SITES if s.group == "crewed"]
ROVERS: list[Site] = [s for s in SITES if s.group == "rover"]


def get(name: str) -> Site:
    if name in BY_NAME:
        return BY_NAME[name]
    wanted = " ".join(name.lower().split())
    for key, site in BY_NAME.items():
        if " ".join(key.lower().split()) == wanted:
            return site
    raise KeyError(f"unknown landing site: {name!r}")


def great_circle_km(lat1: float, lon1: float, lat2: float, lon2: float,
                    radius_km: float = MOON_RADIUS_KM) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * radius_km * math.asin(min(1.0, math.sqrt(a)))


def distance_km(a: Site, b: Site) -> float:
    return great_circle_km(a.lat, a.lon, b.lat, b.lon)


def as_dicts() -> list[dict]:
    return [asdict(s) for s in SITES]


if __name__ == "__main__":
    print(f"{len(SITES)} sites "
          f"({len(IMPACTS)} impacts, {len(SOFT_LANDINGS)} soft landings, "
          f"{len(CREWED_LANDINGS)} crewed, {len(ROVERS)} rovers)\n")
    print(f"{'Crewed landing site':<30}{'date':<12}{'lat':>10}{'lon':>11}")
    for s in CREWED_LANDINGS:
        print(f"{s.name:<30}{s.date:<12}{s.lat:>10.5f}{s.lon:>11.5f}")
    a11, a17 = get("Apollo 11 LM descent stage"), get("Apollo 17 LM descent stage")
    print(f"\nApollo 11 -> 17: {distance_km(a11, a17):.1f} km")
    print(f"Apollo 11 xyz   : {a11.xyz()}")
