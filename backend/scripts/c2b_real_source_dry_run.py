"""Gate B real-source read-only dry-run CLI entry (no Core writes, no import)."""

from __future__ import annotations

import sys

from app.modules.imports_dry_run.gate_b_runner import main

if __name__ == "__main__":
    raise SystemExit(main())
