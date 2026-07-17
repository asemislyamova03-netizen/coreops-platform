"""Marketing module model registration smoke tests."""

from sqlalchemy import inspect

from app.modules.marketing.models import (
    MarketingContentTopic,
    MarketingLeadAttribution,
    MarketingMediaAsset,
    MarketingPublicationPack,
    MarketingPublicationText,
    MarketingPublishingConnection,
    MarketingPublishLog,
    MarketingStorageResourceProfile,
)


def test_marketing_models_registered_in_metadata(db_engine):
    tables = {
        MarketingContentTopic.__tablename__,
        MarketingPublicationPack.__tablename__,
        MarketingPublicationText.__tablename__,
        MarketingMediaAsset.__tablename__,
        MarketingPublishLog.__tablename__,
        MarketingLeadAttribution.__tablename__,
        MarketingPublishingConnection.__tablename__,
        MarketingStorageResourceProfile.__tablename__,
    }
    inspector = inspect(db_engine)
    existing = set(inspector.get_table_names())
    assert tables.issubset(existing)


def test_marketing_topic_table_columns(db_engine):
    inspector = inspect(db_engine)
    columns = {col["name"] for col in inspector.get_columns("marketing_content_topics")}
    expected = {
        "id",
        "tenant_id",
        "title",
        "rubric",
        "status",
        "priority",
        "reusable",
        "used_count",
        "last_used_at",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(columns)
