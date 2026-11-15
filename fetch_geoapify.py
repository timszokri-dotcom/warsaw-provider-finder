"""Fetch a small sample of Warsaw car-repair places from Geoapify REST API."""
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
ENDPOINT = "https://api.geoapify.com/v2/places"


PAGE_SIZE = 20


def retry_delay(value, fallback):
    if not value:
        return fallback
    try:
        return max(0, int(value))
    except ValueError:
        try:
            deadline = parsedate_to_datetime(value)
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            return max(0, (deadline - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return fallback


def request_page(params):
    for attempt in range(3):
        delay = 2 ** attempt
        # Never print the prepared URL or exception: either can contain the key.
        try:
            response = requests.get(ENDPOINT, params=params, timeout=30,
                                    allow_redirects=False)
        except (requests.ConnectionError, requests.Timeout):
            if attempt == 2:
                raise SystemExit("Could not reach Geoapify after three attempts.") from None
        except requests.RequestException:
            raise SystemExit("Could not reach Geoapify. Check your connection and retry.") from None
        else:
            if response.status_code not in {429, 500, 502, 503, 504} or attempt == 2:
                return response
            delay = retry_delay(response.headers.get("Retry-After"), delay)
            if delay > 30:
                raise SystemExit(f"Geoapify HTTP {response.status_code} requested a retry delay over 30 seconds.")
        time.sleep(delay)


def fetch_page(params):
    response = request_page(params)
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

    return data


def main(max_pages=2):
    # Keep credentials outside source code and Git history.
    api_key = os.environ.get("GEOAPIFY_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Set GEOAPIFY_API_KEY before running this script.")

    params = {
        "categories": "service.vehicle.repair.car",
        "filter": "circle:20.98673919377302,52.22711165329281,10000",
        "bias": "proximity:20.98673919377302,52.22711165329281",
        "limit": PAGE_SIZE,
        "apiKey": api_key,
    }
    if max_pages < 1:
        raise ValueError("max_pages must be positive.")

    places = []
    seen_ids = set()
    for page in range(max_pages):
        data = fetch_page({**params, "offset": page * PAGE_SIZE})
        batch = data["features"]
        for place in batch:
            place_id = place["properties"].get("place_id")
            if isinstance(place_id, str) and place_id:
                if place_id in seen_ids:
                    continue
                seen_ids.add(place_id)
            places.append(place)
        if len(batch) < PAGE_SIZE:
            break

    data = {**data, "features": places}
    output = ROOT / "data" / "geoapify_response.json"
    output.parent.mkdir(exist_ok=True)
    temporary = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=output.parent, delete=False
    )
    temp_path = Path(temporary.name)
    try:
        with temporary:
            json.dump(data, temporary, ensure_ascii=False, indent=2)
        temp_path.replace(output)
    finally:
        temp_path.unlink(missing_ok=True)
    print(f"Received {len(places)} places across {page + 1} page(s).")
    for place in places:
        print(place["properties"].get("name") or "Name not provided")
    print("Saved data/geoapify_response.json")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-pages", type=int, default=2)
    args = parser.parse_args()
    if args.max_pages < 1:
        parser.error("--max-pages must be positive")
    main(args.max_pages)
