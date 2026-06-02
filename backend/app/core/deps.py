import uuid
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import SessionLocal
from app.core.enums import ProviderRole
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.permissions import user_is_provider_owner
from app.core.security import TOKEN_TYPE_ACCESS, get_token_subject
from app.modules.auth.models import User
from app.modules.provider.models import ProviderStaff
from app.modules.tenants.models import UserTenantMembership

bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _load_user(db: Session, user_id: uuid.UUID) -> User:
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.provider_staff).selectinload(ProviderStaff.provider_company),
            selectinload(User.tenant_memberships).selectinload(UserTenantMembership.tenant),
        )
    )
    user = db.scalar(stmt)
    if not user:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("Account is disabled")
    return user


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if credentials is None:
        raise AuthenticationError("Not authenticated")

    try:
        user_id = get_token_subject(credentials.credentials, TOKEN_TYPE_ACCESS)
    except ValueError as exc:
        raise AuthenticationError("Invalid access token") from exc

    return _load_user(db, user_id)


def require_provider_owner(
    current_user: User = Depends(get_current_user),
) -> User:
    if not user_is_provider_owner(current_user):
        raise PermissionDeniedError("Provider owner role required")
    return current_user


CurrentUser = Annotated[User, Depends(get_current_user)]
