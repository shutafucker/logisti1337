# LogistiAI MVP implementation plan

## Global constraints

- Work only on `nemain/shuta`; do not delete the existing `LICENSE`.
- Backend uses Python 3.14, FastAPI, Pydantic v2, SQLAlchemy 2, SQLite, and pytest.
- Frontend uses React, TypeScript, Vite, Leaflet, and React-Leaflet.
- The v1 workflow is: demo seed or CSV/JSON import -> SQLite -> deterministic route plan -> dispatcher dashboard.
- An order has `external_id`, `latitude`, `longitude`, `demand`, `priority`, and `status`. A vehicle has `external_id`, `latitude`, `longitude`, `capacity`, and `status`.
- Optimization assigns higher priority first without exceeding a vehicle capacity, then uses nearest-neighbor stop ordering. Unassigned orders must include a machine-readable reason. ETA uses haversine distance, configurable average speed, and configurable stop service duration.
- Do not add auth, live GPS, traffic APIs, road geometry, ML forecasting, multi-tenancy, or commercial map keys.

## Task 1: Backend domain, imports, and deterministic optimizer

Create `backend/` as an independently testable FastAPI project shell with domain dataclasses/Pydantic schemas and pure application services. Implement CSV and JSON payload parsing for orders and vehicles, returning accepted records plus row-level validation errors for missing fields, invalid coordinate ranges, invalid numerical values, and duplicate external IDs in an import batch.

Implement a pure routing engine with explicit `RoutingProvider`, `EtaProvider`, and `DemandForecastProvider` protocol interfaces, plus the v1 deterministic implementation. Assign available vehicles only; process orders by descending priority and deterministic ID tiebreak; reject an order with `no_available_vehicle` or `capacity_exceeded` as appropriate. For each vehicle, order its assigned stops with nearest-neighbor distance and compute cumulative stop ETA from haversine distance, average speed in km/h, and a per-stop service duration in minutes.

Write pytest tests first and capture RED/GREEN evidence in the task report. Cover import validation, duplicate IDs, priority/capacity assignment, no available vehicle, capacity overflow, nearest-neighbor order, and deterministic output.

Acceptance criteria:

- The routing engine has no HTTP, database, or framework dependencies.
- Import errors identify the input row and field/reason without discarding valid rows.
- Tests run with `pytest` from `backend/` and pass after implementation.

## Task 2: Persistence, seed data, and REST API

Build the SQLite persistence layer and FastAPI wiring on the Task 1 contracts. Create SQLAlchemy models/repositories for orders, vehicles, route plans, stops, and unassigned results. Add idempotent demo seed data featuring multiple Almaty-area orders, at least two available vehicles, and one capacity-constrained/unassigned case.

Expose exactly these public endpoints:

- `POST /imports/orders` and `POST /imports/vehicles`: accept JSON arrays and multipart CSV files; persist valid rows and return validation errors for rejected rows.
- `POST /route-plans`: create and persist a route plan from current orders and vehicles; accept optional `average_speed_kmh` and `service_minutes` overrides.
- `GET /route-plans/{id}`: return persisted routes, stops, ETA, metrics, and unassigned results; return 404 for an unknown ID.
- `GET /dashboard`: return the latest plan summary, current order/vehicle counts, route metrics, and unassigned items; seed the demo scenario automatically for an empty database.

Use FastAPI dependency injection for the database session and enable CORS for the Vite development origin. Add API integration tests for the full JSON import -> optimize -> retrieve flow, dashboard response, invalid CSV/JSON rows, and unknown route plan.

Acceptance criteria:

- SQLite database location is configurable through `LOGISTIAI_DATABASE_URL`, defaulting to a local file outside source packages.
- API response schemas are explicit Pydantic models and preserve route stop order.
- `pytest` from `backend/` passes with a temporary SQLite database.

## Task 3: Dispatcher dashboard

Create `frontend/` with React + TypeScript + Vite. Configure a development proxy or configurable API base URL for the FastAPI backend. Build a single responsive dispatcher dashboard with: header and scenario controls; KPI strip; CSV/JSON import controls for orders and vehicles; a button to calculate routes; Leaflet/OpenStreetMap map with vehicle/stop markers and straight route polylines; route cards; order/vehicle tables; and an unassigned-orders/risk panel.

Use the Task 2 endpoint contracts directly. On first load, request `/dashboard`; on calculation, call `POST /route-plans` then fetch its detailed plan. Show loading, empty, and actionable request/import error states. Keep Leaflet and API mapping in small focused components/helpers and avoid a state-management library.

Write frontend tests for rendering the dashboard states and API-driven route/error presentation. Verify the production Vite build.

Acceptance criteria:

- No map or API keys are committed; the map uses OpenStreetMap tiles.
- The page makes status and unassigned reasons visible without requiring the map.
- `npm test` and `npm run build` from `frontend/` pass after implementation.

## Task 4: Cross-stack verification and documentation

Add root-level run instructions covering backend setup, frontend setup, database configuration, demo flow, import field format, API endpoints, and known v1 limitations. Add a lightweight root command or documented sequence for running both services locally.

Run the full backend test suite, frontend tests, frontend production build, and a local API smoke flow. Resolve integration issues found by these checks. Do not add deployment, Docker, or CI unless needed to make the documented local workflow work.

Acceptance criteria:

- A new hackathon teammate can start the services, load demo data, calculate a plan, and use the dashboard from the README alone.
- Verification output and any intentional limitations are recorded in the final task report.
