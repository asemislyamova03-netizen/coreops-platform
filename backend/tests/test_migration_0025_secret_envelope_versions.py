"""Alembic revision metadata checks for M8-B2 secret_envelope_versions migration."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = str(BACKEND_ROOT / "alembic.ini")

REVISION_0024 = "0024_task_run_automation_key"
REVISION_0025 = "0025_secret_envelope_versions"
DOWN_REVISION_0025 = REVISION_0024
MIGRATION_FILENAME = "20260723_0025_secret_envelope_versions.py"


def test_0025_migration_revision_chain():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    rev = script.get_revision(REVISION_0025)
    assert rev is not None
    assert rev.down_revision == DOWN_REVISION_0025
    assert len(REVISION_0025) <= 32

    # 0025 remains a single linear ancestor; current head is a later revision.
    heads = script.get_heads()
    assert len(heads) == 1
    assert REVISION_0025 not in heads or heads[0] == REVISION_0025
    walk = list(script.walk_revisions())
    ids = {item.revision for item in walk}
    assert REVISION_0025 in ids


def test_0025_migration_module_importable():
    import importlib.util

    migration_path = BACKEND_ROOT / "alembic" / "versions" / MIGRATION_FILENAME
    assert migration_path.is_file()
    spec = importlib.util.spec_from_file_location("migration_0025", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == REVISION_0025
    assert module.down_revision == DOWN_REVISION_0025
    assert len(module.revision) <= 32
    assert callable(module.upgrade)
    assert callable(module.downgrade)
    src = migration_path.read_text(encoding="utf-8")
    assert "secret_envelope_versions" in src
    assert "uq_secret_envelope_versions_owner_version" in src
    assert "octet_length(ciphertext_nonce) = 12" in src
    assert "octet_length(wrapped_dek_nonce) = 12" in src
    assert "ForeignKey" not in src
    assert "marketing_publishing_connections" not in src


def test_0025_is_ancestor_of_single_head():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    heads = script.get_heads()
    assert len(heads) == 1
    # Walk down from head until we find 0025 (must be on the only branch).
    current = heads[0]
    seen: set[str] = set()
    while current is not None and current not in seen:
        seen.add(current)
        if current == REVISION_0025:
            break
        rev = script.get_revision(current)
        assert rev is not None
        current = rev.down_revision
    assert REVISION_0025 in seen
