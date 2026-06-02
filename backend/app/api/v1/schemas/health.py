from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok", "degraded"])
    app: str
    environment: str
    database: str = Field(..., examples=["connected", "unavailable"])
