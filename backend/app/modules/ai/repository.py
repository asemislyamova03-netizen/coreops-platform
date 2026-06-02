import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import AIActionProposalStatus, AITaskStatus
from app.modules.ai.models import AIActionProposal, AIAgent, AIApproval, AITask, AIUsageEvent


class AIRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_agents(self, tenant_id: uuid.UUID, *, active_only: bool = True) -> list[AIAgent]:
        stmt = select(AIAgent).where(AIAgent.tenant_id == tenant_id).order_by(AIAgent.name)
        if active_only:
            stmt = stmt.where(AIAgent.is_active.is_(True))
        return list(self.db.scalars(stmt).all())

    def get_agent(self, tenant_id: uuid.UUID, agent_id: uuid.UUID) -> AIAgent | None:
        stmt = select(AIAgent).where(AIAgent.tenant_id == tenant_id, AIAgent.id == agent_id)
        return self.db.scalar(stmt)

    def get_agent_by_code(self, tenant_id: uuid.UUID, code: str) -> AIAgent | None:
        stmt = select(AIAgent).where(AIAgent.tenant_id == tenant_id, AIAgent.code == code)
        return self.db.scalar(stmt)

    def create_agent(self, **kwargs) -> AIAgent:
        agent = AIAgent(**kwargs)
        self.db.add(agent)
        self.db.flush()
        return agent

    def list_tasks(
        self,
        tenant_id: uuid.UUID,
        *,
        agent_id: uuid.UUID | None = None,
        status: AITaskStatus | None = None,
        limit: int = 50,
    ) -> list[AITask]:
        stmt = (
            select(AITask)
            .where(AITask.tenant_id == tenant_id)
            .options(selectinload(AITask.agent), selectinload(AITask.proposals))
            .order_by(AITask.created_at.desc())
            .limit(limit)
        )
        if agent_id:
            stmt = stmt.where(AITask.agent_id == agent_id)
        if status:
            stmt = stmt.where(AITask.status == status)
        return list(self.db.scalars(stmt).all())

    def get_task(self, tenant_id: uuid.UUID, task_id: uuid.UUID) -> AITask | None:
        stmt = (
            select(AITask)
            .where(AITask.tenant_id == tenant_id, AITask.id == task_id)
            .options(selectinload(AITask.agent), selectinload(AITask.proposals))
        )
        return self.db.scalar(stmt)

    def create_task(self, **kwargs) -> AITask:
        task = AITask(**kwargs)
        self.db.add(task)
        self.db.flush()
        return task

    def list_proposals(
        self,
        tenant_id: uuid.UUID,
        *,
        status: AIActionProposalStatus | None = None,
        agent_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[AIActionProposal]:
        stmt = (
            select(AIActionProposal)
            .where(AIActionProposal.tenant_id == tenant_id)
            .options(selectinload(AIActionProposal.approvals))
            .order_by(AIActionProposal.created_at.desc())
            .limit(limit)
        )
        if status:
            stmt = stmt.where(AIActionProposal.status == status)
        if agent_id:
            stmt = stmt.where(AIActionProposal.agent_id == agent_id)
        return list(self.db.scalars(stmt).all())

    def get_proposal(self, tenant_id: uuid.UUID, proposal_id: uuid.UUID) -> AIActionProposal | None:
        stmt = (
            select(AIActionProposal)
            .where(
                AIActionProposal.tenant_id == tenant_id,
                AIActionProposal.id == proposal_id,
            )
            .options(selectinload(AIActionProposal.approvals))
        )
        return self.db.scalar(stmt)

    def create_proposal(self, **kwargs) -> AIActionProposal:
        proposal = AIActionProposal(**kwargs)
        self.db.add(proposal)
        self.db.flush()
        return proposal

    def create_approval(self, **kwargs) -> AIApproval:
        approval = AIApproval(**kwargs)
        self.db.add(approval)
        self.db.flush()
        return approval

    def create_usage_event(self, **kwargs) -> AIUsageEvent:
        event = AIUsageEvent(**kwargs)
        self.db.add(event)
        self.db.flush()
        return event

    def list_usage_events(
        self,
        tenant_id: uuid.UUID,
        *,
        agent_id: uuid.UUID | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AIUsageEvent]:
        stmt = (
            select(AIUsageEvent)
            .where(AIUsageEvent.tenant_id == tenant_id)
            .order_by(AIUsageEvent.created_at.desc())
            .limit(limit)
        )
        if agent_id:
            stmt = stmt.where(AIUsageEvent.agent_id == agent_id)
        if since:
            stmt = stmt.where(AIUsageEvent.created_at >= since)
        return list(self.db.scalars(stmt).all())

    def sum_usage(
        self,
        tenant_id: uuid.UUID,
        *,
        since: datetime | None = None,
    ) -> tuple[int, float]:
        from sqlalchemy import func

        stmt = select(
            func.coalesce(func.sum(AIUsageEvent.tokens_used), 0),
            func.coalesce(func.sum(AIUsageEvent.cost_units), 0),
        ).where(AIUsageEvent.tenant_id == tenant_id)
        if since:
            stmt = stmt.where(AIUsageEvent.created_at >= since)
        row = self.db.execute(stmt).one()
        return int(row[0] or 0), float(row[1] or 0)
