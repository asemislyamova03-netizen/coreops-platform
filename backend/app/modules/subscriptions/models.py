import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import SubscriptionStatus, UsagePeriod
from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin


class Feature(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "features"

    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    module_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class Plan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_modules_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    plan_features: Mapped[list["PlanFeature"]] = relationship(
        "PlanFeature",
        back_populates="plan",
        lazy="selectin",
    )
    usage_limits: Mapped[list["UsageLimit"]] = relationship(
        "UsageLimit",
        back_populates="plan",
        lazy="selectin",
    )


class PlanFeature(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "plan_features"
    __table_args__ = (UniqueConstraint("plan_id", "feature_id", name="uq_plan_feature"),)

    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    feature_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("features.id", ondelete="CASCADE"),
        nullable=False,
    )

    plan: Mapped["Plan"] = relationship("Plan", back_populates="plan_features")
    feature: Mapped["Feature"] = relationship("Feature", lazy="joined")


class Subscription(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_subscription_tenant"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status", native_enum=False),
        default=SubscriptionStatus.TRIAL,
        nullable=False,
    )
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    plan: Mapped["Plan"] = relationship("Plan", lazy="joined")


class UsageLimit(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "usage_limits"
    __table_args__ = (
        UniqueConstraint("plan_id", "limit_code", name="uq_plan_usage_limit"),
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    limit_code: Mapped[str] = mapped_column(String(128), nullable=False)
    limit_value: Mapped[int] = mapped_column(Integer, nullable=False)
    period: Mapped[UsagePeriod] = mapped_column(
        Enum(UsagePeriod, name="usage_period", native_enum=False),
        default=UsagePeriod.MONTHLY,
        nullable=False,
    )

    plan: Mapped["Plan"] = relationship("Plan", back_populates="usage_limits")


class UsageEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "usage_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    limit_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
