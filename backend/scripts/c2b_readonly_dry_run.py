"""Local C2b dry-run using synthetic SQLite fixture only (no production DB)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from app.modules.imports_dry_run.pipeline import DryRunNoOpTargetAdapter, SyntheticDryRunPipeline
from app.modules.imports_dry_run.schemas import SyntheticDryRunContext
from app.modules.imports_dry_run.sqlite_source_adapter import ReadonlySqliteSourceAdapter
from app.modules.imports_dry_run.synthetic_sqlite_fixture import build_synthetic_sqlite_fixture


def main() -> None:
    # Prefer regenerating under tests/_c2b_tmp; also refresh canonical fixture (synthetic only).
    repo_fixture = (
        Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "consulting_legacy_min.sqlite"
    )
    work_dir = Path(__file__).resolve().parents[1] / "tests" / "_c2b_tmp" / "script_run"
    work_dir.mkdir(parents=True, exist_ok=True)
    db_path = work_dir / "consulting_legacy_min.sqlite"
    build_synthetic_sqlite_fixture(db_path)
    build_synthetic_sqlite_fixture(repo_fixture)

    source = ReadonlySqliteSourceAdapter(db_path)
    pipeline = SyntheticDryRunPipeline(source=source, target=DryRunNoOpTargetAdapter())
    result = pipeline.run(
        SyntheticDryRunContext(
            tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000211"),
            default_branch_id=uuid.UUID("00000000-0000-0000-0000-000000000212"),
            created_by_user_id=uuid.UUID("00000000-0000-0000-0000-000000000213"),
            source_system="legacy_consult_app",
            scenario_name="c2b_synthetic_sqlite",
        )
    )
    print(
        json.dumps(
            {
                "summary": result.summary.model_dump(mode="json"),
                "report": {
                    "duplicate_warnings": result.report.duplicate_warnings,
                    "orphan_warnings": result.report.orphan_warnings,
                    "unknown_status_warnings": result.report.unknown_status_warnings,
                    "required_field_errors": result.report.required_field_errors,
                    "finance_check": result.report.finance_check.model_dump(mode="json"),
                    "tenant_branch_readiness": result.report.tenant_branch_readiness.model_dump(
                        mode="json"
                    ),
                    "issue_codes": sorted({i.issue_code for i in result.report.issues}),
                },
                "source": {
                    "system": source.source_system,
                    "schema_fingerprint": source.last_schema_fingerprint,
                    "row_counts": source.last_row_counts,
                    "db_path_is_repo_local": "tests" in str(db_path).replace("\\", "/"),
                },
                "target_endpoint_checks": [
                    {
                        "endpoint": item.endpoint,
                        "schema_name": item.schema_name,
                        "status": item.status,
                        "note": item.note,
                    }
                    for item in pipeline.target.endpoint_checks
                ],
                "notes": "C2b synthetic SQLite only. No production DB. No Core writes.",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
