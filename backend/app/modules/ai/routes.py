import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.entitlements import require_feature
from app.core.enums import AIActionProposalStatus, AITaskStatus
from app.core.modules import require_module
from app.core.tenancy import TenantContext
from app.modules.ai.schemas import (
    AIActionProposalCreate,
    AIActionProposalResponse,
    AIAgentCreate,
    AIAgentResponse,
    AIAgentUpdate,
    AIApprovalRequest,
    AITaskCreate,
    AITaskResponse,
    AIUsageEventResponse,
    AIUsageSummaryResponse,
)
from app.modules.ai.service import AIService

agents_router = APIRouter(prefix="/ai/agents", tags=["ai"])
tasks_router = APIRouter(prefix="/ai/tasks", tags=["ai"])
proposals_router = APIRouter(prefix="/ai/action-proposals", tags=["ai"])
usage_router = APIRouter(prefix="/ai/usage", tags=["ai"])


def _service(ctx: TenantContext, db: Session) -> AIService:
    return AIService(db, ctx.tenant.id)


@agents_router.get("", response_model=list[AIAgentResponse])
def list_agents(
    active_only: bool = True,
    ctx: TenantContext = Depends(require_module("ai")),
    db: Session = Depends(get_db),
) -> list[AIAgentResponse]:
    return _service(ctx, db).list_agents(active_only=active_only)


@agents_router.post("", response_model=AIAgentResponse, status_code=201)
def create_agent(
    payload: AIAgentCreate,
    ctx: TenantContext = Depends(require_module("ai")),
    db: Session = Depends(get_db),
) -> AIAgentResponse:
    result = _service(ctx, db).create_agent(ctx.user, payload)
    db.commit()
    return result


@agents_router.get("/{agent_id}", response_model=AIAgentResponse)
def get_agent(
    agent_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("ai")),
    db: Session = Depends(get_db),
) -> AIAgentResponse:
    return _service(ctx, db).get_agent(agent_id)


@agents_router.patch("/{agent_id}", response_model=AIAgentResponse)
def update_agent(
    agent_id: uuid.UUID,
    payload: AIAgentUpdate,
    ctx: TenantContext = Depends(require_module("ai")),
    db: Session = Depends(get_db),
) -> AIAgentResponse:
    result = _service(ctx, db).update_agent(ctx.user, agent_id, payload)
    db.commit()
    return result


@tasks_router.get("", response_model=list[AITaskResponse])
def list_tasks(
    agent_id: uuid.UUID | None = None,
    status: AITaskStatus | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    ctx: TenantContext = Depends(require_module("ai")),
    db: Session = Depends(get_db),
) -> list[AITaskResponse]:
    return _service(ctx, db).list_tasks(agent_id=agent_id, status=status, limit=limit)


@tasks_router.post("", response_model=AITaskResponse, status_code=201)
def create_task(
    payload: AITaskCreate,
    ctx: TenantContext = Depends(require_feature("ai.tasks.create")),
    db: Session = Depends(get_db),
) -> AITaskResponse:
    result = _service(ctx, db).create_task(ctx.user, payload)
    db.commit()
    return result


@tasks_router.get("/{task_id}", response_model=AITaskResponse)
def get_task(
    task_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("ai")),
    db: Session = Depends(get_db),
) -> AITaskResponse:
    return _service(ctx, db).get_task(task_id)


@proposals_router.get("", response_model=list[AIActionProposalResponse])
def list_proposals(
    status: AIActionProposalStatus | None = None,
    agent_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    ctx: TenantContext = Depends(require_module("ai")),
    db: Session = Depends(get_db),
) -> list[AIActionProposalResponse]:
    return _service(ctx, db).list_proposals(status=status, agent_id=agent_id, limit=limit)


@proposals_router.post("", response_model=AIActionProposalResponse, status_code=201)
def create_proposal(
    payload: AIActionProposalCreate,
    ctx: TenantContext = Depends(require_module("ai")),
    db: Session = Depends(get_db),
) -> AIActionProposalResponse:
    result = _service(ctx, db).create_proposal(ctx.user, payload)
    db.commit()
    return result


@proposals_router.get("/{proposal_id}", response_model=AIActionProposalResponse)
def get_proposal(
    proposal_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("ai")),
    db: Session = Depends(get_db),
) -> AIActionProposalResponse:
    return _service(ctx, db).get_proposal(proposal_id)


@proposals_router.post("/{proposal_id}/approve", response_model=AIActionProposalResponse)
def approve_proposal(
    proposal_id: uuid.UUID,
    payload: AIApprovalRequest = AIApprovalRequest(),
    ctx: TenantContext = Depends(require_module("ai")),
    db: Session = Depends(get_db),
) -> AIActionProposalResponse:
    result = _service(ctx, db).approve_proposal(ctx.user, proposal_id, payload)
    db.commit()
    return result


@proposals_router.post("/{proposal_id}/reject", response_model=AIActionProposalResponse)
def reject_proposal(
    proposal_id: uuid.UUID,
    payload: AIApprovalRequest = AIApprovalRequest(),
    ctx: TenantContext = Depends(require_module("ai")),
    db: Session = Depends(get_db),
) -> AIActionProposalResponse:
    result = _service(ctx, db).reject_proposal(ctx.user, proposal_id, payload)
    db.commit()
    return result


@proposals_router.post("/{proposal_id}/execute", response_model=AIActionProposalResponse)
def execute_proposal(
    proposal_id: uuid.UUID,
    ctx: TenantContext = Depends(require_module("ai")),
    db: Session = Depends(get_db),
) -> AIActionProposalResponse:
    result = _service(ctx, db).execute_proposal(ctx.user, proposal_id)
    db.commit()
    return result


@usage_router.get("", response_model=list[AIUsageEventResponse])
def list_usage_events(
    agent_id: uuid.UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    ctx: TenantContext = Depends(require_module("ai")),
    db: Session = Depends(get_db),
) -> list[AIUsageEventResponse]:
    return _service(ctx, db).list_usage(agent_id=agent_id, limit=limit)


@usage_router.get("/summary", response_model=AIUsageSummaryResponse)
def usage_summary(
    ctx: TenantContext = Depends(require_module("ai")),
    db: Session = Depends(get_db),
) -> AIUsageSummaryResponse:
    return _service(ctx, db).get_usage_summary()
