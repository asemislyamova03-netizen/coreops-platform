"""Declared MIME vs content magic-byte boundary (not malware scanning).

Honest M8-C2a semantics:
- header magic validation only (png/jpeg/webp);
- does NOT set verified_mime_type;
- does NOT imply decoded/safe/malware-free/publish-ready;
- decompression-bomb / dimensions / polyglot → production upload gate (deferred).
"""

from __future__ import annotations

from typing import Protocol


class ContentValidationPort(Protocol):
    def validate_magic_bytes(self, data: bytes, declared_mime: str) -> bool:
        """Return True when bytes are consistent with declared image MIME header.

        Does NOT imply malware-safe, decoded-safe, or publish-ready.
        """


class DeclaredMimeMagicByteValidator:
    """Minimal image magic-byte checks for Mode A boundary."""

    def validate_magic_bytes(self, data: bytes, declared_mime: str) -> bool:
        mime = declared_mime.strip().lower()
        if not data:
            return False
        if mime == "image/png":
            return data.startswith(b"\x89PNG\r\n\x1a\n")
        if mime in {"image/jpeg", "image/jpg"}:
            return data.startswith(b"\xff\xd8\xff")
        if mime == "image/webp":
            return (
                len(data) >= 12
                and data.startswith(b"RIFF")
                and data[8:12] == b"WEBP"
            )
        return False


class AcceptDeclaredMimeStub:
    """Test/dev stub — accepts declared MIME without byte inspection."""

    def validate_magic_bytes(self, data: bytes, declared_mime: str) -> bool:
        return bool(data) and bool(declared_mime.strip())
