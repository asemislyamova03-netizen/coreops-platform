import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.entitlements import require_feature
from app.core.enums import WorkItemStatus
from app.core.modules import require_module
from app.core.tenancy import TenantContext
from app.modules.workflows.schemas import (
    ActivityCreate,
    ActivityResponse,
    CloseWorkItemRequest,
    MoveStageRequest,
    PipelineCreate,
    PipelineResponse,
    PipelineUpdate,
    ReopenWorkItemRequest,
    TaskCreate,
    TaskResponse,
    WorkItemCreate,
    WorkItemResponse,
    WorkItemUpdate,
)
from app.modules.workflows.service import WorkflowService

pipelines_router = APIRouter(prefix="/pipelines", tags=["workflows"])
work_items_router = APIRouter(prefix="/work-items", tags=["workflows"])


def _service(ctx: TenantContext, db: Session) -> WorkflowService:
    return WorkflowService(db, ctx.tenant.id)


@pipelines_router.get("", response_model=list[PipelineResponse])
def list_pipelines(
    ctx: TenantContext = Depends(require_module("crm")),
    db: Session = Depends(get_db),
) -> list[PipelineResponse]:
    return _service(ctx, db).list_pipelines()


@pipelines_router.post("", response_model=PipelineResponse, status_code=201)
def create_pipeline(
    payload: PipelineCreate,
    ctx: TenantContext = Depends(require_module("crm")),
    db: Session = Depends(get_db),
) -> PipelineResponse:
    result = _service(ctx, db).create_pipeline(payload)
    db.commit()
    return result


@pipelines_router.get("/{pipeline_id}", response_model=PipelineResponse)
def get_pipeline(
    pipeline_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("crm")),
    db: Session = Depends(get_db),
) -> PipelineResponse:
    return _service(ctx, db).get_pipeline(pipeline_id)


@pipelines_router.patch("/{pipeline_id}", response_model=PipelineResponse)
def update_pipeline(
    pipeline_id: uuid.UUID,
    payload: PipelineUpdate,
    ctx: TenantContext = Depends(require_module("crm")),
    db: Session = Depends(get_db),
) -> PipelineResponse:
    result = _service(ctx, db).update_pipeline(pipeline_id, payload)
    db.commit()
    return result


@work_items_router.get("", response_model=list[WorkItemResponse])
def list_work_items(
    pipeline_id: uuid.UUID | None = None,
    stage_id: uuid.UUID | None = None,
    status: WorkItemStatus | None = None,
    work_item_type: str | None = None,
    primary_party_id: uuid.UUID | None = None,
    search: str | None = Query(default=None, max_length=255),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    ctx: TenantContext = Depends(require_module("crm")),
    db: Session = Depends(get_db),
) -> list[WorkItemResponse]:
    return _service(ctx, db).list_work_items(
        pipeline_id=pipeline_id,
        stage_id=stage_id,
        status=status,
        work_item_type=work_item_type,
        primary_party_id=primary_party_id,
        search=search,
        skip=skip,
        limit=limit,
    )


@work_items_router.post("", response_model=WorkItemResponse, status_code=201)
def create_work_item(
    payload: WorkItemCreate,
    ctx: TenantContext = Depends(require_feature("crm.work_items.create")),
    db: Session = Depends(get_db),
) -> WorkItemResponse:
    result = _service(ctx, db).create_work_item(ctx.user, payload)
    db.commit()
    return result


@work_items_router.get("/{work_item_id}", response_model=WorkItemResponse)
def get_work_item(
    work_item_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("crm")),
    db: Session = Depends(get_db),
) -> WorkItemResponse:
    return _service(ctx, db).get_work_item(work_item_id)


@work_items_router.patch("/{work_item_id}", response_model=WorkItemResponse)
def update_work_item(
    work_item_id: uuid.UUID,
    payload: WorkItemUpdate,
    ctx: TenantContext = Depends(require_module("crm")),
    db: Session = Depends(get_db),
) -> WorkItemResponse:
    result = _service(ctx, db).update_work_item(ctx.user, work_item_id, payload)
    db.commit()
    return result


@work_items_router.delete("/{work_item_id}", status_code=204)
def delete_work_item(
    work_item_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("crm")),
    db: Session = Depends(get_db),
) -> None:
    _service(ctx, db).delete_work_item(work_item_id)
    db.commit()


@work_items_router.post("/{work_item_id}/move-stage", response_model=WorkItemResponse)
def move_work_item_stage(
    work_item_id: uuid.UUID,
    payload: MoveStageRequest,
    ctx: TenantContext = Depends(require_module("crm")),
    db: Session = Depends(get_db),
) -> WorkItemResponse:
    result = _service(ctx, db).move_stage(ctx.user, work_item_id, payload)
    db.commit()
    return result


@work_items_router.post("/{work_item_id}/close", response_model=WorkItemResponse)
def close_work_item(
    work_item_id: uuid.UUID,
    payload: CloseWorkItemRequest,
    ctx: TenantContext = Depends(require_module("crm")),
    db: Session = Depends(get_db),
) -> WorkItemResponse:
    result = _service(ctx, db).close_work_item(ctx.user, work_item_id, payload)
    db.commit()
    return result


@work_items_router.post("/{work_item_id}/reopen", response_model=WorkItemResponse)
def reopen_work_item(
    work_item_id: uuid.UUID,
    payload: ReopenWorkItemRequest = ReopenWorkItemRequest(),
    ctx: TenantContext = Depends(require_module("crm")),
    db: Session = Depends(get_db),
) -> WorkItemResponse:
    result = _service(ctx, db).reopen_work_item(ctx.user, work_item_id, payload)
    db.commit()
    return result


@work_items_router.post(
    "/{work_item_id}/activities",
    response_model=ActivityResponse,
    status_code=201,
)
def create_activity(
    work_item_id: uuid.UUID,
    payload: ActivityCreate,
    ctx: TenantContext = Depends(require_module("crm")),
    db: Session = Depends(get_db),
) -> ActivityResponse:
    result = _service(ctx, db).add_activity(ctx.user, work_item_id, payload)
    db.commit()
    return result


@work_items_router.post(
    "/{work_item_id}/tasks",
    response_model=TaskResponse,
    status_code=201,
)
def create_task(
    work_item_id: uuid.UUID,
    payload: TaskCreate,
    ctx: TenantContext = Depends(require_module("crm")),
    db: Session = Depends(get_db),
) -> TaskResponse:
    result = _service(ctx, db).add_task(ctx.user, work_item_id, payload)
    db.commit()
    return result
