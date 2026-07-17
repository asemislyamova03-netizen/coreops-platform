"""Gate B real-source read-only dry-run runner (no Core writes, no import)."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from app.modules.imports_dry_run.masked_report import (
    assert_target_is_noop,
    build_masked_gate_b_report,
    write_masked_report,
)
from app.modules.imports_dry_run.pipeline import DryRunNoOpTargetAdapter, SyntheticDryRunPipeline
from app.modules.imports_dry_run.real_source_allowlist import (
    DEFAULT_CREATED_BY_USER_ID,
    REAL_SOURCE_MODE,
    AllowlistError,
    BackupIdError,
    OutputPathError,
    assert_output_path_safe,
    assert_path_allowlisted_for_real_source,
    find_repo_root,
    validate_backup_id,
)
from app.modules.imports_dry_run.schemas import SyntheticDryRunContext
from app.modules.imports_dry_run.sqlite_source_adapter import ReadonlySqliteSourceAdapter

EXIT_PREFLIGHT_FAIL = 2


class GateBPreflightError(Exception):
    """Fail-closed preflight validation error."""


@dataclass(frozen=True)
class GateBConfig:
    source_db: Path
    backup_id: str
    tenant_id: UUID
    default_branch_id: UUID
    output: Path
    created_by_user_id: UUID
    scenario_name: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gate B real-source read-only dry-run (masked report only, no Core writes)."
    )
    parser.add_argument(
        "--mode",
        required=True,
        help="Must be 'real-source-readonly'",
    )
    parser.add_argument("--source-db", required=True, help="Allowlisted absolute path to source SQLite")
    parser.add_argument("--backup-id", required=True, help="Recorded backup ID per runbook")
    parser.add_argument("--tenant-id", required=True, help="Staging dry-run tenant UUID")
    parser.add_argument("--default-branch-id", required=True, help="Tenant default branch UUID")
    parser.add_argument(
        "--output",
        required=True,
        help="Absolute path for masked JSON report (outside git repo)",
    )
    parser.add_argument(
        "--created-by-user-id",
        default=DEFAULT_CREATED_BY_USER_ID,
        help="Optional audit user UUID",
    )
    parser.add_argument(
        "--scenario-name",
        default="gate_b_real_source_readonly",
        help="Dry-run scenario label",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing --output file",
    )
    return parser


def validate_gate_b_args(args: argparse.Namespace, *, repo_root: Path | None = None) -> GateBConfig:
    if args.mode != REAL_SOURCE_MODE:
        raise GateBPreflightError(f"--mode must be '{REAL_SOURCE_MODE}'")

    try:
        backup_id = validate_backup_id(args.backup_id)
    except BackupIdError as exc:
        raise GateBPreflightError(str(exc)) from exc

    try:
        tenant_id = UUID(args.tenant_id)
    except ValueError as exc:
        raise GateBPreflightError(f"Invalid --tenant-id UUID: {args.tenant_id}") from exc

    try:
        default_branch_id = UUID(args.default_branch_id)
    except ValueError as exc:
        raise GateBPreflightError(
            f"Invalid --default-branch-id UUID: {args.default_branch_id}"
        ) from exc

    try:
        created_by_user_id = UUID(args.created_by_user_id)
    except ValueError as exc:
        raise GateBPreflightError(
            f"Invalid --created-by-user-id UUID: {args.created_by_user_id}"
        ) from exc

    try:
        source_db = assert_path_allowlisted_for_real_source(args.source_db)
    except (AllowlistError, FileNotFoundError) as exc:
        raise GateBPreflightError(str(exc)) from exc

    try:
        output = assert_output_path_safe(
            args.output,
            repo_root=repo_root,
            allow_overwrite=bool(args.overwrite),
        )
    except OutputPathError as exc:
        raise GateBPreflightError(str(exc)) from exc

    return GateBConfig(
        source_db=source_db,
        backup_id=backup_id,
        tenant_id=tenant_id,
        default_branch_id=default_branch_id,
        output=output,
        created_by_user_id=created_by_user_id,
        scenario_name=args.scenario_name,
    )


def run_gate_b_dry_run(config: GateBConfig) -> dict:
    source = ReadonlySqliteSourceAdapter(
        config.source_db,
        schema_profile="production_gate_b",
        path_guard="real_source",
    )
    target = DryRunNoOpTargetAdapter()
    assert_target_is_noop(target)

    pipeline = SyntheticDryRunPipeline(source=source, target=target)
    result = pipeline.run(
        SyntheticDryRunContext(
            tenant_id=config.tenant_id,
            default_branch_id=config.default_branch_id,
            created_by_user_id=config.created_by_user_id,
            source_system="legacy_consult_app",
            scenario_name=config.scenario_name,
        )
    )

    return build_masked_gate_b_report(
        result=result,
        pipeline=pipeline,
        source_system=source.source_system,
        scenario_name=config.scenario_name,
        backup_id=config.backup_id,
        source_db_path=config.source_db,
        schema_fingerprint=source.last_schema_fingerprint,
        row_counts=source.last_row_counts,
        tenant_id=config.tenant_id,
        default_branch_id=config.default_branch_id,
        amount_reconciliation_summary=source.last_amount_reconciliation_summary,
        services_mapping_summary=source.last_services_mapping_summary,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = validate_gate_b_args(args, repo_root=find_repo_root())
        report = run_gate_b_dry_run(config)
        write_masked_report(report, config.output)
    except GateBPreflightError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_PREFLIGHT_FAIL
    except Exception as exc:
        print(f"Gate B dry-run failed: {exc}", file=sys.stderr)
        return EXIT_PREFLIGHT_FAIL

    print(f"Masked report written: {config.output}")
    return 0
