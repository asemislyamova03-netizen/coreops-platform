from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_db
from app.modules.public_leads.schemas import PublicLeadCreate, PublicLeadResponse
from app.modules.public_leads.service import PublicLeadService

router = APIRouter(prefix="/public/leads", tags=["public-leads"])


@router.post("", response_model=PublicLeadResponse, status_code=status.HTTP_201_CREATED)
def create_public_lead(
    payload: PublicLeadCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> PublicLeadResponse:
    return PublicLeadService(db, get_settings()).create_lead(
        payload,
        origin=request.headers.get("origin"),
        request=request,
    )
