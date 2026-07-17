"""M8-C2a hardened storage profiles + Mode A/B media boundary tests."""

from __future__ import annotations

import json
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.enums import TenantStatus
from app.core.object_storage.adapters.in_memory import InMemoryStorage
from app.core.object_storage.content_validation import DeclaredMimeMagicByteValidator
from app.core.object_storage.port import StorageError, StorageObjectRef
from app.modules.audit.models import AuditLog
from app.modules.marketing.enums import (
    MarketingMediaAssetStatus,
    MarketingMediaValidationStatus,
    MarketingStorageProfileStatus,
    MarketingStorageResourceMode,
)
from app.modules.marketing.exceptions import (
    MarketingManagedMediaLifecycleError,
    MarketingPublicUrlValidationError,
    MarketingStorageProfileDuplicateActiveError,
    MarketingStorageProfileNotFoundError,
    MarketingStorageProfileValidationError,
)
from app.modules.marketing.models import MarketingMediaAsset
from app.modules.marketing.service.managed_media_lifecycle import (
    ManagedMediaLifecycleService,
)
from app.modules.marketing.service.public_url_media import PublicUrlMediaRegistrationService
from app.modules.marketing.service.public_url_validator import validate_public_url
from app.modules.marketing.service.storage_profiles import MarketingStorageProfileService
from app.modules.provider.models import ProviderCompany
from app.modules.tenants.models import Tenant

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def _factory(db_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


def _create_tenant(db_session, slug: str) -> Tenant:
    provider = ProviderCompany(name=f"Provider {slug}", slug=f"prov-{slug}", is_active=True)
    db_session.add(provider)
    db_session.flush()
    tenant = Tenant(
        provider_company_id=provider.id,
        name=f"Tenant {slug}",
        slug=slug,
        status=TenantStatus.ACTIVE,
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant


def test_mode_a_and_mode_b_active_simultaneously(db_session):
    tenant = _create_tenant(db_session, "c2a-both")
    svc = MarketingStorageProfileService(db_session, tenant.id)
    a = svc.create_profile(
        mode=MarketingStorageResourceMode.FLEXITY_MANAGED,
        display_name="Managed",
        status=MarketingStorageProfileStatus.ACTIVE,
    )
    b = svc.create_profile(
        mode=MarketingStorageResourceMode.CLIENT_PUBLIC_URL,
        display_name="Public",
        status=MarketingStorageProfileStatus.ACTIVE,
    )
    db_session.commit()
    assert a.status == MarketingStorageProfileStatus.ACTIVE
    assert b.status == MarketingStorageProfileStatus.ACTIVE
    assert svc.get_active_storage_profile(MarketingStorageResourceMode.FLEXITY_MANAGED) is not None
    assert svc.get_active_storage_profile(MarketingStorageResourceMode.CLIENT_PUBLIC_URL) is not None


def test_second_active_same_mode_rejected(db_session):
    tenant = _create_tenant(db_session, "c2a-dup-mode")
    svc = MarketingStorageProfileService(db_session, tenant.id)
    svc.create_profile(
        mode=MarketingStorageResourceMode.FLEXITY_MANAGED,
        display_name="A1",
        status=MarketingStorageProfileStatus.ACTIVE,
    )
    db_session.flush()
    with pytest.raises(MarketingStorageProfileDuplicateActiveError):
        svc.create_profile(
            mode=MarketingStorageResourceMode.FLEXITY_MANAGED,
            display_name="A2",
            status=MarketingStorageProfileStatus.ACTIVE,
        )


def test_one_default_per_tenant_and_default_requires_active(db_session):
    tenant = _create_tenant(db_session, "c2a-default")
    svc = MarketingStorageProfileService(db_session, tenant.id)
    with pytest.raises(MarketingStorageProfileValidationError, match="default_requires_active"):
        svc.create_profile(
            mode=MarketingStorageResourceMode.FLEXITY_MANAGED,
            display_name="Disabled default",
            status=MarketingStorageProfileStatus.DISABLED,
            is_default=True,
        )
    first = svc.create_profile(
        mode=MarketingStorageResourceMode.FLEXITY_MANAGED,
        display_name="Default A",
        status=MarketingStorageProfileStatus.ACTIVE,
        is_default=True,
    )
    db_session.flush()
    with pytest.raises(MarketingStorageProfileValidationError, match="default_already_exists"):
        svc.create_profile(
            mode=MarketingStorageResourceMode.CLIENT_PUBLIC_URL,
            display_name="B wants default",
            status=MarketingStorageProfileStatus.ACTIVE,
            is_default=True,
        )
    second = svc.create_profile(
        mode=MarketingStorageResourceMode.CLIENT_PUBLIC_URL,
        display_name="B",
        status=MarketingStorageProfileStatus.ACTIVE,
    )
    db_session.flush()
    # set_default clears previous
    svc.set_default_profile(second.id)
    db_session.commit()
    assert svc.get_default_profile().id == second.id
    assert not svc.get_profile(first.id).is_default


def test_client_bucket_rejected(db_session):
    tenant = _create_tenant(db_session, "c2a-bucket")
    svc = MarketingStorageProfileService(db_session, tenant.id)
    with pytest.raises(MarketingStorageProfileValidationError, match="client_bucket"):
        svc.create_profile(
            mode=MarketingStorageResourceMode.CLIENT_BUCKET,
            display_name="Bucket",
        )


def test_both_asset_types_same_tenant(db_engine, db_session):
    tenant = _create_tenant(db_session, "c2a-dual-assets")
    svc = MarketingStorageProfileService(db_session, tenant.id)
    svc.create_profile(
        mode=MarketingStorageResourceMode.FLEXITY_MANAGED,
        display_name="Managed",
        status=MarketingStorageProfileStatus.ACTIVE,
    )
    svc.create_profile(
        mode=MarketingStorageResourceMode.CLIENT_PUBLIC_URL,
        display_name="Public",
        status=MarketingStorageProfileStatus.ACTIVE,
    )
    db_session.commit()

    life = ManagedMediaLifecycleService(
        tenant.id,
        session_factory=_factory(db_engine),
        storage=InMemoryStorage(app_env="test"),
    )
    managed = life.store_managed_media(
        pack_id=None,
        file_name="hero.png",
        mime_type="image/png",
        data=_PNG,
    )
    pub = PublicUrlMediaRegistrationService(db_session, tenant.id).register_public_url(
        pack_id=None,
        file_name="remote.png",
        mime_type="image/png",
        public_url="https://cdn.example.com/img/remote.png",
    )
    db_session.commit()
    assert managed.resource_mode == MarketingStorageResourceMode.FLEXITY_MANAGED
    assert pub.resource_mode == MarketingStorageResourceMode.CLIENT_PUBLIC_URL
    assert managed.validation_status == MarketingMediaValidationStatus.VALIDATED_METADATA
    assert pub.validation_status == MarketingMediaValidationStatus.REGISTERED_UNVERIFIED
    assert managed.verified_size_bytes == len(_PNG)
    assert managed.declared_size_bytes is None
    assert pub.verified_size_bytes is None
    assert pub.declared_size_bytes is None


def test_selection_strictly_by_mode(db_engine, db_session):
    tenant = _create_tenant(db_session, "c2a-select")
    svc = MarketingStorageProfileService(db_session, tenant.id)
    # Only Mode B active — Mode A must fail (not fall back to B)
    svc.create_profile(
        mode=MarketingStorageResourceMode.CLIENT_PUBLIC_URL,
        display_name="Public",
        status=MarketingStorageProfileStatus.ACTIVE,
        is_default=True,
    )
    db_session.commit()
    life = ManagedMediaLifecycleService(
        tenant.id,
        session_factory=_factory(db_engine),
        storage=InMemoryStorage(app_env="test"),
    )
    with pytest.raises(MarketingStorageProfileNotFoundError):
        life.store_managed_media(
            pack_id=None,
            file_name="x.png",
            mime_type="image/png",
            data=_PNG,
        )


def test_storage_object_ref_redaction():
    tid = uuid.uuid4()
    aid = uuid.uuid4()
    ref = StorageObjectRef(
        tenant_id=tid,
        _object_key=f"marketing/tenants/{tid}/media/{aid}/a.png",
    )
    text = repr(ref) + str(ref)
    assert "marketing/tenants" not in text
    assert ref.redacted_id.startswith("objref:")
    with pytest.raises(TypeError):
        dict(ref)  # type: ignore[arg-type]


def test_media_resource_serialization_hides_key(db_engine, db_session):
    tenant = _create_tenant(db_session, "c2a-opaque")
    MarketingStorageProfileService(db_session, tenant.id).create_profile(
        mode=MarketingStorageResourceMode.FLEXITY_MANAGED,
        display_name="Managed",
        status=MarketingStorageProfileStatus.ACTIVE,
    )
    db_session.commit()
    life = ManagedMediaLifecycleService(
        tenant.id,
        session_factory=_factory(db_engine),
        storage=InMemoryStorage(app_env="test"),
    )
    view = life.store_managed_media(
        pack_id=None,
        file_name="hero.png",
        mime_type="image/png",
        data=_PNG,
    )
    resource = life.resolve_resource(view.id)
    dumped = json.dumps(resource.model_dump())
    assert "marketing/tenants" not in dumped
    assert "marketing/tenants" not in repr(resource)
    assert "file://" not in dumped
    assert resource.size_bytes == len(_PNG)
    assert view.verified_size_bytes == len(_PNG)
    assert view.declared_size_bytes is None


def test_in_memory_storage_runtime_guard():
    with pytest.raises(StorageError, match="forbidden"):
        InMemoryStorage(app_env="production")
    with pytest.raises(StorageError, match="forbidden"):
        InMemoryStorage(app_env="")
    assert InMemoryStorage(app_env="test") is not None


def test_mode_a_db_failure_orphan_cleanup(db_engine, db_session):
    tenant = _create_tenant(db_session, "c2a-orphan")
    MarketingStorageProfileService(db_session, tenant.id).create_profile(
        mode=MarketingStorageResourceMode.FLEXITY_MANAGED,
        display_name="Managed",
        status=MarketingStorageProfileStatus.ACTIVE,
    )
    db_session.commit()
    storage = InMemoryStorage(app_env="test")

    def _failing_session():
        session = _factory(db_engine)()

        def boom():
            raise RuntimeError("forced_db_commit_failure")

        session.commit = boom  # type: ignore[method-assign]
        return session

    life_fail = ManagedMediaLifecycleService(
        tenant.id,
        session_factory=_failing_session,
        storage=storage,
    )
    with pytest.raises(MarketingManagedMediaLifecycleError, match="managed_media_store_failed"):
        life_fail.store_managed_media(
            pack_id=None,
            file_name="orphan.png",
            mime_type="image/png",
            data=_PNG,
        )
    assert len(storage._objects) == 0


def test_compensation_failure_safe_code(db_engine, db_session):
    tenant = _create_tenant(db_session, "c2a-comp-fail")
    MarketingStorageProfileService(db_session, tenant.id).create_profile(
        mode=MarketingStorageResourceMode.FLEXITY_MANAGED,
        display_name="Managed",
        status=MarketingStorageProfileStatus.ACTIVE,
    )
    db_session.commit()
    storage = InMemoryStorage(app_env="test")

    def _failing_session():
        session = _factory(db_engine)()

        def boom():
            raise RuntimeError("forced_db_commit_failure")

        session.commit = boom  # type: ignore[method-assign]
        return session

    life = ManagedMediaLifecycleService(
        tenant.id,
        session_factory=_failing_session,
        storage=storage,
    )
    with patch.object(storage, "delete_object", side_effect=StorageError("boom")):
        with pytest.raises(
            MarketingManagedMediaLifecycleError, match="storage_orphan_compensation_failed"
        ):
            life.store_managed_media(
                pack_id=None,
                file_name="x.png",
                mime_type="image/png",
                data=_PNG,
            )


def test_mode_a_post_commit_does_not_delete_bound(db_engine, db_session):
    tenant = _create_tenant(db_session, "c2a-bound")
    MarketingStorageProfileService(db_session, tenant.id).create_profile(
        mode=MarketingStorageResourceMode.FLEXITY_MANAGED,
        display_name="Managed",
        status=MarketingStorageProfileStatus.ACTIVE,
    )
    db_session.commit()
    storage = InMemoryStorage(app_env="test")
    life = ManagedMediaLifecycleService(
        tenant.id,
        session_factory=_factory(db_engine),
        storage=storage,
    )
    view = life.store_managed_media(
        pack_id=None,
        file_name="kept.png",
        mime_type="image/png",
        data=_PNG,
    )
    ref = StorageObjectRef(
        tenant_id=tenant.id,
        _object_key=f"marketing/tenants/{tenant.id}/media/{view.id}/kept.png",
    )
    assert storage.contains_ref(ref)


def test_mode_a_caller_session_isolation(db_engine, db_session):
    tenant = _create_tenant(db_session, "c2a-uow")
    MarketingStorageProfileService(db_session, tenant.id).create_profile(
        mode=MarketingStorageResourceMode.FLEXITY_MANAGED,
        display_name="Managed",
        status=MarketingStorageProfileStatus.ACTIVE,
    )
    db_session.commit()
    before = id(db_session)
    ManagedMediaLifecycleService(
        tenant.id,
        session_factory=_factory(db_engine),
        storage=InMemoryStorage(app_env="test"),
    ).store_managed_media(
        pack_id=None,
        file_name="iso.png",
        mime_type="image/png",
        data=_PNG,
    )
    assert id(db_session) == before
    assert db_session.is_active


def test_path_traversal_filename_rejected(db_engine, db_session):
    tenant = _create_tenant(db_session, "c2a-path")
    MarketingStorageProfileService(db_session, tenant.id).create_profile(
        mode=MarketingStorageResourceMode.FLEXITY_MANAGED,
        display_name="Managed",
        status=MarketingStorageProfileStatus.ACTIVE,
    )
    db_session.commit()
    life = ManagedMediaLifecycleService(
        tenant.id,
        session_factory=_factory(db_engine),
        storage=InMemoryStorage(app_env="test"),
    )
    with pytest.raises(MarketingManagedMediaLifecycleError, match="path_traversal"):
        life.store_managed_media(
            pack_id=None,
            file_name="../etc/passwd.png",
            mime_type="image/png",
            data=_PNG,
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://cdn.example.com/a.png",
        "https://user:pass@cdn.example.com/a.png",
        "https://cdn.example.com/a.png?token=abc",
        "https://cdn.example.com/a.png#frag",
        "https://localhost/a.png",
        "https://localhost./a.png",
        "https://intranet/a.png",
        "https://10.0.0.1/a.png",
        "https://127.0.0.1/a.png",
        "https://169.254.169.254/a",
        "https://192.168.1.10/a.png",
        "https://[::1]/a",
        "https://0x7f000001/a",
        "https://2130706433/a",
        "https://0177.0.0.1/a",
        "https://metadata.google.internal/a",
        "https://foo.local/a.png",
        "https://svc.internal/a.png",
        "https://host.lan/a.png",
        "https://cdn.example.com\\@evil.com/a",
        "https://exa mple.com/a",
        "https://\x00evil.com/a",
        "https://пример.рф/a.png",  # raw IDN — must be punycode
        "https://xn--/a.png",  # malformed punycode
    ],
)
def test_public_url_rejection_matrix(url):
    with pytest.raises(MarketingPublicUrlValidationError):
        validate_public_url(url)


def test_public_url_accepts_punycode_and_https():
    ok = validate_public_url("https://xn--e1afmkfd.xn--p1ai/media/a.png")
    assert ok.host.startswith("xn--")
    assert ok.host_fingerprint


def test_mode_b_no_network_call_proof(db_session):
    tenant = _create_tenant(db_session, "c2a-mode-b")
    MarketingStorageProfileService(db_session, tenant.id).create_profile(
        mode=MarketingStorageResourceMode.CLIENT_PUBLIC_URL,
        display_name="Public URL",
        status=MarketingStorageProfileStatus.ACTIVE,
    )
    db_session.commit()
    with (
        patch("socket.getaddrinfo") as dns,
        patch("urllib.request.urlopen") as urlopen,
    ):
        view = PublicUrlMediaRegistrationService(db_session, tenant.id).register_public_url(
            pack_id=None,
            file_name="remote.png",
            mime_type="image/png",
            public_url="https://cdn.example.com/img/remote.png",
        )
        db_session.commit()
        assert view.validation_status == MarketingMediaValidationStatus.REGISTERED_UNVERIFIED
        dns.assert_not_called()
        urlopen.assert_not_called()


def test_legacy_assets_remain_unverified(db_session):
    tenant = _create_tenant(db_session, "c2a-legacy")
    asset = MarketingMediaAsset(
        tenant_id=tenant.id,
        pack_id=None,
        role="instagram_feed",
        file_name="legacy.png",
        mime_type="image/png",
        storage_provider="git_path",
        storage_key="content/packs/legacy/feed.png",
        public_url="https://example.com/legacy.png",
        status=MarketingMediaAssetStatus.STORED,
        metadata_json={},
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    assert asset.validation_status == MarketingMediaValidationStatus.LEGACY_UNVERIFIED
    assert asset.verified_size_bytes is None
    assert asset.declared_size_bytes is None


def test_audit_has_no_url_path_or_credentials(db_session):
    tenant = _create_tenant(db_session, "c2a-audit")
    MarketingStorageProfileService(db_session, tenant.id).create_profile(
        mode=MarketingStorageResourceMode.CLIENT_PUBLIC_URL,
        display_name="Public URL",
        status=MarketingStorageProfileStatus.ACTIVE,
    )
    db_session.commit()
    view = PublicUrlMediaRegistrationService(db_session, tenant.id).register_public_url(
        pack_id=None,
        file_name="aud.png",
        mime_type="image/png",
        public_url="https://cdn.example.com/secret-path/aud.png",
    )
    db_session.commit()
    logs = list(db_session.scalars(select(AuditLog).where(AuditLog.entity_id == view.id)).all())
    assert logs
    for log in logs:
        blob = json.dumps(log.changes_json or {}) + (log.summary or "")
        assert "cdn.example.com" not in blob
        assert "secret-path" not in blob
        assert "https://" not in blob
        assert "marketing/tenants" not in blob


def test_profile_tenant_isolation(db_session):
    t1 = _create_tenant(db_session, "c2a-t1")
    t2 = _create_tenant(db_session, "c2a-t2")
    view = MarketingStorageProfileService(db_session, t1.id).create_profile(
        mode=MarketingStorageResourceMode.FLEXITY_MANAGED,
        display_name="Managed A",
        status=MarketingStorageProfileStatus.ACTIVE,
    )
    db_session.commit()
    with pytest.raises(MarketingStorageProfileNotFoundError):
        MarketingStorageProfileService(db_session, t2.id).get_profile(view.id)
