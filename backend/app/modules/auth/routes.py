from fastapi import APIRouter, Depends, Request

from sqlalchemy.orm import Session



from app.core.deps import get_current_user, get_db

from app.core.enums import SecurityEventType

from app.core.exceptions import AuthenticationError

from app.core.security import TOKEN_TYPE_ACCESS, TOKEN_TYPE_REFRESH, get_token_subject

from app.modules.audit.recorder import AuditRecorder

from app.modules.auth.models import User

from app.modules.auth.schemas import (

    LoginRequest,

    MeResponse,

    RefreshRequest,

    RegisterRequest,

    TokenPair,

    UserResponse,

)

from app.modules.auth.service import AuthService



router = APIRouter(prefix="/auth", tags=["auth"])





@router.post("/register", response_model=TokenPair, status_code=201)

def register(

    payload: RegisterRequest,

    request: Request,

    db: Session = Depends(get_db),

) -> TokenPair:

    result = AuthService(db).register_provider_owner(payload)

    AuditRecorder(db).security_event(

        event_type=SecurityEventType.REGISTER,

        email=payload.email,

        request=request,

        details_json={"company_slug": payload.company_slug},

    )

    db.commit()

    return result





@router.post("/login", response_model=TokenPair)

def login(

    payload: LoginRequest,

    request: Request,

    db: Session = Depends(get_db),

) -> TokenPair:

    service = AuthService(db)

    try:

        result = service.login(payload.email, payload.password)

        user_id = get_token_subject(result.access_token, TOKEN_TYPE_ACCESS)

        AuditRecorder(db).security_event(

            event_type=SecurityEventType.LOGIN_SUCCESS,

            user_id=user_id,

            email=payload.email,

            request=request,

        )

        db.commit()

        return result

    except AuthenticationError:

        AuditRecorder(db).security_event(

            event_type=SecurityEventType.LOGIN_FAILED,

            email=payload.email,

            request=request,

        )

        db.commit()

        raise





@router.post("/refresh", response_model=TokenPair)

def refresh(

    payload: RefreshRequest,

    request: Request,

    db: Session = Depends(get_db),

) -> TokenPair:

    result = AuthService(db).refresh(payload.refresh_token)

    user_id = get_token_subject(result.access_token, TOKEN_TYPE_ACCESS)

    AuditRecorder(db).security_event(

        event_type=SecurityEventType.TOKEN_REFRESH,

        user_id=user_id,

        request=request,

    )

    db.commit()

    return result





@router.get("/me", response_model=MeResponse)

def me(

    current_user: User = Depends(get_current_user),

    db: Session = Depends(get_db),

) -> MeResponse:

    return AuthService(db).get_me(current_user.id)


