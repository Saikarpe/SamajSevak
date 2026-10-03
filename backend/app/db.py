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
CREATE TABLE IF NOT EXISTS officers (
    username TEXT PRIMARY KEY, name TEXT, salt BLOB, pw_hash BLOB, demo INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS citizens (
    id TEXT PRIMARY KEY, name TEXT, phone TEXT UNIQUE, created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_g_status ON grievances(status);
CREATE INDEX IF NOT EXISTS idx_g_created ON grievances(created_at);
"""
# Columns added after the first release; applied to old databases on startup.
#   geo_source    gps | pin | seed (a real point)  or  ward (ward centre, approximate)
#   label_source  ai | officer (category confirmed or corrected by a person -> training data)
#
# Master issues. Every row in `grievances` is one citizen report and is never deleted. The report
# whose master_id is its own id IS the master issue: it carries the operational state (status,
# assignee, stage, resolution) and that state is copied onto every report linked to it.
#   master_id           the issue this report belongs to
#   association_source  CITIZEN (joined it) | AI (matched after submission) | OFFICER; NULL on a master
#   stage / stage_due   escalation stage of the issue and when it next escalates
#   satisfaction        this citizen's own answer once resolved: Satisfied | Not Satisfied | NULL (no response)
#   ip_hash             salted hash for abuse signals only; never returned by any API
MIGRATIONS = {"geo_source": "TEXT DEFAULT 'ward'", "language": "TEXT", "photo": "TEXT", "photo_check": "TEXT",
              "resolution_photo": "TEXT", "label_source": "TEXT DEFAULT 'ai'",
              "master_id": "TEXT", "association_source": "TEXT", "association_note": "TEXT", "citizen_id": "TEXT",
              "ai_category": "TEXT", "citizen_category": "TEXT", "classification_source": "TEXT DEFAULT 'AI'",
              "stage": "TEXT DEFAULT 'Complaint'", "stage_due": "TEXT", "satisfaction": "TEXT", "feedback_text": "TEXT",
              "photo_sha": "TEXT", "photo_phash": "TEXT", "ip_hash": "TEXT", "review_signals": "TEXT",
              "abuse_review": "INTEGER DEFAULT 0"}
EVENT_MIGRATIONS = {"actor_type": "TEXT", "prev_state": "TEXT", "new_state": "TEXT"}
# officer roles: admin (everything) | department (its own issues at Complaint / Warning) | strike (all departments)
OFFICER_MIGRATIONS = {"role": "TEXT DEFAULT 'admin'", "department": "TEXT"}
UPLOADS = DB_PATH.parent / "uploads"


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
        for table, cols in (("grievances", MIGRATIONS), ("events", EVENT_MIGRATIONS), ("officers", OFFICER_MIGRATIONS)):
            have = {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}
            for col, ddl in cols.items():
                if col not in have:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
        # reports created before master issues existed: each becomes its own issue at the Complaint stage
        c.execute("UPDATE grievances SET master_id=id, stage_due=sla_due, ai_category=category WHERE master_id IS NULL")
        c.execute("CREATE INDEX IF NOT EXISTS idx_g_master ON grievances(master_id)")


def row_to_dict(r: sqlite3.Row) -> dict:
    d = dict(r)
    for k in ("analysis", "photo_check", "review_signals"):
        if d.get(k):
            d[k] = json.loads(d[k])
    return d
