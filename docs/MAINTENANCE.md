# Maintenance

The lines themselves do not change. Hours, fares and occasional temporary closures do. Plan to do this review **once a year**, before the current feed expires (`FEED_END` in `build.py`), and whenever the operator announces a closure.

## 1. Check the source

Open <https://monserrate.co/en/schedules-and-prices/> and compare it with the `CONFIG` block in `build.py`:

| On the website | In `build.py` |
|---|---|
| "Schedules for the funicular and/or cable car" | `HOURS` |
| "Athletes can purchase their descent ticket … starting at 5:30 AM" | `ATHLETE_DESCENT` |
| Banner at the top of the page about closures, e.g. "transportation … exclusively via the funicular" | `SUSPENSIONS` |
| "Prices", both the Mon–Sat/holidays and the Sunday tables | `FARES` |

Also check the Spanish version of the page (language switch at the top of the site). Announcements sometimes appear there first.

## 2. Update `build.py`

1. **Feed period and version.**
   - Set `FEED_START` to the day of the update.
   - Set `FEED_END` to one year later.
   - Set `FEED_VERSION` to the release date as `YYYY.MM.DD`.
2. **Hours and fares.** Update `HOURS` and `FARES` if they changed.
3. **Suspensions.**
   - Add any announced suspension to `SUSPENSIONS` as `(first_day, last_day, route_id)`, where `route_id` is `FUN` or `TEL`.
   - Old entries may stay in the list; dates outside the feed period are ignored.
   - If a suspension is announced *after* a release, add it and cut a new release right away.
4. **Holidays.** Upgrade the holidays package (`pip install -U holidays`) so that new or changed Colombian holidays are included.

## 3. (Optional) Refresh OpenStreetMap data

Station locations rarely change. To check them, run this query on <https://overpass-turbo.eu>:

```
[out:json][timeout:25];
(
  way["railway"="funicular"](4.595,-74.065,4.610,-74.050);
  way["aerialway"](4.595,-74.065,4.610,-74.050);
  nwr["railway"~"station|halt|stop"](4.595,-74.065,4.610,-74.050);
  nwr["aerialway"="station"](4.595,-74.065,4.610,-74.050);
  nwr["public_transport"~"station|stop_position|platform"](4.595,-74.065,4.610,-74.050);
);
out geom;
```

Then:

1. Export the raw data and save it as `data/osm-export-YYYY-MM-DD.json`.
2. Compare the coordinates with `STOPS` and `SHAPES_UP` in `build.py`. The node and way ids are listed in [DATA_MODEL.md](DATA_MODEL.md).

## 4. Build and validate

```bash
pip install -U -r requirements.txt
python3 build.py
java -jar gtfs-validator-cli.jar -i monserrate-gtfs.zip -o validation -c co
```

Open `validation/report.html`. It should list **no errors**. The only expected warning is `attribution_without_role`.

The validator jar is available from <https://github.com/MobilityData/gtfs-validator/releases>.

## 5. Commit and release

```bash
git add build.py data/ docs/
git commit -m "Update feed for YYYY–YYYY"
git push

gh release create vYYYY.MM.DD monserrate-gtfs.zip \
  --title "Feed YYYY.MM.DD" \
  --notes "Valid YYYY-MM-DD – YYYY-MM-DD. Changes: …"
```

The release asset must be named `monserrate-gtfs.zip`. That keeps the stable download URL working:

```
https://github.com/ColombiaTransit/gtfs-bogota-monserrate/releases/latest/download/monserrate-gtfs.zip
```
