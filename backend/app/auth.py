"""Officer authentication: salted PBKDF2 password hashes and HMAC-signed bearer tokens.
Standard library only.

Accounts come from the environment (OFFICER_USER / OFFICER_PASSWORD / OFFICER_NAME).
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

DEMO_USER, DEMO_PASSWORD = "officer", "samajsevak-demo"
# without SAMAJSEVAK_SECRET the key is random per process, so a restart signs everyone out
SECRET = os.getenv("SAMAJSEVAK_SECRET", "").encode() or secrets.token_bytes(32)
TOKEN_HOURS = 8
MAX_FAILS, LOCK_SECONDS = 5, 300
_fails: dict[str, list[float]] = {}


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)


def is_demo() -> bool:
    return not os.getenv("OFFICER_PASSWORD")


def ensure_officer():
    """Create / refresh the configured account on startup."""
    user = os.getenv("OFFICER_USER", DEMO_USER)
    password = os.getenv("OFFICER_PASSWORD") or DEMO_PASSWORD
    salt = secrets.token_bytes(16)
    with db.conn() as c:
        c.execute("DELETE FROM officers")  # single configured account; stale ones never linger
        c.execute("INSERT OR REPLACE INTO officers(username, name, salt, pw_hash, demo) VALUES (?,?,?,?,?)",
                  (user, os.getenv("OFFICER_NAME", "Duty Officer"), salt, _hash(password, salt), int(is_demo())))


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _sign(payload: str) -> str:
    return _b64(hmac.new(SECRET, payload.encode(), hashlib.sha256).digest())


def login(username: str, password: str) -> dict:
    now = time.time()
    recent = [t for t in _fails.get(username, []) if now - t < LOCK_SECONDS]
    if len(recent) >= MAX_FAILS:
        raise HTTPException(429, "Too many failed attempts. Try again in a few minutes.")
    with db.conn() as c:
        row = c.execute("SELECT * FROM officers WHERE username=?", (username,)).fetchone()
    # hash even for unknown users so response time does not reveal which usernames exist
    ok = hmac.compare_digest(_hash(password, row["salt"] if row else b"-" * 16), row["pw_hash"] if row else b"")
    if not ok:
        _fails[username] = recent + [now]
        raise HTTPException(401, "Wrong username or password")
    _fails.pop(username, None)
    return {"token": issue({"u": username, "n": row["name"]}), "username": username, "name": row["name"]}


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


def require_officer(authorization: str | None = Header(None)) -> dict:
    """FastAPI dependency for every officer-console endpoint."""
    officer = optional_officer(authorization)
    if not officer:
        raise HTTPException(401, "Officer login required", headers={"WWW-Authenticate": "Bearer"})
    return officer
