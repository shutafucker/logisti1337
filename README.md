# LogistiAI

Диспетчерский MVP для хакатона по логистике: импортируйте заказы и машины,
постройте объяснимый план доставки и сразу увидите ETA, загрузку автопарка и
заказы, которые не удалось назначить.

## Быстрый запуск

Нужны Python 3.14+ и Node.js 20+.

Необязательно: скопируйте `.env.example` в `.env`, если нужно изменить
расположение базы или адрес API. `.env` не коммитится. Backend автоматически
читает этот файл, а Vite передаёт во фронтенд только переменные с префиксом
`VITE_` — не храните в них секреты.

В первом терминале запустите API:

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Во втором — диспетчерский интерфейс:

```bash
cd frontend
npm install
npm run dev
```

Откройте адрес, который выведет Vite (обычно `http://localhost:5173`). При
первом открытии `/dashboard` автоматически создаёт демонстрационный сценарий
Алматы. Нажмите **Calculate routes**, чтобы пересчитать и сохранить план.

Vite проксирует запросы `/api/*` на `http://127.0.0.1:8000/*`. Для другого
адреса API задайте `VITE_API_BASE_URL`, например:

```bash
cp .env.example .env
# затем раскомментируйте VITE_API_BASE_URL в .env
npm run dev
```

SQLite по умолчанию хранится в `backend/data/logistiai.db` и не попадает в Git.
Для другого расположения установите `LOGISTIAI_DATABASE_URL`, например
`sqlite:////tmp/logistiai.db` в `.env` перед запуском API.

### Windows PowerShell

```powershell
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
cd ..\frontend
npm install
cd ..
.\scripts\start-dev.ps1
```

Скрипт проверяет окружение и занятость портов, запускает backend/frontend в
отдельных процессах и печатает их PID. Он не завершает чужие процессы и не
удаляет БД. Ошибки находятся в окнах этих процессов; остановить свои процессы
можно командой `Stop-Process -Id <backend PID>,<frontend PID>`.

## Импорт данных

В dashboard можно выбрать CSV или JSON-файл. Валидные строки сохраняются даже
если в соседних строках есть ошибки; ответ API возвращает номер строки, поле и
причину ошибки.

Заказы — JSON-массив либо CSV с заголовком:

```csv
external_id,latitude,longitude,demand,priority,status
ALM-201,43.2384,76.9457,3,3,pending
ALM-202,43.2550,76.9200,2,1,pending
```

Машины — JSON-массив либо CSV с заголовком:

```csv
external_id,latitude,longitude,capacity,status
VAN-03,43.2380,76.9450,8,available
```

`external_id`, координаты, `demand`/`capacity` и приоритет обязательны для
заказа; `status` заказа по умолчанию `pending`, статус машины — `available`.
Допустимая машина не превышает вместимость. Заказы обрабатываются от высокого
приоритета к низкому, а точки каждой машины упорядочиваются ближайшим соседом.

## API

- `POST /imports/orders` — JSON-массив или `multipart/form-data` с полем `file`.
- `POST /imports/vehicles` — JSON-массив или `multipart/form-data` с полем `file`.
- `POST /route-plans` — создаёт план; необязательное JSON-тело:
  `{"average_speed_kmh": 40, "service_minutes": 10}`.
- `GET /route-plans/{id}` — сохранённые маршруты, остановки, ETA, метрики и
  нераспределённые заказы.
- `GET /dashboard` — данные для dashboard и последний рассчитанный план.

### AI-интерпретация (подключается backend-владельцем)

AI-модуль готов в `backend/app/agent/`, но основной `create_app` его намеренно
не подключает: согласно распределению ролей это делает владелец backend по
[инструкции интеграции](docs/demo/integration-handoff.md). После подключения
доступен `POST /agent/interpret`:

```json
{"message":"VAN-02 сломалась","base_plan_id":1}
```

Ответ имеет один из статусов `ready`, `needs_clarification`, `unsupported`.
Только `ready` возвращает действие `exclude_vehicles`; AI не рассчитывает ETA,
не выполняет команд и не меняет план. UI должен затем отдельно вызвать
`/replans` по общему контракту.

Задайте только в backend-процессе (или в неотслеживаемом `.env`) следующие
настройки:

```text
AI_API_KEY=
AI_MODEL=
AI_TIMEOUT_SECONDS=15
```

`.env` подхватывается текущим backend через `python-dotenv`; переменные процесса
имеют приоритет. Не используйте `VITE_` для ключа. Для проверки настоящего
вызова без раскрытия секрета в PowerShell сначала запустите API, затем
используйте `./scripts/check-ai.ps1`: скрипт получает текущие `plan_id` и IDs
машин из маршрутов этого плана через `/dashboard`, загружает root `.env` и печатает лишь валидированный
результат. Зафиксируйте модель и дату в `docs/demo/results.md`.

ETA — оценка в минутах от старта маршрута: haversine-расстояние, средняя
скорость и время обслуживания на каждой точке. Линии на карте — прямые между
рассчитанными остановками, а не дорожная геометрия.

## Проверки

```bash
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm test && npm run build
```

## Границы MVP

В первой версии нет авторизации, live GPS, дорожного трафика, коммерческих
карт, ML-прогноза спроса и multi-tenant режима. В backend уже предусмотрены
расширяемые контракты `RoutingProvider`, `EtaProvider` и
`DemandForecastProvider`, поэтому более точный solver, внешний routing API или
прогноз можно подключать без переноса HTTP/UI-слоя.

## Материалы демо

- [Критерии и наборы данных](docs/demo/acceptance.md)
- [Сценарий выступления](docs/demo/demo-script.md)
- [Факты и результаты](docs/demo/results.md)
