"""Tests run against a throw-away SQLite file, never your Postgres database.
The env vars must be set BEFORE the app is imported."""
import os
import tempfile
from pathlib import Path

_db = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key-test-secret-key-0123456789"
