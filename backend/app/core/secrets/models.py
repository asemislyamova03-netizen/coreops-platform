"""ORM model for envelope-encrypted secret versions (platform secrets core)."""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, Index, Integer, LargeBinary, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin


class SecretEnvelopeVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Ciphertext row for SecretVaultPort envelope adapter. No FK to marketing tables."""

    __tablename__ = "secret_envelope_versions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "connection_id",
            "purpose",
            "version",
            name="uq_secret_envelope_versions_owner_version",
        ),
        CheckConstraint("version >= 1", name="ck_secret_envelope_versions_version_positive"),
        CheckConstraint(
            "state IN ('pending', 'active', 'deactivated')",
            name="ck_secret_envelope_versions_state",
        ),
        CheckConstraint(
            "algorithm = 'aes-256-gcm'",
            name="ck_secret_envelope_versions_algorithm",
        ),
        CheckConstraint(
            "crypto_schema_version >= 1",
            name="ck_secret_envelope_versions_schema",
        ),
        CheckConstraint(
            "kek_version >= 1",
            name="ck_secret_envelope_versions_kek_version",
        ),
        Index(
            "ix_secret_envelope_versions_owner_state",
            "tenant_id",
            "connection_id",
            "purpose",
            "state",
        ),
        Index(
            "ix_secret_envelope_versions_owner_version",
            "tenant_id",
            "connection_id",
            "purpose",
            "version",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    connection_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False)
    crypto_schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    kek_version: Mapped[int] = mapped_column(Integer, nullable=False)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    ciphertext_nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    wrapped_dek: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    wrapped_dek_nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
