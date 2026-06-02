import uuid
from pathlib import Path

from app.core.config import get_settings


def tenant_documents_dir(tenant_id: uuid.UUID) -> Path:
    settings = get_settings()
    path = Path(settings.storage_path) / "tenants" / str(tenant_id) / "documents"
    path.mkdir(parents=True, exist_ok=True)
    return path


def document_dir(tenant_id: uuid.UUID, document_id: uuid.UUID) -> Path:
    path = tenant_documents_dir(tenant_id) / str(document_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_text_file(
    tenant_id: uuid.UUID,
    document_id: uuid.UUID,
    filename: str,
    content: str,
) -> tuple[str, int]:
    target = document_dir(tenant_id, document_id) / filename
    target.write_text(content, encoding="utf-8")
    relative = str(target.relative_to(Path(get_settings().storage_path)))
    return relative.replace("\\", "/"), len(content.encode("utf-8"))


def save_binary_file(
    tenant_id: uuid.UUID,
    document_id: uuid.UUID,
    filename: str,
    data: bytes,
) -> tuple[str, int]:
    target = document_dir(tenant_id, document_id) / filename
    target.write_bytes(data)
    relative = str(target.relative_to(Path(get_settings().storage_path)))
    return relative.replace("\\", "/"), len(data)
