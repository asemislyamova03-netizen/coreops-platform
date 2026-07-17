"""Staging write-import CLI entry (implementation-gated, no execution by default)."""

from __future__ import annotations

from app.modules.imports_dry_run.staging_write_import_runner import main

if __name__ == "__main__":
    raise SystemExit(main())

