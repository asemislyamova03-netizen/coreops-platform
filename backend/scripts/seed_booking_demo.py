"""CLI entrypoint for explicit Booking demo seed (not run on app startup)."""

from __future__ import annotations

import argparse
import sys
import uuid

from app.core.database import SessionLocal
from app.modules.booking.seed import resolve_tenant, seed_demo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed Flexity Booking demo data for a tenant")
    parser.add_argument("--tenant-slug", help="Tenant slug to seed")
    parser.add_argument("--tenant-id", help="Tenant UUID to seed")
    args = parser.parse_args(argv)

    if not args.tenant_slug and not args.tenant_id:
        parser.error("Provide --tenant-slug or --tenant-id")

    tenant_id = uuid.UUID(args.tenant_id) if args.tenant_id else None

    db = SessionLocal()
    try:
        tenant = resolve_tenant(db, tenant_id=tenant_id, tenant_slug=args.tenant_slug)
        result = seed_demo(db, tenant.id)
        print(
            "Booking demo seed OK:",
            f"tenant={tenant.slug}",
            f"territory={result.territory_id}",
            f"owners={len(result.owner_ids)}",
            f"objects={len(result.object_ids)}",
            f"order={result.order_id}",
        )
        return 0
    except Exception as exc:
        print(f"Booking demo seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
