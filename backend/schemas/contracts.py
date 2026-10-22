
from typing import Any, Literal

from pydantic import BaseModel, Field, ConfigDict, field_validator


class AgentResponse(BaseModel):
    """Standard response returned by an individual agent."""

    status: Literal["success", "failed"]
    details: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

    model_config = ConfigDict(extra="ignore")


class RunRequest(BaseModel):
    """Request received by the automation API."""

    user_id: str
    request: str
    context: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")

    @field_validator("user_id", "request")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        """Reject empty or whitespace-only required fields."""

        if not value.strip():
            raise ValueError("This field cannot be empty.")

        return value.strip()


class RunResponse(BaseModel):
    """Standard response returned by the orchestrator."""

    status: Literal["success", "failed"]
    details: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

    model_config = ConfigDict(extra="ignore")
