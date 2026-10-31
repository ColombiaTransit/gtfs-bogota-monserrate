# GTFS – Monserrate funicular & cable car (Bogotá)

Static [GTFS](https://gtfs.org/) feed for the two lines that climb Cerro de Monserrate in Bogotá, Colombia:

| Route | `route_id` | `route_type` |
|---|---|---|
| Funicular de Monserrate | `FUN` | 7 (funicular) |
| Teleférico de Monserrate (cable car) | `TEL` | 6 (aerial lift) |

The operator, Teleférico a Monserrate S.A., does not publish a GTFS feed. This repository builds one from the operator's website and OpenStreetMap.

## Download

The latest feed is attached to the most recent [release](https://github.com/ColombiaTransit/gtfs-bogota-monserrate/releases/latest) as `monserrate-gtfs.zip`.

Stable URL for the most recent feed:

```
https://github.com/ColombiaTransit/gtfs-bogota-monserrate/releases/latest/download/monserrate-gtfs.zip
```

## What is in the feed

- **Stops.** Two stations, each with a separate platform for the funicular and for the cable car:
  - `ABAJO`, the lower station on Paseo Bolívar
  - `CUMBRE`, the summit
- **Service hours:**

  | Day type | Hours |
  |---|---|
  | Mon–Sat | 06:30–22:00 |
  | Sunday | 05:30–17:00 |
  | Public holidays | 06:30–17:00 |

  There is also an early descent for athletes from 05:30 on Mon–Sat.
- **Frequency-based trips.** The vehicles shuttle continuously without a fixed timetable, so trips are modelled in `frequencies.txt` with `exact_times=0`.
- **Colombian public holidays.** They are applied automatically via `calendar_dates.txt`.
- **Fares.** In COP, using GTFS Fares v2, with separate products for Mon–Sat/holidays and for Sundays.
- **Shapes.** Taken from the OpenStreetMap geometry of both lines.
- **Transfers.** Funicular ⇄ cable car transfers at both stations.

The modelling choices and assumptions are described in [docs/DATA_MODEL.md](docs/DATA_MODEL.md).

> **Note:** headways and ride times are estimates, because the operator does not publish them. The feed is meant for trip planners to show that the service exists and when it runs. It does not predict exact departures.

## Building

You need Python 3.9 or newer.

```bash
pip install -r requirements.txt
python3 build.py                 # writes monserrate-gtfs.zip
```

Optionally, validate the feed with the [MobilityData GTFS validator](https://github.com/MobilityData/gtfs-validator):

```bash
java -jar gtfs-validator-cli.jar -i monserrate-gtfs.zip -o validation -c co
```

The current feed produces no errors. It produces one expected warning, `attribution_without_role`: the OpenStreetMap attribution is a data-source credit, not a producer or operator.

## Maintenance

The route itself does not change. Hours and fares do, so they should be checked about once a year, and whenever the operator announces a temporary closure. Everything that can change lives in the `CONFIG` block at the top of `build.py`.

See [docs/MAINTENANCE.md](docs/MAINTENANCE.md) for the step-by-step procedure, including how to cut a release.

## Repository layout

```
build.py                        feed generator (config at the top)
requirements.txt                Python dependencies
data/osm-export-2026-10-31.json OpenStreetMap snapshot used for stops and shapes
docs/DATA_MODEL.md              how the service is modelled in GTFS, and assumptions
docs/MAINTENANCE.md             yearly update and release procedure
```

## Sources and attribution

- **Schedules and fares:** [monserrate.co – Schedules and Prices](https://monserrate.co/en/schedules-and-prices/), checked 2026-10-31.
- **Stop locations and line geometry:** © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), available under the [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/). The OSM-derived parts of the feed (`stops.txt`, `shapes.txt`) are covered by the ODbL. The attribution is also included in the feed's `attributions.txt`.
- **Public holidays:** the [`holidays`](https://pypi.org/project/holidays/) Python package.

This feed is not affiliated with or endorsed by Teleférico a Monserrate S.A. Always check [monserrate.co](https://monserrate.co/) for the authoritative schedule.
