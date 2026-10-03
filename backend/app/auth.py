"""Officer authentication: salted PBKDF2 password hashes and HMAC-signed bearer tokens.
Standard library only.

Accounts come from the environment (OFFICER_USER / OFFICER_PASSWORD / OFFICER_NAME) plus one head per
department and one login per strike body (STAFF_PASSWORD; the demo password in the demo build).
With no password configured a demo account is created and shown on the login page,
so the hosted demo stays usable; set OFFICER_PASSWORD for any real deployment.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from fastapi import Header, HTTPException

from app import db
from app.knowledge import CATEGORIES, ESCALATION_STAGES

DEMO_USER, DEMO_PASSWORD = "officer", "samajsevak-demo"
# login name of each department head
_SHORT = {"Water Supply": "water", "Roads & Potholes": "roads", "Electricity": "electricity",
          "Garbage & Sanitation": "waste", "Drainage & Sewage": "drainage", "Street Lights": "streetlights",
          "Public Health": "health", "Public Transport": "transport", "Encroachment": "encroachment",
          "Safety & Law": "police", "Tree & Parks": "gardens"}
DEPARTMENT_USERS = {_SHORT[cat]: v["department"] for cat, v in CATEGORIES.items()}

def _local_secret() -> bytes:
    """Without SAMAJSEVAK_SECRET a random key is kept next to the database, so a restart
    (or uvicorn --reload) does not invalidate every citizen and officer token."""
    path = db.DB_PATH.parent / ".secret"
    try:
        if path.exists():
            return bytes.fromhex(path.read_text().strip())
        key = secrets.token_bytes(32)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(key.hex())
        return key
    except (OSError, ValueError):
        return secrets.token_bytes(32)


SECRET = os.getenv("SAMAJSEVAK_SECRET", "").encode() or _local_secret()
TOKEN_HOURS = 8
MAX_FAILS, LOCK_SECONDS = 5, 300
_fails: dict[str, list[float]] = {}


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)


def is_demo() -> bool:
    return not os.getenv("OFFICER_PASSWORD")


def staff_accounts() -> list[dict]:
    """One head per department (sees only its own issues while they are at the Complaint / Warning
    stage) and one login per strike body (sees every department, to check they are working)."""
    heads = [{"username": user, "name": f"Head, {dept}", "role": "department", "department": dept}
             for user, dept in DEPARTMENT_USERS.items()]
    strikes = [{"username": f"strike{i}", "name": who, "role": "strike", "department": None}
               for i, (_, who, _) in enumerate(ESCALATION_STAGES[2:], 1)]
    return heads + strikes


def staff_password() -> str | None:
    """STAFF_PASSWORD for every department / strike login; the demo build uses the demo password.
    With OFFICER_PASSWORD set and no STAFF_PASSWORD, no staff logins are created."""
    return os.getenv("STAFF_PASSWORD") or (DEMO_PASSWORD if is_demo() else None)


def ensure_officer():
    """Create / refresh the configured accounts on startup."""
    user = os.getenv("OFFICER_USER", DEMO_USER)
    accounts = [({"username": user, "name": os.getenv("OFFICER_NAME", "Duty Officer"), "role": "admin", "department": None},
                 os.getenv("OFFICER_PASSWORD") or DEMO_PASSWORD)]
    if staff_password():
        accounts += [(a, staff_password()) for a in staff_accounts()]
    with db.conn() as c:
        c.execute("DELETE FROM officers")  # configured accounts only; stale ones never linger
        for a, password in accounts:
            salt = secrets.token_bytes(16)
            c.execute("INSERT OR REPLACE INTO officers(username, name, salt, pw_hash, demo, role, department) VALUES (?,?,?,?,?,?,?)",
                      (a["username"], a["name"], salt, _hash(password, salt), int(is_demo()), a["role"], a["department"]))


def scope(officer: dict) -> str | None:
    """The department a department head is limited to; None = sees every department."""
    return officer.get("d") if officer.get("r") == "department" else None


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _sign(payload: str) -> str:
    return _b64(hmac.new(SECRET, payload.encode(), hashlib.sha256).digest())


def login(username: str, password: str) -> dict:
    # what people actually type: a capitalised first letter, spaces copied along with the text
    username, password = username.strip().lower(), password.strip()
    now = time.time()
    recent = [t for t in _fails.get(username, []) if now - t < LOCK_SECONDS]
    if len(recent) >= MAX_FAILS:
        raise HTTPException(429, "Too many failed attempts. Try again in a few minutes.")
    with db.conn() as c:
        row = c.execute("SELECT * FROM officers WHERE LOWER(username)=?", (username,)).fetchone()
    # hash even for unknown users so response time does not reveal which usernames exist
    ok = hmac.compare_digest(_hash(password, row["salt"] if row else b"-" * 16), row["pw_hash"] if row else b"")
    if not ok:
        _fails[username] = recent + [now]
        raise HTTPException(401, "Wrong username or password")
    _fails.pop(username, None)
    role, dept, username = row["role"] or "admin", row["department"], row["username"]
    return {"token": issue({"u": username, "n": row["name"], "r": role, "d": dept}), "username": username,
            "name": row["name"], "role": role, "department": dept}


def issue(claims: dict, hours: int = TOKEN_HOURS) -> str:
    """Signed token. Officer tokens carry "u" (username); citizen tokens carry "c" (citizen id)."""
    payload = _b64(json.dumps({**claims, "exp": int(time.time()) + hours * 3600}).encode())
    return f"{payload}.{_sign(payload)}"


def verify(token: str) -> dict | None:
    payload, _, sig = token.partition(".")
    if not sig or not hmac.compare_digest(sig, _sign(payload)):
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except ValueError:
        return None
    return data if data.get("exp", 0) > time.time() else None


def _bearer(authorization: str | None) -> dict:
    scheme, _, token = (authorization or "").partition(" ")
    return (verify(token) if scheme.lower() == "bearer" else None) or {}


def optional_officer(authorization: str | None = Header(None)) -> dict | None:
    data = _bearer(authorization)
    return data if "u" in data else None  # a citizen token never opens the officer console


def optional_citizen(x_citizen_token: str | None = Header(None)) -> dict | None:
    """Citizens send their token in X-Citizen-Token, so one browser can hold both sessions."""
    data = verify(x_citizen_token or "") or {}
    return data if "c" in data else None


CITIZEN_EXPIRED = "Citizen session expired. Please sign in again."


def citizen_or_anonymous(x_citizen_token: str | None = Header(None)) -> dict | None:
    """Like optional_citizen, but a token that no longer verifies is an error, not an anonymous
    request: otherwise a signed-in citizen's report would be filed without their account."""
    citizen = optional_citizen(x_citizen_token)
    if x_citizen_token and not citizen:
        raise HTTPException(401, CITIZEN_EXPIRED)
    return citizen


def require_officer(authorization: str | None = Header(None)) -> dict:
    """FastAPI dependency for every officer-console endpoint."""
    officer = optional_officer(authorization)
    if not officer:
        raise HTTPException(401, "Officer login required", headers={"WWW-Authenticate": "Bearer"})
    return officer
