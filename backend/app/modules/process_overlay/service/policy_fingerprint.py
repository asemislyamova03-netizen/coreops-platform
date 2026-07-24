"""Shared policy fingerprint helpers for Process Overlay publication idempotency."""

from __future__ import annotations

import hashlib
import json
import uuid

from app.modules.process_overlay.policy_schema import PolicySnapshotV1, parse_policy_snapshot
from app.modules.process_overlay.repository import ProcessOverlayRepository


def policy_fingerprint(policy: PolicySnapshotV1 | dict) -> str:
    """Stable SHA-256 of a canonical policy representation.

    Transitions are ordered by (from, to) so list order does not create
    false-positive "policy changed" publishes.
    """
    if isinstance(policy, PolicySnapshotV1):
        data = policy.model_dump()
    else:
        data = parse_policy_snapshot(policy).model_dump()

    transitions = sorted(
        data.get("transitions") or [],
        key=lambda item: (item["from_stage_code"], item["to_stage_code"]),
    )
    data["transitions"] = transitions
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def find_matching_published_version(
    repo: ProcessOverlayRepository,
    *,
    tenant_id: uuid.UUID,
    configuration_id: uuid.UUID,
    fingerprint: str,
):
    """Prefer active published version; else latest published with same fingerprint."""
    config = repo.get_configuration(tenant_id, configuration_id)
    if config is None:
        return None

    if config.active_definition_version_id is not None:
        active = repo.get_definition_version_for_configuration(
            tenant_id,
            configuration_id,
            config.active_definition_version_id,
        )
        if active is not None and policy_fingerprint(active.policy_snapshot_json) == fingerprint:
            return active

    latest = repo.get_latest_definition_version(tenant_id, configuration_id)
    if latest is not None and policy_fingerprint(latest.policy_snapshot_json) == fingerprint:
        return latest
    return None


__all__ = ["find_matching_published_version", "policy_fingerprint"]
