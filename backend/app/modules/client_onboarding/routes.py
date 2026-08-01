from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.exceptions import CoreOpsError
from app.modules.client_onboarding.schemas import ClientSignupRequest, ClientSignupResponse
from app.modules.client_onboarding.service import ClientOnboardingService

router = APIRouter(prefix="/client-onboarding", tags=["client-onboarding"])


@router.post("/signup", response_model=ClientSignupResponse, status_code=201)
def client_signup(
    payload: ClientSignupRequest,
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ClientSignupResponse:
    """Public (no app-auth) atomic client signup → tenant_owner + parties/marketing.

    Provider company and module whitelist are server-controlled only.
    """
    if not idempotency_key or not idempotency_key.strip():
        raise CoreOpsError("Idempotency-Key header is required")

    return ClientOnboardingService(db).signup(
        payload,
        idempotency_key=idempotency_key,
        request=request,
    )
