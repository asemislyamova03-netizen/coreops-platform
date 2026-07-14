import re
import unicodedata


def slugify(value: str, *, max_length: int = 128) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text.lower()).strip("-")
    if not slug:
        slug = "pack"
    return slug[:max_length].strip("-")
