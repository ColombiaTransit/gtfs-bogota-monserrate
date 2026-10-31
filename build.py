#!/usr/bin/env python3
"""
Build a static GTFS feed for the funicular and cable car (teleférico) of
Cerro de Monserrate, Bogotá, Colombia.

Schedule and fare source: https://monserrate.co/en/schedules-and-prices/
Location and geometry:    OpenStreetMap (ODbL), see data/osm-export-*.json

Yearly maintenance: edit only the CONFIG block below and run

    python3 build.py [output.zip]

The default output is monserrate-gtfs.zip. See docs/MAINTENANCE.md.
"""
import csv
import io
import sys
import zipfile
from datetime import date, timedelta
from math import asin, cos, radians, sin, sqrt

import holidays  # pip install -r requirements.txt

# =============================================================================
# CONFIG: the only part that needs a yearly review
# =============================================================================

FEED_START = date(2026, 10, 31)
FEED_END = date(2027, 10, 31)
FEED_VERSION = "2026.10.31"

# Opening hours (start, end) per service type. Departures run up to and
# including closing time ("The last car departs at closing time").
HOURS = {
    "MO_SA": ("06:30:00", "22:00:00"),
    "SUNDAY": ("05:30:00", "17:00:00"),
    "HOLIDAY": ("06:30:00", "17:00:00"),
}

# First descent for athletes from 05:30 (Mon–Sat; on Sundays service opens at
# 05:30 anyway). Down only, assumed to run on the funicular.
ATHLETE_DESCENT = ("05:30:00", "06:30:00")

# There is no fixed timetable: vehicles shuttle continuously. Assumptions:
HEADWAY_SECS = 15 * 60          # estimated interval between departures
RIDE_SECS = {"FUN": 4 * 60,     # funicular, estimate
             "TEL": 5 * 60}     # cable car, OSM tag aerialway:duration=5

# Temporary suspensions: (first day, last day inclusive, route_id NOT running).
# Dates outside FEED_START..FEED_END are ignored. Example from the website:
# 13 Sep – 30 Oct 2026 only the funicular ran.
SUSPENSIONS = [
    (date(2026, 9, 13), date(2026, 10, 30), "TEL"),
]

# Fares in COP. The website lists no one-way fare for Sundays.
# product_id: (name, amount, timeframe group)
#   timeframe group "WEEK" = Mon–Sat and public holidays, "SUN" = Sunday
FARES = {
    "one_way_week":   ("Un trayecto (lun–sáb y festivos)",       21000, "WEEK"),
    "round_trip_week": ("Ida y regreso (lun–sáb y festivos)",    35000, "WEEK"),
    "senior_week":    ("Adulto mayor 62+ (lun–sáb y festivos)",  29500, "WEEK"),
    "fast_pass_week": ("Fast pass (lun–sáb y festivos)",         96500, "WEEK"),
    "round_trip_sun": ("Ida y regreso (domingo)",                21000, "SUN"),
    "senior_sun":     ("Adulto mayor 62+ (domingo)",             16500, "SUN"),
    "fast_pass_sun":  ("Fast pass (domingo)",                    96500, "SUN"),
}

# =============================================================================
# Static data (not expected to change)
# =============================================================================

AGENCY = {
    "agency_id": "TAM",
    "agency_name": "Teleférico a Monserrate S.A.",
    "agency_url": "https://monserrate.co/",
    "agency_timezone": "America/Bogota",
    "agency_lang": "es",
    "agency_phone": "+57 601 2845700",
    "agency_fare_url": "https://monserrate.co/en/schedules-and-prices/",
    "agency_email": "info@monserrate.co",
}

FEED_PUBLISHER = {
    "feed_publisher_name": "ColombiaTransit",
    "feed_publisher_url": "https://github.com/ColombiaTransit/gtfs-bogota-monserrate",
    "feed_contact_url": "https://github.com/ColombiaTransit/gtfs-bogota-monserrate/issues",
}

# Stations from OpenStreetMap (node id in stop_code).
STOPS = [
    # Parent stations (midpoint between their two platforms)
    dict(stop_id="ABAJO", stop_name="Estación Monserrate (abajo)",
         stop_lat=4.6029359, stop_lon=-74.0608691, location_type=1,
         stop_desc="Carrera 2 Este No. 21-48, Paseo Bolívar"),
    dict(stop_id="CUMBRE", stop_name="Cerro de Monserrate (cumbre)",
         stop_lat=4.6041272, stop_lon=-74.0554179, location_type=1,
         stop_desc="Estaciones superiores del funicular y del teleférico"),
    # Platforms
    dict(stop_id="FUN_ABAJO", stop_name="Funicular — Estación Monserrate (abajo)",
         stop_lat=4.6030036, stop_lon=-74.0608443, location_type=0,
         parent_station="ABAJO", platform_code="Funicular",
         stop_code="osm:node/12536828938"),
    dict(stop_id="TEL_ABAJO", stop_name="Teleférico — Estación Monserrate (abajo)",
         stop_lat=4.6028682, stop_lon=-74.0608939, location_type=0,
         parent_station="ABAJO", platform_code="Teleférico",
         stop_code="osm:node/12536828937"),
    dict(stop_id="FUN_CUMBRE", stop_name="Funicular — Monserrate (cumbre)",
         stop_lat=4.603599, stop_lon=-74.0551726, location_type=0,
         parent_station="CUMBRE", platform_code="Funicular",
         stop_code="osm:node/1005395546"),
    dict(stop_id="TEL_CUMBRE", stop_name="Teleférico — Monserrate (cumbre)",
         stop_lat=4.6046553, stop_lon=-74.0556631, location_type=0,
         parent_station="CUMBRE", platform_code="Teleférico",
         stop_code="osm:node/1151938687"),
]

ROUTES = [
    dict(route_id="FUN", agency_id="TAM", route_short_name="",
         route_long_name="Funicular de Monserrate", route_type=7,
         route_color="8B1E2D", route_text_color="FFFFFF",
         route_url="https://monserrate.co/en/schedules-and-prices/"),
    dict(route_id="TEL", agency_id="TAM", route_short_name="",
         route_long_name="Teleférico de Monserrate", route_type=6,
         route_color="1E5A8B", route_text_color="FFFFFF",
         route_url="https://monserrate.co/en/schedules-and-prices/"),
]

# Geometry from OSM, bottom to top.
SHAPES_UP = {
    # ways 99625017 + 99625025 (tunnel) + 28555379
    "FUN": [(4.6030036, -74.0608443), (4.6033788, -74.0572811),
            (4.603599, -74.0552256), (4.603599, -74.0551726)],
    # way 360392328 (reversed)
    "TEL": [(4.6028682, -74.0608939), (4.6045557, -74.0559527),
            (4.6046553, -74.0556631)],
}

STOP_PAIR = {"FUN": ("FUN_ABAJO", "FUN_CUMBRE"),
             "TEL": ("TEL_ABAJO", "TEL_CUMBRE")}

HEADSIGN = {"UP": "Monserrate (cumbre)", "DOWN": "Estación Monserrate (abajo)"}

# =============================================================================
# Build
# =============================================================================


def secs(hms_str):
    h, m, s = map(int, hms_str.split(":"))
    return h * 3600 + m * 60 + s


def hms(t):
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def haversine(a, b):
    la1, lo1, la2, lo2 = map(radians, (*a, *b))
    h = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371000 * asin(sqrt(h))


def daterange(a, b):
    while a <= b:
        yield a
        a += timedelta(days=1)


def build(out_path="monserrate-gtfs.zip"):
    files = {}

    def table(name, rows, cols=None):
        cols = cols or list(dict.fromkeys(k for r in rows for k in r))
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})
        files[name] = buf.getvalue()

    table("agency.txt", [AGENCY])
    table("stops.txt", STOPS)
    table("routes.txt", ROUTES)

    # --- Calendar ---------------------------------------------------------
    hol = holidays.Colombia(years=range(FEED_START.year, FEED_END.year + 1))
    s, e = FEED_START.strftime("%Y%m%d"), FEED_END.strftime("%Y%m%d")
    weekdays = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    pattern = {"MO_SA": (1, 1, 1, 1, 1, 1, 0),
               "SUNDAY": (0, 0, 0, 0, 0, 0, 1),
               "HOLIDAY": (0, 0, 0, 0, 0, 0, 0)}  # only via calendar_dates
    table("calendar.txt", [
        dict(service_id=f"{route}_{kind}", **dict(zip(weekdays, days)),
             start_date=s, end_date=e)
        for route in ("FUN", "TEL") for kind, days in pattern.items()])

    exceptions = {}  # (service_id, date) -> exception_type
    for d in daterange(FEED_START, FEED_END):
        ds = d.strftime("%Y%m%d")
        # Holiday on Mon–Sat: holiday service replaces regular service.
        # Holiday on a Sunday: regular Sunday service.
        if d in hol and d.weekday() != 6:
            for route in ("FUN", "TEL"):
                exceptions[(f"{route}_MO_SA", ds)] = 2
                exceptions[(f"{route}_HOLIDAY", ds)] = 1
        # Suspensions override everything for that route.
        for (frm, to, route) in SUSPENSIONS:
            if frm <= d <= to:
                for kind in pattern:
                    exceptions[(f"{route}_{kind}", ds)] = 2
    table("calendar_dates.txt",
          [dict(service_id=sid, date=ds, exception_type=t)
           for (sid, ds), t in sorted(exceptions.items(), key=lambda x: (x[0][1], x[0][0]))],
          ["service_id", "date", "exception_type"])

    # --- Shapes -----------------------------------------------------------
    shapes, shape_len = [], {}
    for route, pts in SHAPES_UP.items():
        for direction, seq in (("UP", pts), ("DOWN", list(reversed(pts)))):
            dist = 0.0
            for i, p in enumerate(seq):
                if i:
                    dist += haversine(seq[i - 1], p)
                shapes.append(dict(shape_id=f"{route}_{direction}", shape_pt_lat=p[0],
                                   shape_pt_lon=p[1], shape_pt_sequence=i + 1,
                                   shape_dist_traveled=round(dist, 1)))
            shape_len[f"{route}_{direction}"] = round(dist, 1)
    table("shapes.txt", shapes)

    # --- Trips, stop_times, frequencies -----------------------------------
    trips, stop_times, freqs = [], [], []

    def add_trip(route, service_id, trip_id, d, start, end):
        lower, upper = STOP_PAIR[route]
        frm, to = (lower, upper) if d == "UP" else (upper, lower)
        ride = RIDE_SECS[route]
        trips.append(dict(route_id=route, service_id=service_id, trip_id=trip_id,
                          trip_headsign=HEADSIGN[d], direction_id=0 if d == "UP" else 1,
                          shape_id=f"{route}_{d}", wheelchair_accessible=0,
                          bikes_allowed=2))
        stop_times.extend([
            dict(trip_id=trip_id, arrival_time="00:00:00", departure_time="00:00:00",
                 stop_id=frm, stop_sequence=1, timepoint=0, shape_dist_traveled=0),
            dict(trip_id=trip_id, arrival_time=hms(ride), departure_time=hms(ride),
                 stop_id=to, stop_sequence=2, timepoint=0,
                 shape_dist_traveled=shape_len[f"{route}_{d}"]),
        ])
        freqs.append(dict(trip_id=trip_id, start_time=start, end_time=end,
                          headway_secs=HEADWAY_SECS, exact_times=0))

    for route in ("FUN", "TEL"):
        for kind, (start, end) in HOURS.items():
            for d in ("UP", "DOWN"):
                # +1 s so a departure falls exactly at closing time
                add_trip(route, f"{route}_{kind}", f"{route}_{kind}_{d}", d,
                         start, hms(secs(end) + 1))
    add_trip("FUN", "FUN_MO_SA", "FUN_MO_SA_DOWN_EARLY", "DOWN", *ATHLETE_DESCENT)

    table("trips.txt", trips)
    table("stop_times.txt", stop_times)
    table("frequencies.txt", freqs)

    # --- Transfers between funicular and cable car ------------------------
    table("transfers.txt", [
        dict(from_stop_id=x, to_stop_id=y, transfer_type=2, min_transfer_time=180)
        for a, b in (("FUN_ABAJO", "TEL_ABAJO"), ("FUN_CUMBRE", "TEL_CUMBRE"))
        for x, y in ((a, b), (b, a))])

    # --- Fares (GTFS Fares v2) --------------------------------------------
    table("networks.txt", [dict(network_id="MONSERRATE",
                                network_name="Teleférico y Funicular de Monserrate")])
    table("route_networks.txt", [dict(network_id="MONSERRATE", route_id=r["route_id"])
                                 for r in ROUTES])
    table("fare_media.txt", [dict(fare_media_id="paper", fare_media_name="Tiquete",
                                  fare_media_type=1)])
    table("fare_products.txt",
          [dict(fare_product_id=pid, fare_product_name=n, fare_media_id="paper",
                amount=f"{amt:.2f}", currency="COP")
           for pid, (n, amt, _) in FARES.items()])
    table("timeframes.txt", [
        dict(timeframe_group_id=grp, start_time="00:00:00", end_time="24:00:00",
             service_id=f"{route}_{kind}")
        for route in ("FUN", "TEL")
        for kind, grp in (("MO_SA", "WEEK"), ("HOLIDAY", "WEEK"), ("SUNDAY", "SUN"))])
    table("fare_leg_rules.txt",
          [dict(leg_group_id=f"LEG_{grp}", network_id="MONSERRATE",
                from_timeframe_group_id=grp, fare_product_id=pid)
           for pid, (_, _, grp) in FARES.items()])

    # --- Feed info and attribution ----------------------------------------
    table("feed_info.txt", [dict(
        **FEED_PUBLISHER, feed_lang="es", default_lang="es",
        feed_start_date=s, feed_end_date=e, feed_version=FEED_VERSION)])
    table("attributions.txt", [dict(
        attribution_id="osm", organization_name="© OpenStreetMap contributors (ODbL)",
        is_producer=0, is_operator=0, is_authority=0,
        attribution_url="https://www.openstreetmap.org/copyright")])

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name, content)
    print(f"{out_path}: {len(files)} files ({', '.join(files)})")


if __name__ == "__main__":
    build(*sys.argv[1:2])
