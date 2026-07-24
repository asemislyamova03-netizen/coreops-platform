"""PostgreSQL envelope-encrypted SecretVaultPort adapter."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.secrets.envelope_crypto import (
    ALGORITHM_AES_256_GCM,
    CRYPTO_SCHEMA_VERSION,
    NONCE_SIZE,
    decrypt_envelope,
    encrypt_envelope,
)
from app.core.secrets.kek_provider import KekProvider
from app.core.secrets.models import SecretEnvelopeVersion
from app.core.secrets.plaintext import SecretPlaintext
from app.core.secrets.port import (
    SecretStoreMetadata,
    SecretVaultError,
    SecretVersionState,
)
from app.core.secrets.ref import SecretRef, build_secret_ref

SessionFactory = Callable[[], Session] | sessionmaker[Session]

DEFAULT_PENDING_TTL_SECONDS = 15 * 60  # Design Lock: 15 minutes
_DEFAULT_PURPOSE = "publishing_connection"


class EnvelopePgSecretVault:
    """AES-256-GCM envelope vault backed by ``secret_envelope_versions``."""

    def __init__(
        self,
        *,
        session_factory: SessionFactory,
        kek_provider: KekProvider,
        pending_ttl_seconds: int = DEFAULT_PENDING_TTL_SECONDS,
    ) -> None:
        if pending_ttl_seconds < 1:
            raise SecretVaultError("pending_ttl_invalid")
        self._session_factory = session_factory
        self._kek_provider = kek_provider
        self._pending_ttl = timedelta(seconds=pending_ttl_seconds)

    def store_secret(
        self,
        *,
        tenant_id: uuid.UUID,
        connection_id: uuid.UUID,
        version: int,
        plaintext: SecretPlaintext,
        metadata: SecretStoreMetadata | None = None,
    ) -> SecretRef:
        if not isinstance(plaintext, SecretPlaintext):
            raise SecretVaultError("plaintext_must_be_SecretPlaintext")
        if version < 1:
            raise SecretVaultError("secret_version_invalid")

        purpose = (metadata.purpose if metadata else None) or _DEFAULT_PURPOSE
        if not isinstance(purpose, str) or not purpose or len(purpose) > 64:
            raise SecretVaultError("purpose_invalid")

        kek_version, kek = self._kek_provider.get_active_kek()
        try:
            envelope = encrypt_envelope(
                plaintext=plaintext.reveal().encode("utf-8"),
                kek=kek,
                kek_version=kek_version,
                tenant_id=tenant_id,
                connection_id=connection_id,
                version=version,
                purpose=purpose,
            )
        finally:
            del kek

        if (
            len(envelope.ciphertext_nonce) != NONCE_SIZE
            or len(envelope.wrapped_dek_nonce) != NONCE_SIZE
        ):
            raise SecretVaultError("nonce_invalid")

        ref = build_secret_ref(
            tenant_id=tenant_id,
            connection_id=connection_id,
            version=version,
        )
        row = SecretEnvelopeVersion(
            tenant_id=tenant_id,
            connection_id=connection_id,
            purpose=purpose,
            version=version,
            state=SecretVersionState.PENDING.value,
            algorithm=envelope.algorithm,
            crypto_schema_version=envelope.crypto_schema_version,
            kek_version=envelope.kek_version,
            ciphertext=envelope.ciphertext,
            ciphertext_nonce=envelope.ciphertext_nonce,
            wrapped_dek=envelope.wrapped_dek,
            wrapped_dek_nonce=envelope.wrapped_dek_nonce,
        )
        with self._session() as db:
            db.add(row)
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise SecretVaultError("secret_version_already_exists") from exc
        return ref

    def read_secret(self, ref: SecretRef) -> SecretPlaintext:
        self._assert_typed_ref(ref)
        with self._session() as db:
            row = self._require_row(db, ref)
            if row.state == SecretVersionState.DEACTIVATED.value:
                raise SecretVaultError("secret_version_inactive")
            plaintext = self._decrypt_row(row, ref)
        return SecretPlaintext(plaintext.decode("utf-8"))

    def activate_version(self, ref: SecretRef) -> None:
        self._assert_typed_ref(ref)
        with self._session() as db:
            row = self._require_row(db, ref)
            if row.state == SecretVersionState.DEACTIVATED.value:
                raise SecretVaultError("secret_version_inactive")
            row.state = SecretVersionState.ACTIVE.value
            db.commit()

    def deactivate_version(self, ref: SecretRef) -> None:
        self._assert_typed_ref(ref)
        with self._session() as db:
            row = self._require_row(db, ref)
            row.state = SecretVersionState.DEACTIVATED.value
            db.commit()

    def delete_version(self, ref: SecretRef) -> None:
        self._assert_typed_ref(ref)
        with self._session() as db:
            db.execute(
                delete(SecretEnvelopeVersion).where(
                    and_(
                        SecretEnvelopeVersion.tenant_id == ref.tenant_id,
                        SecretEnvelopeVersion.connection_id == ref.connection_id,
                        SecretEnvelopeVersion.version == ref.version,
                    )
                )
            )
            db.commit()

    def confirm_inactive(self, ref: SecretRef) -> bool:
        self._assert_typed_ref(ref)
        with self._session() as db:
            row = self._get_row(db, ref)
            if row is None:
                return True
            return row.state == SecretVersionState.DEACTIVATED.value

    def version_exists(self, ref: SecretRef) -> bool:
        self._assert_typed_ref(ref)
        with self._session() as db:
            return self._get_row(db, ref) is not None

    def get_version_state(self, ref: SecretRef) -> SecretVersionState | None:
        self._assert_typed_ref(ref)
        with self._session() as db:
            row = self._get_row(db, ref)
            if row is None:
                return None
            return SecretVersionState(row.state)

    def compensate_delete_pending(self, ref: SecretRef) -> None:
        """Compensation helper for failed bind/rotate: delete orphan pending version."""
        self._assert_typed_ref(ref)
        with self._session() as db:
            row = self._get_row(db, ref)
            if row is None:
                return
            if row.state != SecretVersionState.PENDING.value:
                raise SecretVaultError("compensate_requires_pending")
            db.delete(row)
            db.commit()

    def cleanup_orphan_pending(
        self,
        *,
        older_than: timedelta | None = None,
        now: datetime | None = None,
    ) -> int:
        """Hard-delete pending rows older than TTL. Returns deleted count."""
        ttl = older_than if older_than is not None else self._pending_ttl
        if ttl.total_seconds() < 1:
            raise SecretVaultError("pending_ttl_invalid")
        cutoff = (now or datetime.now(UTC)) - ttl
        with self._session() as db:
            result = db.execute(
                delete(SecretEnvelopeVersion).where(
                    and_(
                        SecretEnvelopeVersion.state == SecretVersionState.PENDING.value,
                        SecretEnvelopeVersion.created_at < cutoff,
                    )
                )
            )
            db.commit()
            return int(result.rowcount or 0)

    def _decrypt_row(self, row: SecretEnvelopeVersion, ref: SecretRef) -> bytes:
        if row.algorithm != ALGORITHM_AES_256_GCM:
            raise SecretVaultError("unsupported_algorithm")
        if row.crypto_schema_version != CRYPTO_SCHEMA_VERSION:
            raise SecretVaultError("unsupported_crypto_schema_version")
        if (
            row.tenant_id != ref.tenant_id
            or row.connection_id != ref.connection_id
            or row.version != ref.version
        ):
            raise SecretVaultError("secret_ref_ownership_mismatch")

        kek = self._kek_provider.get_kek(row.kek_version)
        try:
            return decrypt_envelope(
                ciphertext=bytes(row.ciphertext),
                ciphertext_nonce=bytes(row.ciphertext_nonce),
                wrapped_dek=bytes(row.wrapped_dek),
                wrapped_dek_nonce=bytes(row.wrapped_dek_nonce),
                kek=kek,
                tenant_id=row.tenant_id,
                connection_id=row.connection_id,
                version=row.version,
                purpose=row.purpose,
                crypto_schema_version=row.crypto_schema_version,
                algorithm=row.algorithm,
            )
        finally:
            del kek

    def _assert_typed_ref(self, ref: SecretRef) -> None:
        if not isinstance(ref, SecretRef):
            raise SecretVaultError("secret_ref_must_be_SecretRef")
        expected = build_secret_ref(
            tenant_id=ref.tenant_id,
            connection_id=ref.connection_id,
            version=ref.version,
        )
        if expected.render() != ref.render():
            raise SecretVaultError("secret_ref_ownership_mismatch")

    def _get_row(self, db: Session, ref: SecretRef) -> SecretEnvelopeVersion | None:
        return db.scalar(
            select(SecretEnvelopeVersion).where(
                and_(
                    SecretEnvelopeVersion.tenant_id == ref.tenant_id,
                    SecretEnvelopeVersion.connection_id == ref.connection_id,
                    SecretEnvelopeVersion.version == ref.version,
                )
            )
        )

    def _require_row(self, db: Session, ref: SecretRef) -> SecretEnvelopeVersion:
        row = self._get_row(db, ref)
        if row is None:
            raise SecretVaultError("secret_version_not_found")
        return row

    @contextmanager
    def _session(self) -> Iterator[Session]:
        db = self._session_factory()
        try:
            yield db
        finally:
            db.close()
