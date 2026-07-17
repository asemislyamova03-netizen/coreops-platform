"""Staging write-import CLI entry (implementation-gated).

Plan mode (default path without --allow-execution on execute mode):
  staging-write-import-plan — no Core/Postgres writes.

Execute mode:
  staging-write-import-execute — requires --allow-execution AND
  CONSULTING_STAGING_DATABASE_URL. Never writes via app DATABASE_URL.
  Connected PostgreSQL current_database() must match --target-db.

This is not Gate B dry-run; dry-run scripts remain read-only.
"""

from __future__ import annotations

from app.modules.imports_dry_run.staging_write_import_runner import main

if __name__ == "__main__":
    raise SystemExit(main())
