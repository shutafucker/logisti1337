import pytest

from app.agent.provider import (
    OpenAIResponsesProvider,
    ProviderInvalidResponse,
    ProviderNotConfigured,
    ProviderSettings,
)
from app.agent.schemas import AgentContext


def test_provider_requires_key_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)

    with pytest.raises(ProviderNotConfigured, match="AI_API_KEY"):
        ProviderSettings.from_environment()


def test_provider_requests_strict_schema_with_only_safe_action_context() -> None:
    provider = OpenAIResponsesProvider(ProviderSettings("test-key", "test-model", 5))

    payload = provider._payload("VAN-02 сломалась", AgentContext(base_plan_id=2, vehicle_ids=("VAN-01", "VAN-02")))

    assert payload["model"] == "test-model"
    assert payload["store"] is False
    assert payload["text"]["format"]["strict"] is True
    assert payload["text"]["format"]["schema"]["required"] == ["intent", "vehicle_ids", "explanation", "question"]
    assert "Allowed action: exclude_vehicles" in payload["input"]
    assert "VAN-01, VAN-02" in payload["input"]
    assert "test-key" not in str(payload)


@pytest.mark.parametrize("body", [b"not-json", b'{"output_text":"{\\\"intent\\\":\\\"exclude_vehicles\\\"}"}'])
def test_provider_rejects_invalid_model_response(monkeypatch: pytest.MonkeyPatch, body: bytes) -> None:
    provider = OpenAIResponsesProvider(ProviderSettings("test-key", "test-model", 5))
    monkeypatch.setattr(OpenAIResponsesProvider, "_request_with_one_retry", lambda self, request: body)

    with pytest.raises(ProviderInvalidResponse):
        provider.interpret("VAN-02 сломалась", AgentContext(base_plan_id=2, vehicle_ids=("VAN-02",)))
