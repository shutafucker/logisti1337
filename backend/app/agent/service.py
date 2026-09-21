"""Application service that validates model output against trusted context."""

from dataclasses import dataclass

from app.agent.provider import AgentProvider
from app.agent.schemas import (
    AgentContext,
    ExcludeVehiclesAction,
    InterpretResponse,
    ModelInterpretation,
)


@dataclass(slots=True)
class AgentInterpreter:
    provider: AgentProvider

    def interpret(self, message: str, context: AgentContext) -> InterpretResponse:
        result = self.provider.interpret(message, context)
        return self._validate(result, context)

    @staticmethod
    def _validate(result: ModelInterpretation, context: AgentContext) -> InterpretResponse:
        if result.intent == "needs_clarification":
            return InterpretResponse(
                status="needs_clarification", question=result.question,
                explanation=result.explanation,
            )
        if result.intent == "unsupported":
            return InterpretResponse(status="unsupported", explanation=result.explanation)

        requested_ids = list(dict.fromkeys(result.vehicle_ids))
        unknown_ids = sorted(set(requested_ids).difference(context.vehicle_ids))
        if unknown_ids:
            return InterpretResponse(
                status="needs_clarification",
                question="Укажите ID машины из списка: " + ", ".join(context.vehicle_ids),
                explanation="Указанная машина отсутствует в текущем плане.",
            )
        return InterpretResponse(
            status="ready",
            action=ExcludeVehiclesAction(vehicle_ids=requested_ids),
            explanation=result.explanation or "Предлагаю пересчитать план без выбранных машин.",
        )
