"""Local schemas for the AI interpretation boundary."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AgentContext(BaseModel):
    """Minimal, trusted context supplied by the host application."""

    model_config = ConfigDict(frozen=True)

    base_plan_id: int = Field(gt=0)
    vehicle_ids: tuple[str, ...] = Field(min_length=1)


class ModelInterpretation(BaseModel):
    """Strict JSON response required from the model provider."""

    model_config = ConfigDict(extra="forbid")

    intent: Literal["exclude_vehicles", "needs_clarification", "unsupported"]
    vehicle_ids: list[str] = Field(max_length=8)
    explanation: str | None = Field(max_length=300)
    question: str | None = Field(max_length=300)

    @model_validator(mode="after")
    def has_fields_for_its_intent(self) -> "ModelInterpretation":
        if self.intent == "exclude_vehicles" and not self.vehicle_ids:
            raise ValueError("exclude_vehicles requires at least one vehicle ID")
        if self.intent == "needs_clarification" and not self.question:
            raise ValueError("needs_clarification requires a question")
        if self.intent == "unsupported" and not self.explanation:
            raise ValueError("unsupported requires an explanation")
        return self


class ExcludeVehiclesAction(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["exclude_vehicles"] = "exclude_vehicles"
    vehicle_ids: list[str] = Field(min_length=1, max_length=8)


class InterpretRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    base_plan_id: int = Field(gt=0)


class InterpretResponse(BaseModel):
    status: Literal["ready", "needs_clarification", "unsupported"]
    action: ExcludeVehiclesAction | None = None
    explanation: str | None = Field(default=None, max_length=300)
    question: str | None = Field(default=None, max_length=300)
