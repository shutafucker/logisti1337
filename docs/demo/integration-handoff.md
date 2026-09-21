# Передача AI-модуля Максиму и Константину

## Максиму: backend-интеграция

Нетесов добавил `app.agent.router.router`, но намеренно не менял
`app.main.create_app`. Для подключения в `create_app`:

```python
from app.agent.provider import EnvironmentOpenAIProvider
from app.agent.router import router
from app.agent.service import AgentInterpreter

app.include_router(router)
app.state.agent_interpreter = AgentInterpreter(EnvironmentOpenAIProvider())
app.state.agent_context_provider = get_agent_context
```

`get_agent_context(base_plan_id)` должен получить неизменённый исходный план и
вернуть `AgentContext(base_plan_id=base_plan_id, vehicle_ids=(...))`, где IDs
берутся из фактических маршрутов/машин этого плана. При неизвестном плане он
должен бросать `LookupError`; при несовместимом контексте router вернёт 409.
Это модуль без собственной БД: интерпретация не сохраняет действие и не
вызывает `/replans`.

Новые runtime-настройки уже согласованы общим планом: `AI_API_KEY`, `AI_MODEL`,
`AI_TIMEOUT_SECONDS`. Настройки разрешаются только при запросе `/agent/interpret`:
при отсутствующем ключе, модели или неверном timeout backend продолжает работу,
а router возвращает безопасный 503. Дополнительная Python-зависимость не нужна:
provider использует стандартный HTTPS-клиент для OpenAI Responses API с
`json_schema`.

## Константину: состояния UI

`POST /agent/interpret`:

```json
{"message":"VAN-02 сломалась","base_plan_id":1}
```

- `ready`: показать `action` и кнопку «Применить и пересчитать»; только эта
  кнопка вызывает `/replans`.
- `needs_clarification`: показать `question`, не вызывать `/replans`.
- `unsupported`: показать `explanation`, не вызывать `/replans`.
- `503`: показать безопасное сообщение об AI и оставить ручное исключение
  машины доступным.

Не отображать полный внутренний ответ модели и не отправлять API-ключ во
frontend.
