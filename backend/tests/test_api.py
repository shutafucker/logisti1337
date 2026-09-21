from fastapi.testclient import TestClient

from app.main import create_app


def client_for(tmp_path) -> TestClient:
    return TestClient(create_app(database_url=f"sqlite:///{tmp_path / 'logistiai.db'}"))


def test_import_optimize_and_retrieve_plan(tmp_path) -> None:
    client = client_for(tmp_path)
    orders = [
        {"external_id": "urgent", "latitude": 43.24, "longitude": 76.95, "demand": 4, "priority": 3},
        {"external_id": "later", "latitude": 43.25, "longitude": 76.96, "demand": 3, "priority": 1},
    ]
    vehicles = [
        {"external_id": "van", "latitude": 43.238, "longitude": 76.945, "capacity": 5, "status": "available"},
    ]

    assert client.post("/imports/orders", json=orders).json()["accepted_count"] == 2
    assert client.post("/imports/vehicles", json=vehicles).json()["accepted_count"] == 1

    created = client.post("/route-plans", json={"average_speed_kmh": 40, "service_minutes": 5})
    assert created.status_code == 201
    plan = client.get(f"/route-plans/{created.json()['id']}")

    assert plan.status_code == 200
    assert [stop["order_external_id"] for stop in plan.json()["routes"][0]["stops"]] == ["urgent"]
    assert plan.json()["unassigned"] == [{"order_external_id": "later", "reason": "capacity_exceeded"}]


def test_dashboard_seeds_demo_scenario_and_exposes_unassigned_items(tmp_path) -> None:
    response = client_for(tmp_path).get("/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_orders"] == 3
    assert body["summary"]["active_vehicles"] == 2
    assert body["summary"]["unassigned_orders"] == 1
    assert body["unassigned"][0]["reason"] == "capacity_exceeded"


def test_import_returns_row_level_errors_without_discarding_valid_csv_rows(tmp_path) -> None:
    response = client_for(tmp_path).post(
        "/imports/orders",
        files={"file": ("orders.csv", "external_id,latitude,longitude,demand,priority\ngood,43.2,76.9,2,1\nbad,91,76.9,2,1\n", "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["accepted_count"] == 1
    assert response.json()["errors"] == [{"row": 3, "field": "latitude", "reason": "out_of_range"}]


def test_unknown_route_plan_returns_not_found(tmp_path) -> None:
    response = client_for(tmp_path).get("/route-plans/404")

    assert response.status_code == 404
    assert response.json()["detail"] == "Route plan not found"


def test_route_plan_uses_default_settings_when_frontend_posts_no_body(tmp_path) -> None:
    client = client_for(tmp_path)
    client.get("/dashboard")

    response = client.post("/route-plans")

    assert response.status_code == 201
    assert response.json()["metrics"]["total_duration_minutes"] > 0
