import shutil
from pathlib import Path

import pytest

REGISTER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "securepass123",
    "full_name": "Platform Owner",
    "company_name": "CoreOps Provider",
    "company_slug": "coreops-provider",
}


@pytest.fixture
def storage_path(monkeypatch):
    path = Path(__file__).resolve().parent / "_test_storage"
    path.mkdir(exist_ok=True)
    monkeypatch.setenv("STORAGE_PATH", str(path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield path
    get_settings.cache_clear()
    shutil.rmtree(path, ignore_errors=True)


def _documents_tenant(client):
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    token = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    tenant_id = client.post(
        "/api/v1/tenants",
        json={
            "name": "Documents Tenant",
            "slug": "documents-tenant",
            "industry_template_code": "kindergarten_basic",
            "plan_code": "business",
        },
        headers=headers,
    ).json()["id"]

    return {**headers, "X-Tenant-ID": tenant_id}


def test_document_template_generate_and_sign(client, storage_path):
    headers = _documents_tenant(client)

    templates = client.get("/api/v1/document-templates", headers=headers)
    assert templates.status_code == 200
    codes = {t["code"] for t in templates.json()}
    assert "parent_contract" in codes

    contract = next(t for t in templates.json() if t["code"] == "parent_contract")

    generated = client.post(
        "/api/v1/documents/generate",
        headers=headers,
        json={
            "template_id": contract["id"],
            "context": {
                "contract_number": "2025-001",
                "guardian_name": "Иванова Мария",
                "child_name": "Иванов Пётр",
                "contract_date": "2025-09-01",
            },
        },
    )
    assert generated.status_code == 201
    doc = generated.json()
    assert doc["status"] == "generated"
    assert "Иванова Мария" in doc["rendered_content"]
    assert len(doc["files"]) == 1
    assert doc["files"][0]["file_type"] == "generated"
    doc_id = doc["id"]

    sent = client.post(
        f"/api/v1/documents/{doc_id}/send-for-signature",
        headers=headers,
    )
    assert sent.status_code == 200
    assert sent.json()["status"] == "sent_for_signature"
    assert len(sent.json()["signature_requests"]) == 1

    signed = client.post(
        f"/api/v1/documents/{doc_id}/upload-signed-file",
        headers=headers,
        files={"file": ("signed.pdf", b"%PDF-1.4 signed", "application/pdf")},
    )
    assert signed.status_code == 200
    assert signed.json()["status"] == "signed"
    file_types = {f["file_type"] for f in signed.json()["files"]}
    assert file_types == {"generated", "signed"}

    listed = client.get("/api/v1/documents?status=signed", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_custom_template_and_missing_placeholder(client, storage_path):
    headers = _documents_tenant(client)

    created = client.post(
        "/api/v1/document-templates",
        headers=headers,
        json={
            "code": "simple_letter",
            "name": "Письмо",
            "body_template": "Уважаемый {{name}}, текст: {{body}}",
            "fields": [
                {"field_key": "name", "label": "Имя", "is_required": True},
                {"field_key": "body", "label": "Текст", "is_required": True},
            ],
        },
    )
    assert created.status_code == 201
    template_id = created.json()["id"]

    missing = client.post(
        "/api/v1/documents/generate",
        headers=headers,
        json={"template_id": template_id, "context": {"name": "Алексей"}},
    )
    assert missing.status_code == 409

    ok = client.post(
        "/api/v1/documents/generate",
        headers=headers,
        json={
            "template_id": template_id,
            "context": {"name": "Алексей", "body": "Привет"},
        },
    )
    assert ok.status_code == 201
    assert "Алексей" in ok.json()["rendered_content"]


def test_documents_module_guard(client, storage_path):
    headers = _documents_tenant(client)
    tenant_id = headers["X-Tenant-ID"]
    provider_headers = {k: v for k, v in headers.items() if k != "X-Tenant-ID"}

    client.post(
        f"/api/v1/tenants/{tenant_id}/modules/documents/disable",
        headers=provider_headers,
    )

    blocked = client.get("/api/v1/document-templates", headers=headers)
    assert blocked.status_code == 403
