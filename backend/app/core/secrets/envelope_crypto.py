"""AES-256-GCM envelope helpers for SecretVaultPort (PyCA cryptography only).

Canonical AAD encoding (crypto_schema_version = 1)
==================================================

Authenticated Associated Data binds ciphertext (and wrapped DEK) to ownership
and format metadata. The same AAD bytes are used for both:

  plaintext  --AES-256-GCM(DEK, nonce_c, AAD)--> ciphertext||tag
  DEK        --AES-256-GCM(KEK, nonce_w, AAD)--> wrapped_dek||tag

Byte layout (big-endian integers, fixed UUID bytes):

  offset  size  field
  ------  ----  -----
  0       5     magic = b\"fxse1\"
  5       16    tenant_id       (UUID RFC 4122 bytes)
  21      16    connection_id   (UUID RFC 4122 bytes)
  37      4     version         (uint32, must be >= 1)
  41      2     purpose_len     (uint16)
  43      N     purpose         (UTF-8, N == purpose_len)
  43+N    4     crypto_schema_version (uint32, must be >= 1)

Total length = 47 + len(purpose_utf8).

Mismatch or GCM tag failure → SecretVaultError with a generic safe code.
Never include key material, plaintext, or raw AAD dumps in exception messages.
"""

from __future__ import annotations

import os
import struct
import uuid
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.secrets.port import SecretVaultError

ALGORITHM_AES_256_GCM = "aes-256-gcm"
CRYPTO_SCHEMA_VERSION = 1
NONCE_SIZE = 12  # 96-bit GCM nonce
DEK_SIZE = 32  # 256-bit
_AAD_MAGIC = b"fxse1"
_AAD_HEADER_FIXED = 5 + 16 + 16 + 4 + 2  # magic + uuids + version + purpose_len
_AAD_TRAILER = 4  # crypto_schema_version


@dataclass(frozen=True, slots=True)
class EnvelopeEncryptResult:
    ciphertext: bytes
    ciphertext_nonce: bytes
    wrapped_dek: bytes
    wrapped_dek_nonce: bytes
    kek_version: int
    algorithm: str
    crypto_schema_version: int


def encode_aad(
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    version: int,
    purpose: str,
    crypto_schema_version: int = CRYPTO_SCHEMA_VERSION,
) -> bytes:
    """Encode canonical AAD bytes for schema v1. Fail-closed on bad inputs."""
    if version < 1:
        raise SecretVaultError("aad_invalid_version")
    if crypto_schema_version < 1:
        raise SecretVaultError("aad_invalid_crypto_schema_version")
    if not isinstance(purpose, str) or not purpose:
        raise SecretVaultError("aad_invalid_purpose")
    purpose_bytes = purpose.encode("utf-8")
    if len(purpose_bytes) > 0xFFFF:
        raise SecretVaultError("aad_purpose_too_long")
    return (
        _AAD_MAGIC
        + tenant_id.bytes
        + connection_id.bytes
        + struct.pack(">I", version)
        + struct.pack(">H", len(purpose_bytes))
        + purpose_bytes
        + struct.pack(">I", crypto_schema_version)
    )


def decode_aad(aad: bytes) -> dict[str, object]:
    """Parse canonical AAD for tests/diagnostics. Never log returned purpose in prod logs."""
    if not isinstance(aad, (bytes, bytearray)):
        raise SecretVaultError("aad_invalid")
    min_len = _AAD_HEADER_FIXED + _AAD_TRAILER
    if len(aad) < min_len:
        raise SecretVaultError("aad_invalid")
    if bytes(aad[0:5]) != _AAD_MAGIC:
        raise SecretVaultError("aad_invalid")
    tenant_id = uuid.UUID(bytes=bytes(aad[5:21]))
    connection_id = uuid.UUID(bytes=bytes(aad[21:37]))
    (version,) = struct.unpack(">I", aad[37:41])
    (purpose_len,) = struct.unpack(">H", aad[41:43])
    purpose_end = 43 + purpose_len
    if len(aad) != purpose_end + _AAD_TRAILER:
        raise SecretVaultError("aad_invalid")
    try:
        purpose = bytes(aad[43:purpose_end]).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SecretVaultError("aad_invalid") from exc
    (crypto_schema_version,) = struct.unpack(">I", aad[purpose_end : purpose_end + 4])
    return {
        "tenant_id": tenant_id,
        "connection_id": connection_id,
        "version": version,
        "purpose": purpose,
        "crypto_schema_version": crypto_schema_version,
    }


def generate_dek() -> bytes:
    return os.urandom(DEK_SIZE)


def generate_nonce() -> bytes:
    return os.urandom(NONCE_SIZE)


def encrypt_envelope(
    *,
    plaintext: bytes,
    kek: bytes,
    kek_version: int,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    version: int,
    purpose: str,
    crypto_schema_version: int = CRYPTO_SCHEMA_VERSION,
) -> EnvelopeEncryptResult:
    """Encrypt plaintext under a fresh DEK; wrap DEK under KEK. Both use AES-256-GCM."""
    if kek_version < 1:
        raise SecretVaultError("kek_version_invalid")
    if len(kek) != DEK_SIZE:
        raise SecretVaultError("kek_invalid")
    if not isinstance(plaintext, (bytes, bytearray)) or not plaintext:
        raise SecretVaultError("plaintext_invalid")

    aad = encode_aad(
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=version,
        purpose=purpose,
        crypto_schema_version=crypto_schema_version,
    )
    dek = generate_dek()
    ciphertext_nonce = generate_nonce()
    wrapped_dek_nonce = generate_nonce()
    try:
        ciphertext = AESGCM(dek).encrypt(ciphertext_nonce, bytes(plaintext), aad)
        wrapped_dek = AESGCM(kek).encrypt(wrapped_dek_nonce, dek, aad)
    except Exception as exc:  # pragma: no cover - defensive
        raise SecretVaultError("envelope_encrypt_failed") from exc
    finally:
        # Best-effort: avoid lingering DEK in locals beyond return path.
        del dek

    return EnvelopeEncryptResult(
        ciphertext=ciphertext,
        ciphertext_nonce=ciphertext_nonce,
        wrapped_dek=wrapped_dek,
        wrapped_dek_nonce=wrapped_dek_nonce,
        kek_version=kek_version,
        algorithm=ALGORITHM_AES_256_GCM,
        crypto_schema_version=crypto_schema_version,
    )


def decrypt_envelope(
    *,
    ciphertext: bytes,
    ciphertext_nonce: bytes,
    wrapped_dek: bytes,
    wrapped_dek_nonce: bytes,
    kek: bytes,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    version: int,
    purpose: str,
    crypto_schema_version: int = CRYPTO_SCHEMA_VERSION,
    algorithm: str = ALGORITHM_AES_256_GCM,
) -> bytes:
    """Unwrap DEK then decrypt payload. AAD/tag/algorithm mismatch → generic error."""
    if algorithm != ALGORITHM_AES_256_GCM:
        raise SecretVaultError("unsupported_algorithm")
    if crypto_schema_version != CRYPTO_SCHEMA_VERSION:
        raise SecretVaultError("unsupported_crypto_schema_version")
    if len(kek) != DEK_SIZE:
        raise SecretVaultError("kek_invalid")
    if len(ciphertext_nonce) != NONCE_SIZE or len(wrapped_dek_nonce) != NONCE_SIZE:
        raise SecretVaultError("nonce_invalid")

    aad = encode_aad(
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=version,
        purpose=purpose,
        crypto_schema_version=crypto_schema_version,
    )
    try:
        dek = AESGCM(kek).decrypt(wrapped_dek_nonce, wrapped_dek, aad)
        plaintext = AESGCM(dek).decrypt(ciphertext_nonce, ciphertext, aad)
    except InvalidTag as exc:
        raise SecretVaultError("envelope_auth_failed") from exc
    except SecretVaultError:
        raise
    except Exception as exc:
        raise SecretVaultError("envelope_decrypt_failed") from exc
    finally:
        try:
            del dek  # type: ignore[name-defined]
        except NameError:
            pass

    return plaintext
