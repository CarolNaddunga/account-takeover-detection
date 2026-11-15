from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    event_id: str = Field(min_length=1, max_length=100)
    account_id: str = Field(min_length=1, max_length=100)
    event_time: datetime
    result: Literal["success", "failure"]
    ip_address: str = Field(min_length=1, max_length=64)
    device_id: str = Field(min_length=1, max_length=100)

    @field_validator("event_time")
    @classmethod
    def event_time_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event_time must include a timezone, for example Z")
        return value


class LoginEvent(LoginInput):
    received_at: datetime

    @field_validator("received_at")
    @classmethod
    def received_at_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("received_at must include a timezone, for example Z")
        return value


class PredictionResponse(BaseModel):
    event_id: str
    risk_score: float = Field(ge=0.0, le=1.0)
    model_version: str
    decision: Literal["allow", "verify", "hold_for_review"]
    reasons: list[str]


class EventIngestResponse(BaseModel):
    event_id: str
    status: Literal["processed", "duplicate_ignored", "late_for_review"]
    delay_seconds: float
    message: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    scorer_ready: bool
    model_version: str
    processor_ready: bool
    feature_store: str
