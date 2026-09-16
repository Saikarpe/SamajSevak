import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.getenv("SAMAJSEVAK_DB", Path(__file__).resolve().parents[1] / "data" / "samajsevak.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS grievances (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    citizen_name TEXT, phone TEXT, channel TEXT DEFAULT 'Web',
    ward TEXT, lat REAL, lng REAL,
    text TEXT NOT NULL, title TEXT,
    category TEXT, confidence REAL, department TEXT,
    priority_score REAL, priority_level TEXT, sentiment TEXT,
    status TEXT DEFAULT 'Submitted', assigned_to TEXT,
    sla_due TEXT, resolved_at TEXT, resolution_note TEXT, resolution_hours REAL,
    duplicate_of TEXT, feedback_rating INTEGER, analysis TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grievance_id TEXT, ts TEXT, status TEXT, note TEXT, actor TEXT
);
CREATE INDEX IF NOT EXISTS idx_g_status ON grievances(status);
CREATE INDEX IF NOT EXISTS idx_g_created ON grievances(created_at);
"""


@contextmanager
def conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    with conn() as c:
        c.executescript(SCHEMA)


def row_to_dict(r: sqlite3.Row) -> dict:
    d = dict(r)
    if d.get("analysis"):
        d["analysis"] = json.loads(d["analysis"])
    return d
