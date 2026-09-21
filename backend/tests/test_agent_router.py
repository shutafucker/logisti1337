from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent.provider import ProviderNotConfigured
from app.agent.router import router
from app.agent.schemas import AgentContext, ModelInterpretation
from app.agent.service import AgentInterpreter


class StubProvider:
    def __init__(self, result: ModelInterpretation | Exception) -> None:
        self.result = result

    def interpret(self, message: str, context: AgentContext) -> ModelInterpretation:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def configured_client(result: ModelInterpretation | Exception) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.state.agent_interpreter = AgentInterpreter(StubProvider(result))
    app.state.agent_context_provider = lambda plan_id: AgentContext(
        base_plan_id=plan_id, vehicle_ids=("VAN-01", "VAN-02")
    )
    return TestClient(app)


def test_interpret_endpoint_returns_validated_action_without_persisting_it() -> None:
    client = configured_client(ModelInterpretation(
        intent="exclude_vehicles", vehicle_ids=["VAN-02"],
        explanation="Предлагаю пересчитать план без VAN-02.", question=None,
    ))

    response = client.post("/agent/interpret", json={"message": "VAN-02 сломалась", "base_plan_id": 4})

    assert response.status_code == 200
    assert response.json()["action"] == {"type": "exclude_vehicles", "vehicle_ids": ["VAN-02"]}


def test_interpret_endpoint_returns_safe_error_when_provider_is_not_configured() -> None:
    client = configured_client(ProviderNotConfigured("AI_API_KEY is not configured"))

    response = client.post("/agent/interpret", json={"message": "VAN-02 сломалась", "base_plan_id": 4})

    assert response.status_code == 503
    assert response.json() == {"detail": "AI is not configured"}


def test_interpret_endpoint_requires_host_application_context_integration() -> None:
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).post("/agent/interpret", json={"message": "VAN-02 сломалась", "base_plan_id": 4})

    assert response.status_code == 503
    assert response.json() == {"detail": "AI interpreter is not configured"}
