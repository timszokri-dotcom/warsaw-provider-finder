"""Import a Geoapify snapshot into the local workshop database."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
SNAPSHOT = DATA_DIR / "geoapify_response.json"
DATABASE = DATA_DIR / "workshops.sqlite3"


def import_snapshot(snapshot=SNAPSHOT, database=DATABASE):
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        raise ValueError("Expected a GeoJSON FeatureCollection.")
    features = payload.get("features")
    if not isinstance(features, list):
        raise ValueError("Expected a list of GeoJSON features.")

    rows = {}
    for feature in features:
        properties = feature.get("properties") if isinstance(feature, dict) else None
        place_id = properties.get("place_id") if isinstance(properties, dict) else None
        if not isinstance(place_id, str) or not place_id.strip():
            raise ValueError("Every workshop must have a Geoapify place ID.")
        rows.setdefault(place_id, json.dumps(feature, ensure_ascii=False, allow_nan=False))

    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS workshops (id TEXT PRIMARY KEY, feature TEXT NOT NULL)"
        )
        connection.execute("DELETE FROM workshops")
        connection.executemany("INSERT INTO workshops VALUES (?, ?)", rows.items())
    return len(rows)


if __name__ == "__main__":
    try:
        print(f"Imported {import_snapshot()} workshops into {DATABASE.name}.")
    except (OSError, ValueError, sqlite3.Error) as error:
        raise SystemExit(f"Workshop import failed: {error}") from None
