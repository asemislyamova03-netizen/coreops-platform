"""Alembic revision + enum NAME-storage invariants for M8-C2a migration 0018.

SQLite create_all / static audits are not PostgreSQL proof.
Repeated disposable PG smoke remains mandatory before M8-C2a final acceptance.
"""

from __future__ import annotations

import importlib.util
import re
import uuid
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

from app.modules.marketing.enums import (
    MarketingMediaAssetStatus,
    MarketingMediaValidationStatus,
)
from app.modules.marketing.models import MarketingMediaAsset

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = str(BACKEND_ROOT / "alembic.ini")

REVISION_0018 = "0018_mkt_storage_profiles"
DOWN_REVISION_0018 = "0017_mkt_secret_binding"
MIGRATION_FILENAME = "20260716_0018_mkt_storage_profiles.py"
MIGRATION_PATH = BACKEND_ROOT / "alembic" / "versions" / MIGRATION_FILENAME

# Canonical SQLAlchemy Enum NAME storage (matches ORM / existing PG convention).
ENUM_NAMES = (
    "LEGACY_UNVERIFIED",
    "VALIDATED_METADATA",
    "REGISTERED_UNVERIFIED",
    "REJECTED",
    "ARCHIVED",
    "FLEXITY_MANAGED",
    "CLIENT_PUBLIC_URL",
    "CLIENT_BUCKET",
    "ACTIVE",
    "DISABLED",
)
FORBIDDEN_LOWERCASE_DEFAULTS = (
    "legacy_unverified",
    "validated_metadata",
    "registered_unverified",
    "flexity_managed",
    "client_public_url",
    "client_bucket",
    "active",
    "disabled",
    "rejected",
    "archived",
)


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("migration_0018", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_0018_migration_revision_chain():
    script = ScriptDirectory.from_config(Config(ALEMBIC_INI))
    rev = script.get_revision(REVISION_0018)
    assert rev is not None
    assert rev.down_revision == DOWN_REVISION_0018
    assert len(REVISION_0018) <= 32

    head = script.get_current_head()
    assert head == REVISION_0018
    assert script.get_heads() == [REVISION_0018]

    # Prior chain intact
    assert script.get_revision("0017_mkt_secret_binding").down_revision == "0016_mkt_publishing_conn"
    assert script.get_revision("0016_mkt_publishing_conn").down_revision == "0015_marketing_cabinet_mvp"


def test_0018_migration_module_importable():
    module = _load_migration_module()
    assert module.revision == REVISION_0018
    assert module.down_revision == DOWN_REVISION_0018
    assert len(module.revision) <= 32
    assert callable(module.upgrade)
    assert callable(module.downgrade)


def test_0018_enum_name_storage_invariants_in_migration_source():
    """All 0018 enum server_defaults / CHECK / index predicates must use NAME storage.

    This catches the PG smoke failure class: lowercase server_default vs uppercase CHECK.
    Not a substitute for disposable PostgreSQL smoke.
    """
    src = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'server_default="LEGACY_UNVERIFIED"' in src
    assert 'server_default="DISABLED"' in src

    for bad in FORBIDDEN_LOWERCASE_DEFAULTS:
        assert f'server_default="{bad}"' not in src
        assert f"server_default='{bad}'" not in src

    # CHECK / partial-index predicates must quote uppercase names, not values.
    required_fragments = (
        "'LEGACY_UNVERIFIED'",
        "'REGISTERED_UNVERIFIED'",
        "'VALIDATED_METADATA'",
        "'FLEXITY_MANAGED'",
        "'CLIENT_PUBLIC_URL'",
        "'CLIENT_BUCKET'",
        "status = 'ACTIVE'",
        "mode = 'CLIENT_BUCKET'",
        "status IN ('ACTIVE','DISABLED')",
    )
    for fragment in required_fragments:
        assert fragment in src, f"missing uppercase predicate fragment: {fragment}"

    forbidden_predicate_fragments = (
        "status = 'active'",
        "status = 'disabled'",
        "mode = 'client_bucket'",
        "mode = 'flexity_managed'",
        "'legacy_unverified'",
        "'validated_metadata'",
        "'registered_unverified'",
        "'flexity_managed'",
        "'client_public_url'",
        "'client_bucket'",
        "'active'",
        "'disabled'",
    )
    for fragment in forbidden_predicate_fragments:
        assert fragment not in src, f"lowercase enum predicate found: {fragment}"

    assert "verified_size_bytes" in src
    assert "ck_marketing_media_verified_size_nonneg" in src
    assert "ck_marketing_media_declared_size_nonneg" in src
    assert "drop_column(\"marketing_media_assets\", \"verified_size_bytes\")" in src


def test_0018_sa_enum_constructors_use_member_names():
    """sa.Enum(...) positional args in 0018 upgrade must be uppercase member names."""
    src = MIGRATION_PATH.read_text(encoding="utf-8")
    upgrade_src = src.split("def downgrade", 1)[0]
    blocks = re.findall(r"sa\.Enum\((.*?)\)", upgrade_src, flags=re.DOTALL)
    assert blocks, "expected sa.Enum constructors in upgrade()"
    for block in blocks:
        tokens = re.findall(r'"([A-Za-z0-9_]+)"', block)
        member_tokens = [t for t in tokens if not t.startswith("marketing_")]
        assert member_tokens, f"sa.Enum block missing NAME tokens: {block[:120]}"
        for token in member_tokens:
            assert token == token.upper(), f"sa.Enum must use NAME not value: {token}"
            assert token in ENUM_NAMES, f"unexpected enum token in 0018: {token}"


def test_pre_0018_style_media_row_defaults_to_legacy_unverified(db_session):
    """Existing media rows (no validation fields set) get LEGACY_UNVERIFIED + NULL sizes.

    Uses create_all schema (SQLite/test). Confirms ORM server_default NAME semantics.
    Disposable PG smoke still required for real alembic upgrade path.
    """
    from app.core.enums import TenantStatus
    from app.modules.provider.models import ProviderCompany
    from app.modules.tenants.models import Tenant

    provider = ProviderCompany(
        name="C2a Mig Provider",
        slug=f"c2a-mig-{uuid.uuid4().hex[:8]}",
        is_active=True,
    )
    db_session.add(provider)
    db_session.flush()
    tenant = Tenant(
        provider_company_id=provider.id,
        name="C2a Mig Tenant",
        slug=f"c2a-mig-t-{uuid.uuid4().hex[:8]}",
        status=TenantStatus.ACTIVE,
    )
    db_session.add(tenant)
    db_session.commit()

    asset = MarketingMediaAsset(
        tenant_id=tenant.id,
        pack_id=None,
        role="instagram_feed",
        file_name="pre0018.png",
        mime_type="image/png",
        storage_provider="git_path",
        storage_key="content/packs/pre0018/feed.png",
        public_url="https://example.com/pre0018.png",
        status=MarketingMediaAssetStatus.STORED,
        metadata_json={},
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    assert asset.validation_status == MarketingMediaValidationStatus.LEGACY_UNVERIFIED
    assert asset.validation_status.name == "LEGACY_UNVERIFIED"
    assert asset.verified_size_bytes is None
    assert asset.declared_size_bytes is None
    assert asset.verified_mime_type is None
    assert asset.storage_profile_id is None
    assert asset.resource_mode is None


def test_0018_model_columns_include_verified_size_bytes(db_engine):
    columns = {col["name"] for col in inspect(db_engine).get_columns("marketing_media_assets")}
    assert "verified_size_bytes" in columns
    assert "declared_size_bytes" in columns
    assert "validation_status" in columns
