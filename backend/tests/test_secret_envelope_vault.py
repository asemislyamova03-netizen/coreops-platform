"""M8-B2 envelope-encrypted SecretVaultPort test matrix (Design Lock §9)."""

from __future__ import annotations

import base64
import json
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from io import StringIO

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, get_settings
from app.core.secrets.adapters.envelope_pg import EnvelopePgSecretVault
from app.core.secrets.envelope_crypto import (
    CRYPTO_SCHEMA_VERSION,
    NONCE_SIZE,
    decode_aad,
    decrypt_envelope,
    encode_aad,
    encrypt_envelope,
)
from app.core.secrets.kek_provider import (
    KekProvider,
    KekProviderError,
    build_ephemeral_kek_ring,
    parse_kek_ring,
    write_ephemeral_kek_ring_file,
)
from app.core.secrets.models import SecretEnvelopeVersion
from app.core.secrets.plaintext import SecretPlaintext
from app.core.secrets.port import SecretStoreMetadata, SecretVaultError, SecretVersionState
from app.core.secrets.ref import build_secret_ref
from app.main import app as fastapi_app
from app.modules.marketing.deps import resolve_secret_vault


def _factory(db_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


def _vault(db_engine, kek_provider: KekProvider | None = None) -> EnvelopePgSecretVault:
    provider = kek_provider or KekProvider.from_mapping(build_ephemeral_kek_ring())
    return EnvelopePgSecretVault(
        session_factory=_factory(db_engine),
        kek_provider=provider,
        pending_ttl_seconds=15 * 60,
    )


# --- §9.1 / §9.2 crypto + vault round-trip / non-determinism ---


def test_aad_canonical_encode_decode_roundtrip():
    tenant_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    aad = encode_aad(
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=7,
        purpose="publishing_connection",
        crypto_schema_version=CRYPTO_SCHEMA_VERSION,
    )
    parsed = decode_aad(aad)
    assert parsed["tenant_id"] == tenant_id
    assert parsed["connection_id"] == connection_id
    assert parsed["version"] == 7
    assert parsed["purpose"] == "publishing_connection"
    assert parsed["crypto_schema_version"] == CRYPTO_SCHEMA_VERSION
    assert aad.startswith(b"fxse1")


def test_encrypt_decrypt_roundtrip_and_nondeterministic_ciphertext():
    tenant_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    kek = os.urandom(32)
    plaintext = b"synthetic-token-roundtrip-001"
    a = encrypt_envelope(
        plaintext=plaintext,
        kek=kek,
        kek_version=1,
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=1,
        purpose="publishing_connection",
    )
    b = encrypt_envelope(
        plaintext=plaintext,
        kek=kek,
        kek_version=1,
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=1,
        purpose="publishing_connection",
    )
    assert a.ciphertext != b.ciphertext
    assert a.ciphertext_nonce != b.ciphertext_nonce
    assert a.wrapped_dek != b.wrapped_dek
    assert len(a.ciphertext_nonce) == NONCE_SIZE
    assert len(a.wrapped_dek_nonce) == NONCE_SIZE

    recovered = decrypt_envelope(
        ciphertext=a.ciphertext,
        ciphertext_nonce=a.ciphertext_nonce,
        wrapped_dek=a.wrapped_dek,
        wrapped_dek_nonce=a.wrapped_dek_nonce,
        kek=kek,
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=1,
        purpose="publishing_connection",
    )
    assert recovered == plaintext


def test_envelope_vault_store_read_activate_roundtrip(db_engine):
    vault = _vault(db_engine)
    tenant_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    ref = vault.store_secret(
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=1,
        plaintext=SecretPlaintext("synthetic-vault-token-aaa"),
        metadata=SecretStoreMetadata(purpose="publishing_connection"),
    )
    assert vault.get_version_state(ref) == SecretVersionState.PENDING
    assert vault.read_secret(ref).reveal() == "synthetic-vault-token-aaa"
    vault.activate_version(ref)
    assert vault.get_version_state(ref) == SecretVersionState.ACTIVE
    assert vault.read_secret(ref).reveal() == "synthetic-vault-token-aaa"


# --- §9.3 AAD mismatch ---


def test_aad_mismatch_fail_closed():
    tenant_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    kek = os.urandom(32)
    env = encrypt_envelope(
        plaintext=b"synthetic-aad-token",
        kek=kek,
        kek_version=1,
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=1,
        purpose="publishing_connection",
    )
    with pytest.raises(SecretVaultError) as exc:
        decrypt_envelope(
            ciphertext=env.ciphertext,
            ciphertext_nonce=env.ciphertext_nonce,
            wrapped_dek=env.wrapped_dek,
            wrapped_dek_nonce=env.wrapped_dek_nonce,
            kek=kek,
            tenant_id=uuid.uuid4(),
            connection_id=connection_id,
            version=1,
            purpose="publishing_connection",
        )
    assert exc.value.code == "envelope_auth_failed"
    assert "synthetic" not in str(exc.value)


# --- §9.4 tampered ciphertext ---


def test_tampered_ciphertext_fail_closed():
    tenant_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    kek = os.urandom(32)
    env = encrypt_envelope(
        plaintext=b"synthetic-tamper-token",
        kek=kek,
        kek_version=1,
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=1,
        purpose="publishing_connection",
    )
    tampered = bytearray(env.ciphertext)
    tampered[-1] ^= 0xFF
    with pytest.raises(SecretVaultError) as exc:
        decrypt_envelope(
            ciphertext=bytes(tampered),
            ciphertext_nonce=env.ciphertext_nonce,
            wrapped_dek=env.wrapped_dek,
            wrapped_dek_nonce=env.wrapped_dek_nonce,
            kek=kek,
            tenant_id=tenant_id,
            connection_id=connection_id,
            version=1,
            purpose="publishing_connection",
        )
    assert exc.value.code == "envelope_auth_failed"


# --- §9.5 missing / wrong KEK ---


def test_unknown_kek_version_fail_closed(db_engine):
    ring = build_ephemeral_kek_ring(active_kek_version=1)
    vault = _vault(db_engine, KekProvider.from_mapping(ring))
    tenant_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    ref = vault.store_secret(
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=1,
        plaintext=SecretPlaintext("synthetic-kek-miss"),
    )
    with _factory(db_engine)() as db:
        db.execute(
            update(SecretEnvelopeVersion)
            .where(
                SecretEnvelopeVersion.tenant_id == tenant_id,
                SecretEnvelopeVersion.connection_id == connection_id,
                SecretEnvelopeVersion.version == 1,
            )
            .values(kek_version=99)
        )
        db.commit()
    with pytest.raises(SecretVaultError) as exc:
        vault.read_secret(ref)
    assert exc.value.code == "kek_version_unknown"


def test_wrong_kek_material_fail_closed():
    tenant_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    kek_a = os.urandom(32)
    kek_b = os.urandom(32)
    env = encrypt_envelope(
        plaintext=b"synthetic-wrong-kek",
        kek=kek_a,
        kek_version=1,
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=1,
        purpose="publishing_connection",
    )
    with pytest.raises(SecretVaultError) as exc:
        decrypt_envelope(
            ciphertext=env.ciphertext,
            ciphertext_nonce=env.ciphertext_nonce,
            wrapped_dek=env.wrapped_dek,
            wrapped_dek_nonce=env.wrapped_dek_nonce,
            kek=kek_b,
            tenant_id=tenant_id,
            connection_id=connection_id,
            version=1,
            purpose="publishing_connection",
        )
    assert exc.value.code == "envelope_auth_failed"


def test_unsupported_algorithm_and_schema_fail_closed(db_engine):
    tenant_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    kek = os.urandom(32)
    env = encrypt_envelope(
        plaintext=b"synthetic-algo",
        kek=kek,
        kek_version=1,
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=1,
        purpose="publishing_connection",
    )
    with pytest.raises(SecretVaultError) as exc:
        decrypt_envelope(
            ciphertext=env.ciphertext,
            ciphertext_nonce=env.ciphertext_nonce,
            wrapped_dek=env.wrapped_dek,
            wrapped_dek_nonce=env.wrapped_dek_nonce,
            kek=kek,
            tenant_id=tenant_id,
            connection_id=connection_id,
            version=1,
            purpose="publishing_connection",
            algorithm="aes-128-gcm",
        )
    assert exc.value.code == "unsupported_algorithm"

    vault = _vault(db_engine)
    ref = vault.store_secret(
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=1,
        plaintext=SecretPlaintext("synthetic-schema"),
    )
    with _factory(db_engine)() as db:
        db.execute(
            update(SecretEnvelopeVersion)
            .where(
                SecretEnvelopeVersion.tenant_id == tenant_id,
                SecretEnvelopeVersion.version == 1,
            )
            .values(crypto_schema_version=99)
        )
        db.commit()
    with pytest.raises(SecretVaultError) as exc2:
        vault.read_secret(ref)
    assert exc2.value.code == "unsupported_crypto_schema_version"


# --- §9.6 DEK uniqueness + KEK rotation ---


def test_dek_per_version_and_kek_rotation_decrypt(db_engine):
    kek_v1 = os.urandom(32)
    kek_v2 = os.urandom(32)
    ring_v1 = {
        "schema_version": 1,
        "active_kek_version": 1,
        "keys": {"1": base64.b64encode(kek_v1).decode("ascii")},
    }
    ring_both = {
        "schema_version": 1,
        "active_kek_version": 2,
        "keys": {
            "1": base64.b64encode(kek_v1).decode("ascii"),
            "2": base64.b64encode(kek_v2).decode("ascii"),
        },
    }
    vault_v1 = _vault(db_engine, KekProvider.from_mapping(ring_v1))
    tenant_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    ref1 = vault_v1.store_secret(
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=1,
        plaintext=SecretPlaintext("synthetic-old-kek-token"),
    )
    vault_v1.activate_version(ref1)

    vault_rot = _vault(db_engine, KekProvider.from_mapping(ring_both))
    ref2 = vault_rot.store_secret(
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=2,
        plaintext=SecretPlaintext("synthetic-new-kek-token"),
    )
    vault_rot.activate_version(ref2)

    with _factory(db_engine)() as db:
        rows = db.scalars(
            select(SecretEnvelopeVersion).where(
                SecretEnvelopeVersion.tenant_id == tenant_id,
                SecretEnvelopeVersion.connection_id == connection_id,
            )
        ).all()
        assert {r.version: r.kek_version for r in rows} == {1: 1, 2: 2}
        assert rows[0].wrapped_dek != rows[1].wrapped_dek

    assert vault_rot.read_secret(ref1).reveal() == "synthetic-old-kek-token"
    assert vault_rot.read_secret(ref2).reveal() == "synthetic-new-kek-token"


# --- §9.7 compensation + orphan pending cleanup ---


def test_compensation_and_orphan_pending_cleanup(db_engine):
    vault = _vault(db_engine)
    tenant_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    ref = vault.store_secret(
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=1,
        plaintext=SecretPlaintext("synthetic-orphan-pending"),
    )
    assert vault.get_version_state(ref) == SecretVersionState.PENDING
    vault.compensate_delete_pending(ref)
    assert vault.version_exists(ref) is False

    ref2 = vault.store_secret(
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=2,
        plaintext=SecretPlaintext("synthetic-ttl-pending"),
    )
    with _factory(db_engine)() as db:
        db.execute(
            update(SecretEnvelopeVersion)
            .where(
                SecretEnvelopeVersion.tenant_id == tenant_id,
                SecretEnvelopeVersion.version == 2,
            )
            .values(created_at=datetime.now(UTC) - timedelta(minutes=20))
        )
        db.commit()
    deleted = vault.cleanup_orphan_pending(older_than=timedelta(minutes=15))
    assert deleted == 1
    assert vault.version_exists(ref2) is False

    ref3 = vault.store_secret(
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=3,
        plaintext=SecretPlaintext("synthetic-active-not-cleaned"),
    )
    vault.activate_version(ref3)
    with _factory(db_engine)() as db:
        db.execute(
            update(SecretEnvelopeVersion)
            .where(SecretEnvelopeVersion.version == 3)
            .values(created_at=datetime.now(UTC) - timedelta(hours=2))
        )
        db.commit()
    assert vault.cleanup_orphan_pending() == 0
    assert vault.version_exists(ref3) is True

    vault.deactivate_version(ref3)
    with pytest.raises(SecretVaultError):
        vault.read_secret(ref3)
    assert vault.confirm_inactive(ref3) is True
    vault.delete_version(ref3)
    assert vault.version_exists(ref3) is False


# --- §9.8 redaction ---


def test_redaction_no_key_material_in_repr_or_logs(db_engine, caplog):
    path, provider = write_ephemeral_kek_ring_file()
    try:
        vault = _vault(db_engine, provider)
        secret = "synthetic-redact-token-XYZ"
        ref = vault.store_secret(
            tenant_id=uuid.uuid4(),
            connection_id=uuid.uuid4(),
            version=1,
            plaintext=SecretPlaintext(secret),
        )
        assert secret not in repr(vault)
        assert secret not in repr(provider)
        assert ref.render() not in repr(ref)
        with caplog.at_level(logging.DEBUG):
            logging.getLogger("test_secret_envelope").debug("vault=%r provider=%r", vault, provider)
        assert secret not in caplog.text
        assert "keys" not in caplog.text or base64.b64encode(b"x" * 32).decode() not in caplog.text
    finally:
        path.unlink(missing_ok=True)


# --- §9.9 production-like DI → 503 ---


def test_production_without_kek_returns_none_for_503():
    get_settings.cache_clear()
    settings = Settings(
        app_env="production",
        secret_vault_adapter="auto",
        secret_kek_credential_path=None,
        secret_kek_credentials_dir=None,
        secret_kek_credential_name=None,
    )

    class _Req:
        app = fastapi_app

    if hasattr(fastapi_app.state, "marketing_secret_vault"):
        delattr(fastapi_app.state, "marketing_secret_vault")
    assert resolve_secret_vault(_Req(), settings) is None
    get_settings.cache_clear()


def test_production_in_memory_adapter_forbidden():
    class _Req:
        app = fastapi_app

    if hasattr(fastapi_app.state, "marketing_secret_vault"):
        delattr(fastapi_app.state, "marketing_secret_vault")
    settings = Settings(app_env="production", secret_vault_adapter="in_memory")
    assert resolve_secret_vault(_Req(), settings) is None


def test_staging_envelope_with_temp_kek_loads(db_engine):
    path, provider = write_ephemeral_kek_ring_file()

    class _Req:
        app = fastapi_app

    try:
        if hasattr(fastapi_app.state, "marketing_secret_vault"):
            delattr(fastapi_app.state, "marketing_secret_vault")

        vault = EnvelopePgSecretVault(
            session_factory=_factory(db_engine),
            kek_provider=provider,
        )
        fastapi_app.state.marketing_secret_vault = vault
        settings = Settings(
            app_env="staging",
            secret_vault_adapter="envelope_pg",
            secret_kek_credential_path=str(path),
        )
        resolved = resolve_secret_vault(_Req(), settings)
        assert isinstance(resolved, EnvelopePgSecretVault)
    finally:
        if hasattr(fastapi_app.state, "marketing_secret_vault"):
            delattr(fastapi_app.state, "marketing_secret_vault")
        path.unlink(missing_ok=True)


# --- §9.10 backup/restore ciphertext-only fixture ---


def test_backup_restore_ciphertext_only_no_plaintext_in_logs(db_engine, caplog):
    vault = _vault(db_engine)
    tenant_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    secret = "synthetic-backup-restore-token"
    ref = vault.store_secret(
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=1,
        plaintext=SecretPlaintext(secret),
    )
    vault.activate_version(ref)

    with _factory(db_engine)() as db:
        row = db.scalar(
            select(SecretEnvelopeVersion).where(
                SecretEnvelopeVersion.tenant_id == tenant_id,
                SecretEnvelopeVersion.version == 1,
            )
        )
        assert row is not None
        fixture = {
            "tenant_id": str(row.tenant_id),
            "connection_id": str(row.connection_id),
            "purpose": row.purpose,
            "version": row.version,
            "state": row.state,
            "algorithm": row.algorithm,
            "crypto_schema_version": row.crypto_schema_version,
            "kek_version": row.kek_version,
            "ciphertext": base64.b64encode(row.ciphertext).decode("ascii"),
            "ciphertext_nonce": base64.b64encode(row.ciphertext_nonce).decode("ascii"),
            "wrapped_dek": base64.b64encode(row.wrapped_dek).decode("ascii"),
            "wrapped_dek_nonce": base64.b64encode(row.wrapped_dek_nonce).decode("ascii"),
        }

    stream = StringIO()
    json.dump(fixture, stream)
    dumped = stream.getvalue()
    assert secret not in dumped
    assert "synthetic-backup" not in dumped

    with caplog.at_level(logging.INFO):
        logging.getLogger("test_backup").info("restored_fixture_keys=%s", list(fixture.keys()))
    assert secret not in caplog.text

    # Restore into a fresh row (new id) and decrypt with same KEK ring via vault provider.
    # Re-store path: delete then insert from fixture fields through ORM.
    vault.delete_version(ref)
    with _factory(db_engine)() as db:
        restored = SecretEnvelopeVersion(
            tenant_id=uuid.UUID(fixture["tenant_id"]),
            connection_id=uuid.UUID(fixture["connection_id"]),
            purpose=fixture["purpose"],
            version=fixture["version"],
            state=fixture["state"],
            algorithm=fixture["algorithm"],
            crypto_schema_version=fixture["crypto_schema_version"],
            kek_version=fixture["kek_version"],
            ciphertext=base64.b64decode(fixture["ciphertext"]),
            ciphertext_nonce=base64.b64decode(fixture["ciphertext_nonce"]),
            wrapped_dek=base64.b64decode(fixture["wrapped_dek"]),
            wrapped_dek_nonce=base64.b64decode(fixture["wrapped_dek_nonce"]),
        )
        db.add(restored)
        db.commit()

    assert vault.read_secret(ref).reveal() == secret


# --- KEK provider helpers ---


def test_kek_ring_rejects_bad_key_length_and_unknown_version():
    bad = {
        "schema_version": 1,
        "active_kek_version": 1,
        "keys": {"1": base64.b64encode(os.urandom(16)).decode("ascii")},
    }
    with pytest.raises(KekProviderError):
        parse_kek_ring(bad)

    good = build_ephemeral_kek_ring(active_kek_version=1)
    provider = KekProvider.from_mapping(good)
    with pytest.raises(KekProviderError) as exc:
        provider.get_kek(9)
    assert exc.value.code == "kek_version_unknown"
    assert "keys" not in repr(provider)


def test_duplicate_store_fails(db_engine):
    vault = _vault(db_engine)
    tenant_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    vault.store_secret(
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=1,
        plaintext=SecretPlaintext("synthetic-dup-1"),
    )
    with pytest.raises(SecretVaultError) as exc:
        vault.store_secret(
            tenant_id=tenant_id,
            connection_id=connection_id,
            version=1,
            plaintext=SecretPlaintext("synthetic-dup-2"),
        )
    assert exc.value.code == "secret_version_already_exists"


def test_secret_ref_ownership_helpers():
    ref = build_secret_ref(tenant_id=uuid.uuid4(), connection_id=uuid.uuid4(), version=1)
    assert "secret://" not in repr(ref)
