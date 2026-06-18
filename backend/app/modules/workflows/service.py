import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.enums import ActivityType, WorkItemStatus
from app.core.exceptions import ConflictError, NotFoundError
from app.modules.auth.models import User
from app.modules.parties.custom_fields import CustomFieldService
from app.modules.parties.repository import PartyRepository
from app.modules.workflows.models import ENTITY_WORK_ITEM
from app.modules.workflows.repository import WorkflowRepository
from app.modules.workflows.schemas import (
    ActivityCreate,
    ActivityResponse,
    MoveStageRequest,
    PipelineCreate,
    PipelineResponse,
    PipelineUpdate,
    TaskCreate,
    TaskResponse,
    WorkItemCreate,
    WorkItemResponse,
    WorkItemUpdate,
)


class WorkflowService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = WorkflowRepository(db)
        self.parties = PartyRepository(db)
        self.custom_fields = CustomFieldService(db, tenant_id)

    def list_pipelines(self) -> list[PipelineResponse]:
        return [PipelineResponse.model_validate(p) for p in self.repo.list_pipelines(self.tenant_id)]

    def get_pipeline(self, pipeline_id: uuid.UUID) -> PipelineResponse:
        pipeline = self.repo.get_pipeline(self.tenant_id, pipeline_id)
        if not pipeline:
            raise NotFoundError("Pipeline not found")
        return PipelineResponse.model_validate(pipeline)

    def create_pipeline(self, payload: PipelineCreate) -> PipelineResponse:
        if self.repo.get_pipeline_by_code(self.tenant_id, payload.code):
            raise ConflictError("Pipeline code already exists")

        pipeline = self.repo.create_pipeline(
            tenant_id=self.tenant_id,
            code=payload.code,
            name=payload.name,
            entity_type=payload.entity_type,
            is_default=payload.is_default,
        )
        for stage_data in payload.stages:
            self.repo.create_stage(pipeline_id=pipeline.id, **stage_data.model_dump())

        self.db.flush()
        return self.get_pipeline(pipeline.id)

    def update_pipeline(self, pipeline_id: uuid.UUID, payload: PipelineUpdate) -> PipelineResponse:
        pipeline = self.repo.get_pipeline(self.tenant_id, pipeline_id)
        if not pipeline:
            raise NotFoundError("Pipeline not found")
        if payload.name is not None:
            pipeline.name = payload.name
        if payload.is_default is not None:
            pipeline.is_default = payload.is_default
        self.db.flush()
        return self.get_pipeline(pipeline_id)

    def list_work_items(self, **filters) -> list[WorkItemResponse]:
        items = self.repo.list_work_items(self.tenant_id, **filters)
        return [self._to_work_item_response(item) for item in items]

    def get_work_item(self, work_item_id: uuid.UUID) -> WorkItemResponse:
        item = self._get_work_item_or_404(work_item_id)
        return self._to_work_item_response(item, include_related=True)

    def create_work_item(self, user: User, payload: WorkItemCreate) -> WorkItemResponse:
        pipeline = self.repo.get_pipeline(self.tenant_id, payload.pipeline_id)
        if not pipeline:
            raise NotFoundError("Pipeline not found")

        stage_id = payload.stage_id
        if stage_id is None:
            if not pipeline.stages:
                raise ConflictError("Pipeline has no stages")
            first_stage = min(pipeline.stages, key=lambda s: s.sort_order)
            stage_id = first_stage.id
        else:
            stage = self.repo.get_stage(self.tenant_id, stage_id)
            if not stage or stage.pipeline_id != pipeline.id:
                raise ConflictError("Stage does not belong to the specified pipeline")

        if payload.primary_party_id:
            self._ensure_party(payload.primary_party_id)

        custom_values = self.custom_fields.validate_and_prepare(
            ENTITY_WORK_ITEM, payload.custom_fields
        )

        item = self.repo.create_work_item(
            tenant_id=self.tenant_id,
            pipeline_id=pipeline.id,
            stage_id=stage_id,
            work_item_type=payload.work_item_type,
            title=payload.title,
            description=payload.description,
            primary_party_id=payload.primary_party_id,
            status=payload.status,
            amount=payload.amount,
            currency=payload.currency,
            source=payload.source,
            custom_fields_json={},
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )

        for participant in payload.participants:
            self._ensure_party(participant.party_id)
            self.repo.add_participant(
                tenant_id=self.tenant_id,
                work_item_id=item.id,
                party_id=participant.party_id,
                role=participant.role,
            )

        if custom_values:
            self.custom_fields.upsert_values(ENTITY_WORK_ITEM, item.id, custom_values)

        self.db.flush()
        return self.get_work_item(item.id)

    def update_work_item(
        self,
        user: User,
        work_item_id: uuid.UUID,
        payload: WorkItemUpdate,
    ) -> WorkItemResponse:
        item = self._get_work_item_or_404(work_item_id)

        if payload.stage_id is not None:
            stage = self.repo.get_stage(self.tenant_id, payload.stage_id)
            if not stage or stage.pipeline_id != item.pipeline_id:
                raise ConflictError("Stage does not belong to the work item pipeline")
            item.stage_id = payload.stage_id

        if payload.work_item_type is not None:
            item.work_item_type = payload.work_item_type
        if payload.title is not None:
            item.title = payload.title
        if payload.description is not None:
            item.description = payload.description
        if payload.primary_party_id is not None:
            self._ensure_party(payload.primary_party_id)
            item.primary_party_id = payload.primary_party_id
        if payload.status is not None:
            item.status = payload.status
        if payload.amount is not None:
            item.amount = payload.amount
        if payload.currency is not None:
            item.currency = payload.currency
        if payload.source is not None:
            item.source = payload.source

        if payload.custom_fields is not None:
            custom_values = self.custom_fields.validate_and_prepare(
                ENTITY_WORK_ITEM, payload.custom_fields
            )
            self.custom_fields.upsert_values(ENTITY_WORK_ITEM, item.id, custom_values)

        item.updated_by_user_id = user.id
        self.db.flush()
        return self.get_work_item(item.id)

    def move_stage(
        self,
        user: User,
        work_item_id: uuid.UUID,
        payload: MoveStageRequest,
    ) -> WorkItemResponse:
        item = self._get_work_item_or_404(work_item_id)
        old_stage_id = item.stage_id

        stage = self.repo.get_stage(self.tenant_id, payload.stage_id)
        if not stage or stage.pipeline_id != item.pipeline_id:
            raise ConflictError("Stage does not belong to the work item pipeline")

        item.stage_id = stage.id
        if stage.is_terminal:
            if stage.code in ("lost", "cancelled", "rejected"):
                item.status = WorkItemStatus.LOST
            else:
                item.status = WorkItemStatus.WON
        else:
            item.status = WorkItemStatus.IN_PROGRESS

        item.updated_by_user_id = user.id

        self.repo.add_activity(
            tenant_id=self.tenant_id,
            work_item_id=item.id,
            activity_type=ActivityType.STATUS_CHANGE,
            title=f"Moved to stage: {stage.name}",
            description=f"stage_id: {old_stage_id} -> {stage.id}",
            occurred_at=datetime.now(UTC),
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )

        self.db.flush()
        return self.get_work_item(item.id)

    def add_activity(
        self,
        user: User,
        work_item_id: uuid.UUID,
        payload: ActivityCreate,
    ) -> ActivityResponse:
        self._get_work_item_or_404(work_item_id)
        occurred_at = payload.occurred_at or datetime.now(UTC)
        activity = self.repo.add_activity(
            tenant_id=self.tenant_id,
            work_item_id=work_item_id,
            activity_type=payload.activity_type,
            title=payload.title,
            description=payload.description,
            occurred_at=occurred_at,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )
        self.db.flush()
        return ActivityResponse.model_validate(activity)

    def add_task(self, user: User, work_item_id: uuid.UUID, payload: TaskCreate) -> TaskResponse:
        self._get_work_item_or_404(work_item_id)
        task = self.repo.add_task(
            tenant_id=self.tenant_id,
            work_item_id=work_item_id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            due_at=payload.due_at,
            assigned_to_user_id=payload.assigned_to_user_id,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )
        self.db.flush()
        return TaskResponse.model_validate(task)

    def delete_work_item(self, work_item_id: uuid.UUID) -> None:
        item = self._get_work_item_or_404(work_item_id)
        self.repo.delete_work_item(item)
        self.db.flush()

    def _get_work_item_or_404(self, work_item_id: uuid.UUID):
        item = self.repo.get_work_item(self.tenant_id, work_item_id)
        if not item:
            raise NotFoundError("Work item not found")
        return item

    def _ensure_party(self, party_id: uuid.UUID) -> None:
        party = self.parties.get_party(self.tenant_id, party_id)
        if not party:
            raise NotFoundError("Party not found")

    def _to_work_item_response(self, item, *, include_related: bool = False) -> WorkItemResponse:
        custom = self.custom_fields.get_values_map(ENTITY_WORK_ITEM, item.id)
        activities: list[ActivityResponse] = []
        tasks: list[TaskResponse] = []
        if include_related:
            activities = [ActivityResponse.model_validate(a) for a in item.activities]
            tasks = [TaskResponse.model_validate(t) for t in item.tasks]
        return WorkItemResponse(
            id=item.id,
            tenant_id=item.tenant_id,
            pipeline_id=item.pipeline_id,
            stage_id=item.stage_id,
            work_item_type=item.work_item_type,
            title=item.title,
            description=item.description,
            primary_party_id=item.primary_party_id,
            status=item.status,
            amount=item.amount,
            currency=item.currency,
            source=item.source,
            custom_fields=custom,
            participants=item.participants,
            activities=activities,
            tasks=tasks,
            created_at=item.created_at,
            updated_at=item.updated_at,
            created_by_user_id=item.created_by_user_id,
            updated_by_user_id=item.updated_by_user_id,
        )
