"""HTTP adapter; the host app provides trusted plan context at integration time."""

from collections.abc import Callable

from fastapi import APIRouter, HTTPException, Request

from app.agent.provider import (
    ProviderError,
    ProviderInvalidResponse,
    ProviderNotConfigured,
    ProviderTimeout,
)
from app.agent.schemas import AgentContext, InterpretRequest, InterpretResponse
from app.agent.service import AgentInterpreter

router = APIRouter(prefix="/agent", tags=["agent"])

AgentContextProvider = Callable[[int], AgentContext]


@router.post("/interpret", response_model=InterpretResponse)
def interpret_request(payload: InterpretRequest, request: Request) -> InterpretResponse:
    """Interpret only; it never saves data or invokes replanning."""
    interpreter = getattr(request.app.state, "agent_interpreter", None)
    context_provider = getattr(request.app.state, "agent_context_provider", None)
    if not isinstance(interpreter, AgentInterpreter) or not callable(context_provider):
        raise HTTPException(status_code=503, detail="AI interpreter is not configured")
    try:
        context = context_provider(payload.base_plan_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail="Base plan was not found") from error
    if context.base_plan_id != payload.base_plan_id:
        raise HTTPException(status_code=409, detail="Base plan context is stale")
    try:
        return interpreter.interpret(payload.message, context)
    except ProviderNotConfigured as error:
        raise HTTPException(status_code=503, detail="AI is not configured") from error
    except ProviderTimeout as error:
        raise HTTPException(status_code=503, detail="AI request timed out; use manual vehicle exclusion") from error
    except (ProviderInvalidResponse, ProviderError) as error:
        raise HTTPException(status_code=503, detail="AI is unavailable; use manual vehicle exclusion") from error
