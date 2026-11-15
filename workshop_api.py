"""Read the imported workshops through a local REST API."""
import json
import sqlite3
from contextlib import closing

from fastapi import FastAPI, HTTPException, Query

from workshop_store import DATABASE

app = FastAPI(title="Warsaw Workshop API")


def connect():
    try:
        return sqlite3.connect(f"{DATABASE.as_uri()}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        raise HTTPException(503, "Workshop database unavailable. Run workshop_store.py to import it.") from None


@app.get("/workshops")
def list_workshops(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=2**63 - 1),
):
    with closing(connect()) as connection:
        # Read the count and page from the same snapshot during a concurrent import.
        connection.execute("BEGIN")
        total = connection.execute("SELECT COUNT(*) FROM workshops").fetchone()[0]
        rows = connection.execute(
            "SELECT id, feature FROM workshops ORDER BY id LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()

    items = [{"id": workshop_id, "feature": json.loads(feature)} for workshop_id, feature in rows]
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "next_offset": offset + len(items) if offset + len(items) < total else None,
    }


@app.get("/workshops/{workshop_id}")
def get_workshop(workshop_id: str):
    with closing(connect()) as connection:
        row = connection.execute(
            "SELECT feature FROM workshops WHERE id = ?", (workshop_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(404, "Workshop not found.")
    return {"id": workshop_id, "feature": json.loads(row[0])}
