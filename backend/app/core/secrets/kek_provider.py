"""KEK ring loader for envelope-encrypted SecretVaultPort.

Ring JSON schema (strict):
  {
    "schema_version": <int >= 1>,
    "active_kek_version": <int >= 1>,
    "keys": {
      "<version>": "<base64 of exactly 32 raw bytes>",
      ...
    }
  }

Rules:
- Never log, print, or include ring/key material in exception messages.
- Unknown / missing kek_version → fail-closed SecretVaultError.
- Paths come from Settings (credential file or systemd credentials dir+name).
- No hard-coded Hoster paths in this module.
"""

from __future__ import annotations

import base64
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from app.core.secrets.port import SecretVaultError

_KEK_SIZE = 32
_RING_SCHEMA_VERSION = 1


class KekProviderError(SecretVaultError):
    """Fail-closed KEK load/lookup error (safe code only)."""


@dataclass(frozen=True, slots=True)
class KekRing:
    schema_version: int
    active_kek_version: int
    _keys: Mapping[int, bytes]

    def get(self, version: int) -> bytes:
        if version < 1:
            raise KekProviderError("kek_version_invalid")
        key = self._keys.get(version)
        if key is None:
            raise KekProviderError("kek_version_unknown")
        return key

    @property
    def versions(self) -> frozenset[int]:
        return frozenset(self._keys.keys())

    def __repr__(self) -> str:
        return (
            f"KekRing(schema_version={self.schema_version}, "
            f"active_kek_version={self.active_kek_version}, "
            f"versions={sorted(self._keys.keys())})"
        )


def parse_kek_ring(raw: bytes | str | Mapping[str, object]) -> KekRing:
    """Parse and validate a KEK ring. Never echo key material on failure."""
    try:
        if isinstance(raw, Mapping):
            data = dict(raw)
        else:
            if isinstance(raw, bytes):
                text = raw.decode("utf-8")
            else:
                text = raw
            data = json.loads(text)
        if not isinstance(data, dict):
            raise KekProviderError("kek_ring_invalid")
        schema_version = data.get("schema_version")
        active = data.get("active_kek_version")
        keys_obj = data.get("keys")
        if schema_version != _RING_SCHEMA_VERSION:
            raise KekProviderError("kek_ring_schema_unsupported")
        if not isinstance(active, int) or isinstance(active, bool) or active < 1:
            raise KekProviderError("kek_ring_invalid")
        if not isinstance(keys_obj, dict) or not keys_obj:
            raise KekProviderError("kek_ring_invalid")

        keys: dict[int, bytes] = {}
        for ver_raw, b64 in keys_obj.items():
            try:
                ver = int(ver_raw)
            except (TypeError, ValueError) as exc:
                raise KekProviderError("kek_ring_invalid") from exc
            if ver < 1:
                raise KekProviderError("kek_ring_invalid")
            if not isinstance(b64, str):
                raise KekProviderError("kek_ring_invalid")
            try:
                material = base64.b64decode(b64, validate=True)
            except Exception as exc:
                raise KekProviderError("kek_ring_invalid") from exc
            if len(material) != _KEK_SIZE:
                raise KekProviderError("kek_ring_invalid")
            if ver in keys:
                raise KekProviderError("kek_ring_invalid")
            keys[ver] = material

        if active not in keys:
            raise KekProviderError("kek_ring_invalid")
        return KekRing(schema_version=schema_version, active_kek_version=active, _keys=keys)
    except KekProviderError:
        raise
    except SecretVaultError:
        raise
    except Exception as exc:
        raise KekProviderError("kek_ring_invalid") from exc


def resolve_kek_credential_path(
    *,
    credential_path: str | None = None,
    credentials_dir: str | None = None,
    credential_name: str | None = None,
) -> Path:
    """Resolve KEK file path from config. No hard-coded host paths."""
    direct = (credential_path or "").strip()
    if direct:
        return Path(direct)

    directory = (credentials_dir or "").strip() or (os.environ.get("CREDENTIALS_DIRECTORY") or "").strip()
    name = (credential_name or "").strip()
    if directory and name:
        # Reject path separators in name (credential basename only).
        if Path(name).name != name or "/" in name or "\\" in name:
            raise KekProviderError("kek_credential_name_invalid")
        return Path(directory) / name

    raise KekProviderError("kek_credential_path_unconfigured")


class KekProvider:
    """In-process KEK map keyed by kek_version."""

    def __init__(self, ring: KekRing) -> None:
        self._ring = ring

    @property
    def active_kek_version(self) -> int:
        return self._ring.active_kek_version

    def get_kek(self, version: int) -> bytes:
        return self._ring.get(version)

    def get_active_kek(self) -> tuple[int, bytes]:
        version = self._ring.active_kek_version
        return version, self._ring.get(version)

    @classmethod
    def from_ring(cls, ring: KekRing) -> KekProvider:
        return cls(ring)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> KekProvider:
        return cls(parse_kek_ring(raw))

    @classmethod
    def from_file(cls, path: Path | str) -> KekProvider:
        file_path = Path(path)
        try:
            raw = file_path.read_bytes()
        except OSError as exc:
            raise KekProviderError("kek_credential_unreadable") from exc
        return cls(parse_kek_ring(raw))

    @classmethod
    def load_from_config(
        cls,
        *,
        credential_path: str | None = None,
        credentials_dir: str | None = None,
        credential_name: str | None = None,
    ) -> KekProvider:
        path = resolve_kek_credential_path(
            credential_path=credential_path,
            credentials_dir=credentials_dir,
            credential_name=credential_name,
        )
        return cls.from_file(path)

    def __repr__(self) -> str:
        return f"KekProvider(active={self._ring.active_kek_version}, versions={sorted(self._ring.versions)})"


def build_ephemeral_kek_ring(
    *,
    active_kek_version: int = 1,
    extra_versions: Mapping[int, bytes] | None = None,
) -> dict[str, object]:
    """Test helper: build a valid ring dict with random KEKs (never for production)."""
    keys: dict[str, str] = {}
    material = {active_kek_version: os.urandom(_KEK_SIZE)}
    if extra_versions:
        for ver, key in extra_versions.items():
            if ver < 1 or len(key) != _KEK_SIZE:
                raise KekProviderError("kek_ring_invalid")
            material[ver] = key
    for ver, key in material.items():
        keys[str(ver)] = base64.b64encode(key).decode("ascii")
    return {
        "schema_version": _RING_SCHEMA_VERSION,
        "active_kek_version": active_kek_version,
        "keys": keys,
    }


def write_ephemeral_kek_ring_file(
    *,
    active_kek_version: int = 1,
    extra_versions: Mapping[int, bytes] | None = None,
    directory: str | Path | None = None,
) -> tuple[Path, KekProvider]:
    """Test helper: write a temp KEK ring file and return (path, provider)."""
    ring = build_ephemeral_kek_ring(
        active_kek_version=active_kek_version,
        extra_versions=extra_versions,
    )
    if directory is None:
        fd, name = tempfile.mkstemp(prefix="flexity-kek-", suffix=".json")
        path = Path(name)
        with os.fdopen(fd, "wb") as handle:
            handle.write(json.dumps(ring).encode("utf-8"))
    else:
        path = Path(directory) / "flexity-kek-ring.json"
        path.write_bytes(json.dumps(ring).encode("utf-8"))
    return path, KekProvider.from_file(path)
