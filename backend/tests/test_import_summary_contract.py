import uuid

import pytest

from app.modules.audit.schemas import ImportBatchEntitySummary
from app.modules.audit.service import AuditService


def test_build_import_batch_summary_aggregates(db_session):
    service = AuditService(db_session)
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    entities = [
        ImportBatchEntitySummary(
            entity="parties",
            source_count=10,
            imported_count=8,
            skipped_count=1,
            error_count=1,
            review_count=2,
        ),
        ImportBatchEntitySummary(
            entity="work_items",
            source_count=5,
            imported_count=5,
            skipped_count=0,
            error_count=0,
            review_count=0,
        ),
    ]

    summary = service.build_import_batch_summary(
        tenant_id=tenant_id,
        created_by_user_id=user_id,
        source_system="consult_app",
        entities=entities,
    )
    assert summary.tenant_id == tenant_id
    assert summary.created_by_user_id == user_id
    assert summary.total_source_rows == 15
    assert summary.total_imported_rows == 13
    assert summary.total_skipped_rows == 1
    assert summary.total_error_rows == 1
    assert summary.total_review_rows == 2
    assert summary.status_mapping_warnings == 2


def test_build_import_batch_summary_rejects_invalid_totals(db_session):
    service = AuditService(db_session)
    with pytest.raises(ValueError, match="totals exceed source rows"):
        service.build_import_batch_summary(
            tenant_id=uuid.uuid4(),
            created_by_user_id=None,
            source_system="consult_app",
            entities=[
                ImportBatchEntitySummary(
                    entity="documents",
                    source_count=2,
                    imported_count=2,
                    skipped_count=1,
                    error_count=0,
                    review_count=0,
                )
            ],
        )


def test_record_import_batch_summary_event_writes_audit_log(db_session):
    from sqlalchemy import select

    from app.core.enums import TenantStatus
    from app.modules.audit.models import AuditLog
    from app.modules.provider.models import ProviderCompany
    from app.modules.tenants.models import Tenant

    provider = ProviderCompany(name="Import Summary Co", slug=f"import-sum-{uuid.uuid4().hex[:8]}")
    db_session.add(provider)
    db_session.flush()
    tenant = Tenant(
        provider_company_id=provider.id,
        name="Import Summary Tenant",
        slug=f"import-sum-t-{uuid.uuid4().hex[:8]}",
        status=TenantStatus.TRIAL,
    )
    db_session.add(tenant)
    db_session.flush()

    service = AuditService(db_session)
    summary = service.build_import_batch_summary(
        tenant_id=tenant.id,
        created_by_user_id=None,
        source_system="consult_app",
        entities=[
            ImportBatchEntitySummary(
                entity="payments",
                source_count=3,
                imported_count=3,
                skipped_count=0,
                error_count=0,
                review_count=1,
            )
        ],
    )
    service.record_import_batch_summary_event(summary=summary)
    db_session.flush()

    rows = list(
        db_session.scalars(
            select(AuditLog).where(AuditLog.entity_type == "import_batch_summary")
        ).all()
    )
    assert len(rows) == 1
    assert rows[0].metadata_json["event"] == "import.batch.summary"
    assert rows[0].changes_json["total_source_rows"] == 3
