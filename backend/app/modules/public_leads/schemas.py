from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class PublicLeadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = Field(default=None, max_length=320)
    company: str | None = Field(default=None, max_length=160)
    preferred_channel: str | None = Field(default=None, max_length=40)
    process_area: str | None = Field(default=None, max_length=120)
    message: str | None = Field(default=None, max_length=2000)
    source_page: str = Field(min_length=1, max_length=500)
    utm_source: str | None = Field(default=None, max_length=120)
    utm_medium: str | None = Field(default=None, max_length=120)
    utm_campaign: str | None = Field(default=None, max_length=160)
    utm_content: str | None = Field(default=None, max_length=160)
    utm_term: str | None = Field(default=None, max_length=160)
    referrer: str | None = Field(default=None, max_length=500)
    consent_accepted: bool
    website: str | None = Field(default=None, max_length=200)

    @field_validator("*", mode="before")
    @classmethod
    def _strip_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _validate_required_pairs(self) -> "PublicLeadCreate":
        if not self.consent_accepted:
            raise ValueError("consent_accepted must be true")
        if self.website:
            raise ValueError("website must be empty")
        if not self.phone and not self.email:
            raise ValueError("phone or email is required")
        if not self.message and not self.process_area:
            raise ValueError("message or process_area is required")
        return self


class PublicLeadResponse(BaseModel):
    """Public ack only — no party/work_item/match internals."""

    status: str = "created"
    message: str = "Lead received"
