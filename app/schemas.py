
from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    status: Literal["success", "failed"]
    details: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class RunRequest(BaseModel):
    user_id: str
    request: str


class RunResponse(BaseModel):
    status: Literal["success", "failed"]
    details: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
