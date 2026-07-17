"""Allowlist and preflight guards for Gate B real-source read-only dry-run."""

from __future__ import annotations

import re
from pathlib import Path

# Gate A confirmed canonical production path (read-only URI only).
PROD_RO_PRIMARY = Path("/var/www/consult_app/instance/consulting_os.db")

IMPORT_WORK_COPY_DIR = Path("/opt/flexity/import_work")
IMPORT_WORK_COPY_PATTERN = re.compile(
    r"^/opt/flexity/import_work/consulting_os_readonly_\d{8}\.db$"
)

BACKUP_ID_PATTERN = re.compile(
    r"^consulting-gate-b-\d{8}-\d{4}-[a-zA-Z0-9_-]+$"
)

REAL_SOURCE_MODE = "real-source-readonly"

DEFAULT_CREATED_BY_USER_ID = "00000000-0000-0000-0000-000000000214"


class AllowlistError(RuntimeError):
    """Raised when source path is not on the Gate B allowlist."""


class BackupIdError(ValueError):
    """Raised when backup ID is missing or invalid."""


class OutputPathError(ValueError):
    """Raised when report output path is unsafe."""


def _normalize_allowlist_path(db_path: str | Path) -> str:
    """Normalize path for allowlist compare (POSIX server paths stay POSIX on dev Windows)."""
    text = str(db_path).replace("\\", "/")
    if text.startswith("/"):
        return text
    return str(Path(db_path).resolve()).replace("\\", "/")


def path_is_allowlisted(db_path: str | Path) -> bool:
    """Return True if path matches an approved real-source location."""
    normalized = _normalize_allowlist_path(db_path)

    if normalized == "/var/www/consult_app/instance/consulting_os.db":
        return True

    if IMPORT_WORK_COPY_PATTERN.match(normalized):
        return True

    return False


def assert_path_allowlisted_for_real_source(db_path: str | Path) -> Path:
    path = Path(db_path)
    normalized = _normalize_allowlist_path(db_path)
    if not path_is_allowlisted(normalized):
        raise AllowlistError(
            "Source path is not on the Gate B allowlist. "
            "Approved: /var/www/consult_app/instance/consulting_os.db "
            "or /opt/flexity/import_work/consulting_os_readonly_YYYYMMDD.db"
        )
    resolved = path.resolve()
    if resolved.is_dir():
        raise AllowlistError(f"Source path is a directory, not a SQLite file: {resolved}")
    if not resolved.exists():
        raise FileNotFoundError(f"SQLite file not found: {resolved}")
    return resolved


def validate_backup_id(backup_id: str | None) -> str:
    value = (backup_id or "").strip()
    if not value:
        raise BackupIdError("--backup-id is required")
    if not BACKUP_ID_PATTERN.match(value):
        raise BackupIdError(
            "Invalid --backup-id format. Expected: consulting-gate-b-YYYYMMDD-HHMM-operator"
        )
    return value


def find_repo_root(start: Path | None = None) -> Path:
    """Flexity repo root (parent of backend/)."""
    if start is None:
        start = Path(__file__).resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "backend" / "app").is_dir() and (candidate / "docs").is_dir():
            return candidate
    raise RuntimeError("Could not locate Flexity repo root")


def _normalize_resolved_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def assert_output_path_safe(
    output_path: str | Path,
    *,
    repo_root: Path | None = None,
    allow_overwrite: bool = False,
) -> Path:
    root = repo_root or find_repo_root()
    path = Path(output_path).resolve()

    if not path.is_absolute():
        raise OutputPathError("--output must be an absolute path outside the git repo")

    repo_normalized = _normalize_resolved_path(root)
    output_normalized = _normalize_resolved_path(path)

    if output_normalized == repo_normalized or output_normalized.startswith(repo_normalized + "/"):
        raise OutputPathError("--output must not be inside the Flexity git repository")

    tests_marker = "/backend/tests/"
    if tests_marker in output_normalized:
        raise OutputPathError("--output must not be under backend/tests/")

    if path.exists() and not allow_overwrite:
        raise OutputPathError(
            f"Output file already exists: {path}. Pass --overwrite to replace explicitly."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    return path
