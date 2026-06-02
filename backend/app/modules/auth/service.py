import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import ProviderRole
from app.core.exceptions import (
    AuthenticationError,
    BootstrapCompletedError,
    ConflictError,
)
from app.core.security import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    get_token_subject,
    hash_password,
    verify_password,
)
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import (
    MeResponse,
    ProviderStaffInfo,
    RegisterRequest,
    TenantMembershipInfo,
    TokenPair,
    UserResponse,
)
from app.modules.provider.models import ProviderStaff
from app.modules.provider.repository import ProviderRepository
from app.modules.tenants.models import UserTenantMembership


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.providers = ProviderRepository(db)

    def register_provider_owner(self, payload: RegisterRequest) -> TokenPair:
        if self.users.count() > 0:
            raise BootstrapCompletedError(
                "Platform already bootstrapped. Contact the platform operator."
            )

        if self.users.get_by_email(payload.email):
            raise ConflictError("Email already registered")

        if self.providers.get_company_by_slug(payload.company_slug):
            raise ConflictError("Company slug already taken")

        user = self.users.create(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
        )
        company = self.providers.create_company(
            name=payload.company_name,
            slug=payload.company_slug,
        )
        self.providers.create_staff(
            provider_company_id=company.id,
            user_id=user.id,
            role=ProviderRole.PROVIDER_OWNER,
        )
        self.db.commit()
        self.db.refresh(user)

        return self._issue_tokens(user.id)

    def login(self, email: str, password: str) -> TokenPair:
        user = self.users.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Account is disabled")

        return self._issue_tokens(user.id)

    def refresh(self, refresh_token: str) -> TokenPair:
        try:
            user_id = get_token_subject(refresh_token, TOKEN_TYPE_REFRESH)
        except ValueError as exc:
            raise AuthenticationError("Invalid refresh token") from exc

        user = self.users.get_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("Invalid refresh token")

        return self._issue_tokens(user.id)

    def get_me(self, user_id: uuid.UUID) -> MeResponse:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.provider_staff).selectinload(ProviderStaff.provider_company),
                selectinload(User.tenant_memberships).selectinload(
                    UserTenantMembership.tenant
                ),
            )
        )
        user = self.db.scalar(stmt)
        if not user:
            raise AuthenticationError("User not found")

        provider_info: ProviderStaffInfo | None = None
        if user.provider_staff:
            staff = user.provider_staff[0]
            provider_info = ProviderStaffInfo(
                provider_company_id=staff.provider_company_id,
                provider_company_name=staff.provider_company.name,
                role=staff.role,
            )

        tenants: list[TenantMembershipInfo] = []
        for membership in user.tenant_memberships:
            if not membership.is_active:
                continue
            tenants.append(
                TenantMembershipInfo(
                    tenant_id=membership.tenant_id,
                    tenant_name=membership.tenant.name,
                    tenant_slug=membership.tenant.slug,
                    role=membership.role,
                )
            )

        return MeResponse(
            user=UserResponse.model_validate(user),
            provider=provider_info,
            tenants=tenants,
        )

    def _issue_tokens(self, user_id: uuid.UUID) -> TokenPair:
        return TokenPair(
            access_token=create_access_token(user_id),
            refresh_token=create_refresh_token(user_id),
        )
