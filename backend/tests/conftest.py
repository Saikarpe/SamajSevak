"""Run the tests against a throwaway database (and uploads / signing key next to it), never the real one.
Set before any app module is imported, because db.DB_PATH is read at import time."""
import os
import tempfile

os.environ["SAMAJSEVAK_DB"] = os.path.join(tempfile.mkdtemp(prefix="samajsevak-test-"), "samajsevak.db")
