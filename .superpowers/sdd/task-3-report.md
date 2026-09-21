# Task 3: Dispatcher dashboard report

## Implementation

Created a standalone Vite + React + TypeScript dispatcher dashboard in `frontend/`.

- Uses `VITE_API_BASE_URL` when supplied; otherwise calls `/api`, which Vite proxies to `http://127.0.0.1:8000` and removes the `/api` prefix.
- Fetches `/dashboard` on first load. Route calculation posts to `/route-plans`, then gets `/route-plans/{id}` and presents route cards, map lines/stops, revised metrics, and unassigned orders.
- Upload controls send CSV/JSON files as multipart form data to `/imports/orders` and `/imports/vehicles`.
- Clearly presents loading, empty, import/request error, retry, status, route, and capacity-risk states without depending on the map.
- `MapPanel` is isolated from API/state concerns and uses only OpenStreetMap tiles; no map or API keys are present.

## Tests and verification

### RED evidence

After adding tests before production components, ran from `frontend/`:

```text
npm test -- --reporter=verbose
FAIL src/components/Dashboard.test.tsx
Error: Failed to resolve import "./Dashboard"
FAIL src/components/MapPanel.test.tsx
Error: Failed to resolve import "./MapPanel"
```

This was the expected failure because the user-facing dashboard and map implementations did not yet exist.

### GREEN evidence

After minimal implementation, ran:

```text
npm test -- --reporter=verbose
Test Files  2 passed (2)
Tests  6 passed (6)
```

Tests cover loading, API-rendered dashboard metrics/status/unassigned reason, plan creation/detail presentation, dashboard request retry error, import validation error, and OpenStreetMap vehicle/stop/route rendering.

Production build initially identified two typed configuration gaps (`ImportMeta.env` declaration and Vitest's `test` config typing). After tracing each failure and applying the targeted configuration change, fresh verification was:

```text
npm run build
✓ built in 1.26s

npm test -- --reporter=verbose
Test Files  2 passed (2)
Tests  6 passed (6)
```

## Files

- `frontend/package.json`, `package-lock.json`, TypeScript/Vite configuration, and `.gitignore`
- `frontend/src/api/client.ts` and `frontend/src/api/types.ts`
- `frontend/src/components/Dashboard.tsx` and `MapPanel.tsx`
- `frontend/src/components/Dashboard.test.tsx` and `MapPanel.test.tsx`
- `frontend/src/main.tsx`, `styles.css`, and test setup

## Self-review

- Reviewed that all HTTP calls use the configurable base URL and route only through the documented endpoint paths.
- Confirmed file uploads do not manually set multipart headers, allowing the browser to provide the boundary.
- Confirmed status and machine-readable unassigned reason are visible in the tables/risk panel, including when no map interactions occur.
- Confirmed map provider URL is OpenStreetMap and no key-like configuration is added.

## Concerns

- This task was implemented against the supplied Task 2 public contracts while the Task 2 source was not yet present in the shared checkout. The API client expects the documented `id`, `summary`, `orders`, `vehicles`, `metrics`, `unassigned`, and route/stop fields; an integration smoke test should be run once that backend task lands.
- Vite reports two moderate transitive dependency audit findings during install. No automatic audit upgrade was made because it could change the locked toolchain outside this task's scope.
