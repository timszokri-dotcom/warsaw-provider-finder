"""Fetch a small sample of Warsaw car-repair places from Geoapify REST API."""
import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
ENDPOINT = "https://api.geoapify.com/v2/places"


def main():
    # Keep credentials outside source code and Git history.
    api_key = os.environ.get("GEOAPIFY_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Set GEOAPIFY_API_KEY before running this script.")

    params = {
        "categories": "service.vehicle.repair.car",
        "filter": "circle:20.98673919377302,52.22711165329281,10000",
        "bias": "proximity:20.98673919377302,52.22711165329281",
        "limit": 20,
        "apiKey": api_key,
    }
    # Never print the prepared URL or exception: either can contain the key.
    try:
        response = requests.get(ENDPOINT, params=params, timeout=30,
                                allow_redirects=False)
    except requests.RequestException:
        raise SystemExit("Could not reach Geoapify. Check your connection and retry.") from None
    if response.status_code != 200:
        raise SystemExit(f"Geoapify request failed: HTTP {response.status_code}.")
    try:
        data = response.json()
    except ValueError:
        raise SystemExit("Geoapify returned invalid JSON.") from None
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        raise SystemExit("Unexpected response: expected a GeoJSON FeatureCollection.")
    places = data.get("features")
    if not isinstance(places, list):
        raise SystemExit("Unexpected response: features must be a list.")
    for place in places:
        if not isinstance(place, dict) or not isinstance(place.get("properties"), dict):
            raise SystemExit("Unexpected response: a place is missing its properties.")

    output = ROOT / "data" / "geoapify_response.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Received {len(places)} places (up to 20; not a complete Warsaw inventory).")
    for place in places:
        print(place["properties"].get("name") or "Name not provided")
    print("Saved data/geoapify_response.json")


if __name__ == "__main__":
    main()
