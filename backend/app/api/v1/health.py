from fastapi import APIRouter

from app.core.config import get_settings
from app.core.database import check_database_connection
from app.api.v1.schemas.health import HealthResponse

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    db_ok = check_database_connection()
    status = "ok" if db_ok else "degraded"
    return HealthResponse(
        status=status,
        app=settings.app_name,
        environment=settings.app_env,
        database="connected" if db_ok else "unavailable",
    )
