"""Secret plaintext wrapper — never log, repr, or serialize as raw value."""

from __future__ import annotations


class SecretPlaintext:
    """Ephemeral plaintext holder for vault/adapter boundaries only."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("secret_plaintext_must_be_str")
        if not value:
            raise ValueError("secret_plaintext_empty")
        object.__setattr__(self, "_value", value)

    def reveal(self) -> str:
        """Return plaintext. Caller must not log, cache, or serialize."""
        return object.__getattribute__(self, "_value")

    def __repr__(self) -> str:
        return "SecretPlaintext(<redacted>)"

    def __str__(self) -> str:
        return "SecretPlaintext(<redacted>)"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SecretPlaintext):
            return NotImplemented
        return self.reveal() == other.reveal()

    def __hash__(self) -> int:
        raise TypeError("unhashable_type_SecretPlaintext")
