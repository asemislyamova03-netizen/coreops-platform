"""CLI entry: one-shot flexity-sales lead automation activation."""

from __future__ import annotations

from app.modules.process_overlay.ops.lead_automation_activation import main

if __name__ == "__main__":
    raise SystemExit(main())
