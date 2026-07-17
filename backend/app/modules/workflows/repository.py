import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import WorkItemStatus
from app.modules.workflows.models import (
    Activity,
    Pipeline,
    PipelineStage,
    Task,
    WorkItem,
)


class WorkflowRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_pipelines(self, tenant_id: uuid.UUID) -> list[Pipeline]:
        stmt = (
            select(Pipeline)
            .where(Pipeline.tenant_id == tenant_id)
            .options(selectinload(Pipeline.stages))
            .order_by(Pipeline.name)
        )
        return list(self.db.scalars(stmt).all())

    def get_pipeline(self, tenant_id: uuid.UUID, pipeline_id: uuid.UUID) -> Pipeline | None:
        stmt = (
            select(Pipeline)
            .where(Pipeline.tenant_id == tenant_id, Pipeline.id == pipeline_id)
            .options(selectinload(Pipeline.stages))
        )
        return self.db.scalar(stmt)

    def get_pipeline_by_code(self, tenant_id: uuid.UUID, code: str) -> Pipeline | None:
        stmt = (
            select(Pipeline)
            .where(Pipeline.tenant_id == tenant_id, Pipeline.code == code)
            .options(selectinload(Pipeline.stages))
        )
        return self.db.scalar(stmt)

    def create_pipeline(self, **kwargs) -> Pipeline:
        pipeline = Pipeline(**kwargs)
        self.db.add(pipeline)
        self.db.flush()
        return pipeline

    def create_stage(self, **kwargs) -> PipelineStage:
        stage = PipelineStage(**kwargs)
        self.db.add(stage)
        self.db.flush()
        return stage

    def get_stage(self, tenant_id: uuid.UUID, stage_id: uuid.UUID) -> PipelineStage | None:
        stmt = (
            select(PipelineStage)
            .join(Pipeline)
            .where(Pipeline.tenant_id == tenant_id, PipelineStage.id == stage_id)
        )
        return self.db.scalar(stmt)

    def get_stage_by_code(
        self,
        tenant_id: uuid.UUID,
        pipeline_id: uuid.UUID,
        code: str,
    ) -> PipelineStage | None:
        stmt = (
            select(PipelineStage)
            .join(Pipeline)
            .where(
                Pipeline.tenant_id == tenant_id,
                PipelineStage.pipeline_id == pipeline_id,
                PipelineStage.code == code,
            )
        )
        return self.db.scalar(stmt)

    def list_work_items(
        self,
        tenant_id: uuid.UUID,
        *,
        pipeline_id: uuid.UUID | None = None,
        stage_id: uuid.UUID | None = None,
        status: WorkItemStatus | None = None,
        work_item_type: str | None = None,
        primary_party_id: uuid.UUID | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[WorkItem]:
        stmt = (
            select(WorkItem)
            .where(WorkItem.tenant_id == tenant_id)
            .options(selectinload(WorkItem.participants))
            .order_by(WorkItem.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if pipeline_id:
            stmt = stmt.where(WorkItem.pipeline_id == pipeline_id)
        if stage_id:
            stmt = stmt.where(WorkItem.stage_id == stage_id)
        if status:
            stmt = stmt.where(WorkItem.status == status)
        if work_item_type:
            stmt = stmt.where(WorkItem.work_item_type == work_item_type)
        if primary_party_id:
            stmt = stmt.where(WorkItem.primary_party_id == primary_party_id)
        if search:
            stmt = stmt.where(WorkItem.title.ilike(f"%{search}%"))
        return list(self.db.scalars(stmt).all())

    def get_work_item(self, tenant_id: uuid.UUID, work_item_id: uuid.UUID) -> WorkItem | None:
        stmt = (
            select(WorkItem)
            .where(WorkItem.tenant_id == tenant_id, WorkItem.id == work_item_id)
            .options(
                selectinload(WorkItem.participants),
                selectinload(WorkItem.activities),
                selectinload(WorkItem.tasks),
            )
        )
        return self.db.scalar(stmt)

    def get_work_item_for_update(
        self,
        tenant_id: uuid.UUID,
        work_item_id: uuid.UUID,
    ) -> WorkItem | None:
        """Tenant-scoped WorkItem with row lock. SQLite may no-op FOR UPDATE."""
        stmt = (
            select(WorkItem)
            .where(WorkItem.tenant_id == tenant_id, WorkItem.id == work_item_id)
            .options(
                selectinload(WorkItem.participants),
                selectinload(WorkItem.activities),
                selectinload(WorkItem.tasks),
            )
            .with_for_update()
        )
        return self.db.scalar(stmt)

    def create_work_item(self, **kwargs) -> WorkItem:
        item = WorkItem(**kwargs)
        self.db.add(item)
        self.db.flush()
        return item

    def add_participant(self, **kwargs):
        from app.modules.workflows.models import WorkItemParticipant

        row = WorkItemParticipant(**kwargs)
        self.db.add(row)
        self.db.flush()
        return row

    def add_activity(self, **kwargs) -> Activity:
        row = Activity(**kwargs)
        self.db.add(row)
        self.db.flush()
        return row

    def add_task(self, **kwargs) -> Task:
        row = Task(**kwargs)
        self.db.add(row)
        self.db.flush()
        return row

    def delete_work_item(self, item: WorkItem) -> None:
        self.db.delete(item)
