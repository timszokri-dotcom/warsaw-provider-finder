# Warsaw Provider Finder

**Business question:** Which mapped car-repair businesses in Warsaw could a car-service startup
investigate as potential service providers for a car-service marketplace?

## Geoapify REST API — beginner exercise

`fetch_geoapify.py` makes a GET request for up to 20 car-repair places within
10 km of a selected point in Warsaw. It reads an API key from the environment,
checks HTTP status and response structure, prints business names, and saves
`data/geoapify_response.json`. The circle is not Warsaw's administrative boundary,
and this one-page sample is not an exhaustive list. No scheduling is implemented.

Create a free Geoapify project and key, then run on macOS/Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# Prompt for the key without displaying it or storing it in shell history.
printf 'Geoapify API key: '
read -r -s GEOAPIFY_API_KEY
export GEOAPIFY_API_KEY
printf '\\n'
python fetch_geoapify.py
```

Run the offline checks (no API credits used):

```sh
python -m unittest test_geoapify -v
```

Never commit keys. `.env` files and generated data are ignored; the script does
not automatically load `.env` files. Replace keys that have been disclosed.
Keep usage within your free-plan allowance; a request can consume multiple credits.
Observe Geoapify and underlying data-source attribution requirements when sharing
results. This connector demonstrates REST API extraction, not advertising API access.

- [Geoapify Places documentation](https://apidocs.geoapify.com/docs/places/)
- [Plans and attribution requirements](https://www.geoapify.com/pricing/)

## Original Overpass extractor

This first step retrieves real OpenStreetMap data through the public Overpass
HTTP API, validates the response, and exports a CSV. Python 3.9+; no packages,
API key, account, or billing required.

## Run

```sh
python3 fetch_providers.py
```

Run from this folder or use the script's absolute path. Output is saved beside
the script in `data/`. Each run replaces the previous snapshot.

On Tim's Mac, the default Apple Python encountered an HTTPS handshake failure.
Use the existing newer installation instead:

```sh
/opt/homebrew/bin/python3 fetch_providers.py
```

## Understand the request

1. Read `query.overpassql`: select Warsaw's city-level administrative area using
   Wikidata Q270 and `admin_level=8` (the source also has other Warsaw boundaries).
2. Select nodes, ways, and relations (`nwr`) tagged `shop=car_repair` in that area.
3. Send the query as a form-encoded HTTP POST to
   `https://overpass-api.de/api/interpreter`.
4. Read the JSON `elements` array, preserving the complete response.
5. Validate the selected boundary, object IDs, category, and coordinates.
6. Export business details to `data/providers.csv` and coverage counts to
   `data/summary.json`.

Overpass is a query-based HTTP API, not a conventional resource-oriented REST
interface. It still provides real HTTP/JSON extraction experience.

## Files to inspect

- `data/raw_response.json`: original source and tags.
- `data/providers.csv`: one row per OSM object, not necessarily one unique business.
- `data/summary.json`: source timestamp and field-completeness counts.

Empty fields mean unknown, not that a business lacks that feature. Way/relation
coordinates are bounding-box centers, not verified entrances. OSM may have duplicate,
missing, outdated, or misclassified businesses. Boundary selection follows Overpass
area semantics; edge cases can require geographic review. These records do not prove
that businesses are operational, provide mobile assistance, or want to join the app.
Review duplicates before counting unique businesses. This snapshot measures mapped
supply, not customer demand or advertising performance.

## Next learning steps

Inspect five source records and their CSV rows. Then load the snapshot into SQL,
measure missing fields and duplicates, and make a Power BI coverage map. Add app
requests and registered-provider data later to analyse marketplace fulfilment.

## Responsible use and attribution

Download a modest snapshot for local analysis; cache results instead of repeatedly
querying the shared service. Public servers may time out or rate-limit requests;
this script fails visibly rather than silently publishing a partial query result.
Do not use this public instance as the production backend for Dima's app.

Data © OpenStreetMap contributors, licensed under the Open Database License (ODbL).
Include attribution on any map/report and review ODbL obligations before distributing
a derived database. CSV contact fields are source data, not an outreach instruction.

- https://www.openstreetmap.org/copyright
- https://wiki.openstreetmap.org/wiki/Overpass_API
- https://dev.overpass-api.de/overpass-doc/en/preface/commons.html
- https://wiki.openstreetmap.org/wiki/Tag:shop=car_repair

The code and README are prepared for GitHub; nothing is published automatically.
