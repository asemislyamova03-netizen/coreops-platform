from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin


class IndustryTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "industry_templates"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_modules: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    default_roles: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    default_pipelines: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    default_statuses: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    default_custom_fields: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    default_document_templates: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    default_catalog_items: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    default_dashboards: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    default_ai_agents: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    labels_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    settings_schema: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
