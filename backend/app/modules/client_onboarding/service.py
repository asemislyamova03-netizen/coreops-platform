"""Atomic generic client self-service onboarding (D1–D3)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import (
    AuditAction,
    ModuleStatus,
    SecurityEventType,
    TenantRole,
    TenantStatus,
)
from app.core.exceptions import (
    ConflictError,
    CoreOpsError,
    PermissionDeniedError,
    ServiceUnavailableError,
)
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.modules.audit.recorder import AuditRecorder
from app.modules.auth.repository import UserRepository
from app.modules.branches.service import BranchService
from app.modules.client_onboarding.constants import CLIENT_ONBOARDING_MODULE_WHITELIST
from app.modules.client_onboarding.models import ClientOnboardingIdempotencyKey
from app.modules.client_onboarding.schemas import (
    ClientSignupRequest,
    ClientSignupResponse,
    ClientSignupTenant,
    ClientSignupUser,
)
from app.modules.module_registry.repository import ModuleRegistryRepository
from app.modules.module_registry.service import ModuleRegistryService
from app.modules.provider.repository import ProviderRepository
from app.modules.tenants.repository import TenantRepository


def _request_hash(payload: ClientSignupRequest) -> str:
    canonical = json.dumps(
        {
            "full_name": payload.full_name.strip(),
            "email": str(payload.email).lower().strip(),
            "tenant_name": payload.tenant_name.strip(),
            "tenant_slug": payload.tenant_slug.strip(),
            # Password participates in fingerprint so same key + different password conflicts.
            "password": payload.password,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ClientOnboardingService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.providers = ProviderRepository(db)
        self.tenants = TenantRepository(db)
        self.modules = ModuleRegistryService(db)
        self.module_repo = ModuleRegistryRepository(db)
        self.branches = BranchService(db)
        self.audit = AuditRecorder(db)

    def signup(
        self,
        payload: ClientSignupRequest,
        *,
        idempotency_key: str,
        request: Request | None = None,
    ) -> ClientSignupResponse:
        settings = get_settings()
        if not settings.client_self_service_onboarding_enabled:
            raise PermissionDeniedError("Client self-service onboarding is disabled")

        provider_slug = (settings.client_onboarding_provider_slug or "").strip()
        if not provider_slug:
            raise ServiceUnavailableError(
                "Onboarding provider is not configured"
            )

        provider = self.providers.get_company_by_slug(provider_slug)
        if provider is None or not provider.is_active:
            raise ServiceUnavailableError(
                "Onboarding provider is not configured"
            )

        key = idempotency_key.strip()
        if not key or len(key) > 128:
            raise CoreOpsError("Invalid Idempotency-Key")

        req_hash = _request_hash(payload)

        existing_key = self.db.scalar(
            select(ClientOnboardingIdempotencyKey).where(
                ClientOnboardingIdempotencyKey.key == key
            )
        )
        if existing_key is not None:
            if existing_key.request_hash != req_hash:
                raise ConflictError("Idempotency-Key reuse with different payload")
            if (
                existing_key.status == "completed"
                and existing_key.user_id
                and existing_key.tenant_id
            ):
                return self._response_for_existing(
                    user_id=existing_key.user_id,
                    tenant_id=existing_key.tenant_id,
                )
            raise ConflictError("Onboarding already in progress for this Idempotency-Key")

        email = str(payload.email).lower().strip()
        if self.users.get_by_email(email):
            raise ConflictError("Email already registered")

        if self.tenants.get_by_provider_and_slug(provider.id, payload.tenant_slug):
            raise ConflictError("Tenant slug already exists for this provider")

        for code in CLIENT_ONBOARDING_MODULE_WHITELIST:
            if not self.module_repo.get_definition(code):
                raise ServiceUnavailableError(
                    f"Required module definition '{code}' is missing"
                )

        try:
            user = self.users.create(
                email=email,
                hashed_password=hash_password(payload.password),
                full_name=payload.full_name.strip(),
            )

            # Invariant: never attach ProviderStaff / provider_owner.
            if self.providers.get_staff_for_user(user.id) is not None:
                raise ConflictError("Unexpected provider staff assignment")

            tenant = self.tenants.create(
                provider_company_id=provider.id,
                name=payload.tenant_name.strip(),
                slug=payload.tenant_slug.strip(),
                status=TenantStatus.TRIAL,
            )

            default_branch_id = self.branches.ensure_default_branch(tenant.id)
            if not default_branch_id:
                raise ServiceUnavailableError("Default branch was not created")

            membership = self.tenants.create_membership(
                tenant_id=tenant.id,
                user_id=user.id,
                role=TenantRole.TENANT_OWNER,
            )
            if membership.role != TenantRole.TENANT_OWNER:
                raise ConflictError("Tenant owner membership was not assigned")

            # Strict whitelist only — never accept client module lists.
            enabled = self.modules.enable_modules_ordered(
                tenant.id,
                list(CLIENT_ONBOARDING_MODULE_WHITELIST),
                as_trial=False,
            )
            if tuple(enabled) != CLIENT_ONBOARDING_MODULE_WHITELIST:
                raise ConflictError("Module whitelist mismatch after enable")

            active = {
                tm.module_code
                for tm in self.module_repo.list_tenant_modules(tenant.id)
                if tm.status in {ModuleStatus.ENABLED, ModuleStatus.TRIAL}
            }
            if active != set(CLIENT_ONBOARDING_MODULE_WHITELIST):
                raise ConflictError("Unexpected active modules after onboarding")

            now = datetime.now(UTC)
            idem = ClientOnboardingIdempotencyKey(
                key=key,
                request_hash=req_hash,
                status="completed",
                user_id=user.id,
                tenant_id=tenant.id,
                tenant_slug=tenant.slug,
                completed_at=now,
            )
            self.db.add(idem)
            self.db.flush()

            self.audit.security_event(
                event_type=SecurityEventType.CLIENT_ONBOARDING_COMPLETED,
                user_id=user.id,
                tenant_id=tenant.id,
                email=user.email,
                request=request,
                details_json={
                    "tenant_slug": tenant.slug,
                    "modules_enabled": list(CLIENT_ONBOARDING_MODULE_WHITELIST),
                    "provider_slug": provider_slug,
                },
            )
            self.audit.audit_log(
                action=AuditAction.CREATE,
                summary="Client self-service onboarding completed",
                tenant_id=tenant.id,
                user_id=user.id,
                entity_type="tenant",
                entity_id=tenant.id,
                changes_json={
                    "modules_enabled": list(CLIENT_ONBOARDING_MODULE_WHITELIST),
                    "role": TenantRole.TENANT_OWNER.value,
                },
                request=request,
                metadata_json={"flow": "client_onboarding_d1_d3"},
            )

            self.db.commit()
            self.db.refresh(user)
            self.db.refresh(tenant)

            return self._build_response(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                tenant_id=tenant.id,
                tenant_name=tenant.name,
                tenant_slug=tenant.slug,
                default_branch_id=default_branch_id,
            )
        except IntegrityError as exc:
            self.db.rollback()
            # Parallel duplicate email/slug races land here.
            if self.users.get_by_email(email):
                raise ConflictError("Email already registered") from exc
            if self.tenants.get_by_provider_and_slug(provider.id, payload.tenant_slug):
                raise ConflictError(
                    "Tenant slug already exists for this provider"
                ) from exc
            raise ConflictError("Onboarding conflict") from exc
        except Exception:
            self.db.rollback()
            raise

    def _response_for_existing(
        self,
        *,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> ClientSignupResponse:
        user = self.users.get_by_id(user_id)
        tenant = self.tenants.get_by_id(tenant_id)
        if not user or not tenant or not tenant.default_branch_id:
            raise ConflictError("Idempotent onboarding record is incomplete")

        membership = self.tenants.get_membership(tenant_id, user_id)
        if not membership or membership.role != TenantRole.TENANT_OWNER:
            raise ConflictError("Idempotent onboarding membership mismatch")

        if self.providers.get_staff_for_user(user_id) is not None:
            raise ConflictError("Idempotent onboarding has unexpected provider staff")

        active = {
            tm.module_code
            for tm in self.module_repo.list_tenant_modules(tenant_id)
            if tm.status in {ModuleStatus.ENABLED, ModuleStatus.TRIAL}
        }
        if active != set(CLIENT_ONBOARDING_MODULE_WHITELIST):
            raise ConflictError("Idempotent onboarding module mismatch")

        return self._build_response(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            tenant_slug=tenant.slug,
            default_branch_id=tenant.default_branch_id,
        )

    def _build_response(
        self,
        *,
        user_id: uuid.UUID,
        email: str,
        full_name: str,
        tenant_id: uuid.UUID,
        tenant_name: str,
        tenant_slug: str,
        default_branch_id: uuid.UUID,
    ) -> ClientSignupResponse:
        return ClientSignupResponse(
            access_token=create_access_token(user_id),
            refresh_token=create_refresh_token(user_id),
            user=ClientSignupUser(id=user_id, email=email, full_name=full_name),
            tenant=ClientSignupTenant(
                id=tenant_id,
                name=tenant_name,
                slug=tenant_slug,
                default_branch_id=default_branch_id,
                role=TenantRole.TENANT_OWNER,
            ),
            modules_enabled=list(CLIENT_ONBOARDING_MODULE_WHITELIST),
            # React Router basename=/console → browser URL /console/workspace/...
            redirect_path=f"/workspace/{tenant_slug}/marketing/guide",
        )
