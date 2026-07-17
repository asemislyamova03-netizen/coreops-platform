"""Read-only SQLite connection helpers for C2b synthetic/local and Gate B real-source access."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Literal

from app.modules.imports_dry_run.real_source_allowlist import assert_path_allowlisted_for_real_source

BLOCKED_PATH_FRAGMENTS = (
    "consulting_os.db",
    "/var/www/consult_app",
    "\\var\\www\\consult_app",
)

PathGuardMode = Literal["synthetic", "real_source"]


class SqliteWriteAttemptError(RuntimeError):
    """Raised when a write is possible or attempted on a connection that must be read-only."""


class BlockedSqlitePathError(RuntimeError):
    """Raised when path looks like production legacy DB (forbidden in synthetic C2b mode)."""


def assert_path_allowed_for_c2b_synthetic(db_path: str | Path) -> Path:
    path = Path(db_path).resolve()
    normalized = str(path).replace("\\", "/").lower()
    for fragment in BLOCKED_PATH_FRAGMENTS:
        if fragment.lower().replace("\\", "/") in normalized:
            raise BlockedSqlitePathError(
                f"Refusing path that matches production/legacy DB pattern: {fragment}"
            )
    if not path.exists():
        raise FileNotFoundError(f"SQLite file not found: {path}")
    return path


# Backward-compatible alias for synthetic C2b tests and scripts.
def assert_path_allowed_for_c2b(db_path: str | Path) -> Path:
    return assert_path_allowed_for_c2b_synthetic(db_path)


def open_readonly_sqlite_uri(
    db_path: str | Path,
    *,
    path_guard: PathGuardMode = "synthetic",
) -> sqlite3.Connection:
    if path_guard == "synthetic":
        path = assert_path_allowed_for_c2b_synthetic(db_path)
    elif path_guard == "real_source":
        path = assert_path_allowlisted_for_real_source(db_path)
    else:
        raise ValueError(f"Unsupported path_guard: {path_guard}")

    uri = path.as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    assert_connection_is_readonly(conn)
    return conn


def open_readonly_sqlite(db_path: str | Path) -> sqlite3.Connection:
    """Open SQLite in URI read-only mode for synthetic/local sources (production paths blocked)."""
    return open_readonly_sqlite_uri(db_path, path_guard="synthetic")


def open_readonly_sqlite_real_source(db_path: str | Path) -> sqlite3.Connection:
    """Open allowlisted production source SQLite in URI read-only mode."""
    return open_readonly_sqlite_uri(db_path, path_guard="real_source")


def assert_connection_is_readonly(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("CREATE TABLE __flexity_ro_probe__(id INTEGER)")
    except sqlite3.OperationalError:
        return
    try:
        conn.execute("DROP TABLE IF EXISTS __flexity_ro_probe__")
    except sqlite3.Error:
        pass
    raise SqliteWriteAttemptError("SQLite connection is writable; read-only mode required")
