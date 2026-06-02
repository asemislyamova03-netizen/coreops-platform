import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.entitlements import EntitlementService
from app.core.enums import (
    AIActionProposalStatus,
    AIActionType,
    AIApprovalDecision,
    AITaskStatus,
    AuditAction,
)
from app.modules.audit.recorder import AuditRecorder
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.modules.ai.critical_actions import is_critical_action
from app.modules.ai.models import AIActionProposal
from app.modules.ai.repository import AIRepository
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
from app.modules.auth.models import User


class AIService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = AIRepository(db)
        self.entitlements = EntitlementService(db, tenant_id)

    def list_agents(self, active_only: bool = True) -> list[AIAgentResponse]:
        return [
            AIAgentResponse.model_validate(a)
            for a in self.repo.list_agents(self.tenant_id, active_only=active_only)
        ]

    def get_agent(self, agent_id: uuid.UUID) -> AIAgentResponse:
        agent = self._get_agent_or_404(agent_id)
        return AIAgentResponse.model_validate(agent)

    def create_agent(self, user: User, payload: AIAgentCreate) -> AIAgentResponse:
        if self.repo.get_agent_by_code(self.tenant_id, payload.code):
            raise ConflictError("AI agent code already exists")
        agent = self.repo.create_agent(
            tenant_id=self.tenant_id,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
            **payload.model_dump(),
        )
        self._record_usage(agent_id=agent.id, event_type="agent.created", tokens_used=0)
        return AIAgentResponse.model_validate(agent)

    def update_agent(
        self,
        user: User,
        agent_id: uuid.UUID,
        payload: AIAgentUpdate,
    ) -> AIAgentResponse:
        agent = self._get_agent_or_404(agent_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(agent, key, value)
        agent.updated_by_user_id = user.id
        self.db.flush()
        return AIAgentResponse.model_validate(agent)

    def import_agents_from_config(self, user: User, agents_config: list[dict]) -> int:
        created = 0
        for item in agents_config:
            code = item["code"]
            if self.repo.get_agent_by_code(self.tenant_id, code):
                continue
            self.repo.create_agent(
                tenant_id=self.tenant_id,
                code=code,
                name=item["name"],
                role_code=item.get("role_code", code),
                description=item.get("description"),
                system_prompt=item.get("system_prompt"),
                config_json=item.get("config_json", {}),
                is_active=True,
                requires_approval_for_critical=True,
                created_by_user_id=user.id,
                updated_by_user_id=user.id,
            )
            created += 1
        return created

    def list_tasks(
        self,
        *,
        agent_id: uuid.UUID | None = None,
        status: AITaskStatus | None = None,
        limit: int = 50,
    ) -> list[AITaskResponse]:
        tasks = self.repo.list_tasks(
            self.tenant_id,
            agent_id=agent_id,
            status=status,
            limit=limit,
        )
        return [AITaskResponse.model_validate(t) for t in tasks]

    def get_task(self, task_id: uuid.UUID) -> AITaskResponse:
        task = self._get_task_or_404(task_id)
        return AITaskResponse.model_validate(task)

    def create_task(self, user: User, payload: AITaskCreate) -> AITaskResponse:
        self.entitlements.assert_feature("ai.tasks.create")
        agent = self._get_agent_or_404(payload.agent_id)
        if not agent.is_active:
            raise ConflictError("AI agent is not active")

        task = self.repo.create_task(
            tenant_id=self.tenant_id,
            agent_id=agent.id,
            task_type=payload.task_type,
            title=payload.title,
            input_json=payload.input_json,
            context_entity_type=payload.context_entity_type,
            context_entity_id=payload.context_entity_id,
            status=AITaskStatus.PENDING,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )
        self._record_usage(
            agent_id=agent.id,
            task_id=task.id,
            event_type="task.created",
            tokens_used=100,
        )

        if payload.run_mock:
            self._run_mock_task(task, agent, user)

        self.db.refresh(task)
        return AITaskResponse.model_validate(task)

    def list_proposals(
        self,
        *,
        status: AIActionProposalStatus | None = None,
        agent_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[AIActionProposalResponse]:
        proposals = self.repo.list_proposals(
            self.tenant_id,
            status=status,
            agent_id=agent_id,
            limit=limit,
        )
        return [AIActionProposalResponse.model_validate(p) for p in proposals]

    def get_proposal(self, proposal_id: uuid.UUID) -> AIActionProposalResponse:
        proposal = self._get_proposal_or_404(proposal_id)
        return AIActionProposalResponse.model_validate(proposal)

    def create_proposal(
        self,
        user: User,
        payload: AIActionProposalCreate,
    ) -> AIActionProposalResponse:
        agent = self._get_agent_or_404(payload.agent_id)
        if payload.task_id:
            self._get_task_or_404(payload.task_id)

        critical = is_critical_action(payload.action_type)
        proposal = self.repo.create_proposal(
            tenant_id=self.tenant_id,
            agent_id=agent.id,
            task_id=payload.task_id,
            action_type=payload.action_type,
            title=payload.title,
            description=payload.description,
            payload_json=payload.payload_json,
            target_entity_type=payload.target_entity_type,
            target_entity_id=payload.target_entity_id,
            is_critical=critical,
            status=AIActionProposalStatus.PENDING,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        self._record_usage(
            agent_id=agent.id,
            task_id=payload.task_id,
            proposal_id=proposal.id,
            event_type="proposal.created",
            tokens_used=50,
            metadata={"is_critical": critical},
        )
        return AIActionProposalResponse.model_validate(proposal)

    def approve_proposal(
        self,
        user: User,
        proposal_id: uuid.UUID,
        payload: AIApprovalRequest,
    ) -> AIActionProposalResponse:
        proposal = self._get_proposal_or_404(proposal_id)
        self._ensure_pending(proposal)

        self.repo.create_approval(
            tenant_id=self.tenant_id,
            proposal_id=proposal.id,
            approver_user_id=user.id,
            decision=AIApprovalDecision.APPROVED,
            comment=payload.comment,
            decided_at=datetime.now(UTC),
        )
        proposal.status = AIActionProposalStatus.APPROVED
        AuditRecorder(self.db).audit_log(
            action=AuditAction.APPROVE,
            summary=f"AI proposal approved: {proposal.title}",
            tenant_id=self.tenant_id,
            user_id=user.id,
            entity_type="ai_action_proposal",
            entity_id=proposal.id,
            ai_proposal_id=proposal.id,
            approved_by_user_id=user.id,
            metadata_json={"action_type": proposal.action_type.value},
        )
        self._record_usage(
            agent_id=proposal.agent_id,
            proposal_id=proposal.id,
            event_type="proposal.approved",
            metadata={"approver_id": str(user.id)},
        )
        self.db.flush()
        self.db.refresh(proposal)
        return AIActionProposalResponse.model_validate(proposal)

    def reject_proposal(
        self,
        user: User,
        proposal_id: uuid.UUID,
        payload: AIApprovalRequest,
    ) -> AIActionProposalResponse:
        proposal = self._get_proposal_or_404(proposal_id)
        self._ensure_pending(proposal)

        self.repo.create_approval(
            tenant_id=self.tenant_id,
            proposal_id=proposal.id,
            approver_user_id=user.id,
            decision=AIApprovalDecision.REJECTED,
            comment=payload.comment,
            decided_at=datetime.now(UTC),
        )
        proposal.status = AIActionProposalStatus.REJECTED
        AuditRecorder(self.db).audit_log(
            action=AuditAction.REJECT,
            summary=f"AI proposal rejected: {proposal.title}",
            tenant_id=self.tenant_id,
            user_id=user.id,
            entity_type="ai_action_proposal",
            entity_id=proposal.id,
            ai_proposal_id=proposal.id,
            approved_by_user_id=user.id,
        )
        self._record_usage(
            agent_id=proposal.agent_id,
            proposal_id=proposal.id,
            event_type="proposal.rejected",
            metadata={"approver_id": str(user.id)},
        )
        self.db.flush()
        self.db.refresh(proposal)
        return AIActionProposalResponse.model_validate(proposal)

    def execute_proposal(self, user: User, proposal_id: uuid.UUID) -> AIActionProposalResponse:
        proposal = self._get_proposal_or_404(proposal_id)
        agent = self._get_agent_or_404(proposal.agent_id)

        if proposal.status == AIActionProposalStatus.EXECUTED:
            raise ConflictError("Proposal already executed")
        if proposal.status == AIActionProposalStatus.REJECTED:
            raise ConflictError("Rejected proposals cannot be executed")
        if proposal.status == AIActionProposalStatus.CANCELLED:
            raise ConflictError("Cancelled proposals cannot be executed")

        if proposal.is_critical and agent.requires_approval_for_critical:
            if proposal.status != AIActionProposalStatus.APPROVED:
                raise PermissionDeniedError(
                    "Critical AI actions require human approval before execution"
                )

        proposal.status = AIActionProposalStatus.EXECUTED
        proposal.executed_at = datetime.now(UTC)
        proposal.execution_result_json = {
            "mock": True,
            "executed_by_user_id": str(user.id),
            "action_type": proposal.action_type.value,
            "message": "Action executed in mock mode (no side effects on core data)",
        }
        AuditRecorder(self.db).audit_log(
            action=AuditAction.EXECUTE,
            summary=f"AI proposal executed: {proposal.title}",
            tenant_id=self.tenant_id,
            user_id=user.id,
            entity_type="ai_action_proposal",
            entity_id=proposal.id,
            ai_proposal_id=proposal.id,
            approved_by_user_id=user.id if proposal.is_critical else None,
            metadata_json={"action_type": proposal.action_type.value, "mock": True},
        )
        self._record_usage(
            agent_id=proposal.agent_id,
            proposal_id=proposal.id,
            event_type="proposal.executed",
            tokens_used=25,
        )
        self.db.flush()
        self.db.refresh(proposal)
        return AIActionProposalResponse.model_validate(proposal)

    def list_usage(
        self,
        *,
        agent_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> list[AIUsageEventResponse]:
        events = self.repo.list_usage_events(
            self.tenant_id,
            agent_id=agent_id,
            limit=limit,
        )
        return [AIUsageEventResponse.model_validate(e) for e in events]

    def get_usage_summary(self) -> AIUsageSummaryResponse:
        tokens, cost = self.repo.sum_usage(self.tenant_id)
        events = self.repo.list_usage_events(self.tenant_id, limit=1000)
        return AIUsageSummaryResponse(
            total_tokens=tokens,
            total_cost_units=cost,
            events_count=len(events),
        )

    def _run_mock_task(self, task, agent, user: User) -> None:
        task.status = AITaskStatus.RUNNING
        self.db.flush()

        action_type = AIActionType.CHANGE_WORK_ITEM_STATUS
        if task.task_type == "document_review":
            action_type = AIActionType.SEND_DOCUMENT
        elif task.task_type == "finance_assist":
            action_type = AIActionType.CREATE_INVOICE

        critical = is_critical_action(action_type)
        proposal = self.repo.create_proposal(
            tenant_id=self.tenant_id,
            agent_id=agent.id,
            task_id=task.id,
            action_type=action_type,
            title=f"Proposed: {action_type.value}",
            description="Auto-generated mock proposal from task",
            payload_json={"source": "mock_task", "task_type": task.task_type},
            target_entity_type=task.context_entity_type,
            target_entity_id=task.context_entity_id,
            is_critical=critical,
            status=AIActionProposalStatus.PENDING,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )

        task.status = AITaskStatus.COMPLETED
        task.completed_at = datetime.now(UTC)
        task.output_json = {
            "mock": True,
            "proposal_id": str(proposal.id),
            "proposal_requires_approval": critical,
        }
        task.updated_by_user_id = user.id
        self._record_usage(
            agent_id=agent.id,
            task_id=task.id,
            proposal_id=proposal.id,
            event_type="task.completed",
            tokens_used=200,
        )

    def _ensure_pending(self, proposal: AIActionProposal) -> None:
        if proposal.status != AIActionProposalStatus.PENDING:
            raise ConflictError(f"Proposal is not pending (status: {proposal.status.value})")
        if proposal.expires_at and self._is_expired(proposal.expires_at):
            proposal.status = AIActionProposalStatus.EXPIRED
            self.db.flush()
            raise ConflictError("Proposal has expired")

    @staticmethod
    def _is_expired(expires_at: datetime) -> bool:
        now = datetime.now(UTC)
        if expires_at.tzinfo is None:
            return expires_at < now.replace(tzinfo=None)
        return expires_at < now

    def _record_usage(
        self,
        *,
        event_type: str,
        tokens_used: int = 0,
        cost_units: float = 0,
        agent_id: uuid.UUID | None = None,
        task_id: uuid.UUID | None = None,
        proposal_id: uuid.UUID | None = None,
        metadata: dict | None = None,
    ) -> None:
        self.repo.create_usage_event(
            tenant_id=self.tenant_id,
            agent_id=agent_id,
            task_id=task_id,
            proposal_id=proposal_id,
            event_type=event_type,
            tokens_used=tokens_used,
            cost_units=cost_units,
            metadata_json=metadata or {},
        )

    def _get_agent_or_404(self, agent_id: uuid.UUID):
        agent = self.repo.get_agent(self.tenant_id, agent_id)
        if not agent:
            raise NotFoundError("AI agent not found")
        return agent

    def _get_task_or_404(self, task_id: uuid.UUID):
        task = self.repo.get_task(self.tenant_id, task_id)
        if not task:
            raise NotFoundError("AI task not found")
        return task

    def _get_proposal_or_404(self, proposal_id: uuid.UUID):
        proposal = self.repo.get_proposal(self.tenant_id, proposal_id)
        if not proposal:
            raise NotFoundError("AI action proposal not found")
        return proposal
