from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "CoreOps Platform"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://coreops:coreops@localhost:5432/coreops"

    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    storage_path: str = "./storage"
    seed_on_startup: bool = True

    public_leads_enabled: bool = False
    public_leads_target_tenant_id: str | None = None
    public_leads_pipeline_id: str | None = None
    public_leads_stage_id: str | None = None
    public_leads_created_by_user_id: str | None = None
    public_leads_allowed_origins: str = ""
    public_leads_telegram_bot_token: str | None = None
    public_leads_telegram_chat_id: str | None = None
    # Public leads rate limit (in-memory MVP; env overrides optional)
    public_leads_rate_limit_enabled: bool = True
    public_leads_rate_limit_window_seconds: int = 600
    public_leads_rate_limit_max_requests: int = 5
    public_leads_rate_limit_hour_window_seconds: int = 3600
    public_leads_rate_limit_hour_max_requests: int = 20

    # Process Overlay LOCAL/ops bootstrap — disabled by default; never enable in production
    process_overlay_bootstrap_enabled: bool = False

    @property
    def public_leads_allowed_origin_list(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.public_leads_allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
