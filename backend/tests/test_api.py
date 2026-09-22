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
    assert body["route_plan"]["id"] > 0
    assert len(body["route_plan"]["routes"]) == 2


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


def test_imported_data_invalidates_old_plan_and_dashboard_returns_a_fresh_plan(tmp_path) -> None:
    client = client_for(tmp_path)
    first_plan_id = client.get("/dashboard").json()["route_plan"]["id"]

    imported = client.post("/imports/orders", json=[
        {"external_id": "new-order", "latitude": 43.24, "longitude": 76.95, "demand": 1, "priority": 2}
    ])
    dashboard = client.get("/dashboard").json()

    assert imported.json()["accepted_count"] == 1
    assert dashboard["summary"]["total_orders"] == 4
    assert dashboard["route_plan"]["id"] != first_plan_id
    assert dashboard["summary"]["assigned_orders"] == sum(
        len(route["stops"]) for route in dashboard["route_plan"]["routes"]
    )


def _plan_with_two_vehicles(client: TestClient) -> dict:
    client.post("/imports/orders", json=[
        {"external_id": "high", "latitude": 43.24, "longitude": 76.95, "demand": 2, "priority": 2},
        {"external_id": "low", "latitude": 43.25, "longitude": 76.96, "demand": 2, "priority": 1},
    ])
    client.post("/imports/vehicles", json=[
        {"external_id": "van-a", "latitude": 43.238, "longitude": 76.945, "capacity": 2, "status": "available"},
        {"external_id": "van-b", "latitude": 43.238, "longitude": 76.945, "capacity": 2, "status": "available"},
    ])
    response = client.post("/route-plans")
    assert response.status_code == 201
    return response.json()


def test_replan_excludes_vehicle_saves_new_plan_and_compares_with_unchanged_base(tmp_path) -> None:
    client = client_for(tmp_path)
    base = _plan_with_two_vehicles(client)

    response = client.post("/replans", json={
        "base_plan_id": base["id"], "unavailable_vehicle_ids": ["van-a"],
    })

    assert response.status_code == 201
    body = response.json()
    assert body["base_plan_id"] == base["id"]
    assert body["plan"]["id"] != base["id"]
    assert [route["vehicle_external_id"] for route in body["plan"]["routes"]] == ["van-b"]
    assert body["comparison"] == {
        "before": {"assigned_orders": 2, "unassigned_orders": 0, "distance_km": base["metrics"]["total_distance_km"], "duration_minutes": base["metrics"]["total_duration_minutes"]},
        "after": {"assigned_orders": 1, "unassigned_orders": 1, "distance_km": body["plan"]["metrics"]["total_distance_km"], "duration_minutes": body["plan"]["metrics"]["total_duration_minutes"]},
        "delta": {
            "assigned_orders": -1,
            "unassigned_orders": 1,
            "distance_km": body["plan"]["metrics"]["total_distance_km"] - base["metrics"]["total_distance_km"],
            "duration_minutes": body["plan"]["metrics"]["total_duration_minutes"] - base["metrics"]["total_duration_minutes"],
        },
    }
    assert client.get(f"/route-plans/{base['id']}").json() == base
    assert {vehicle["external_id"]: vehicle["status"] for vehicle in client.get("/dashboard").json()["vehicles"]} == {
        "van-a": "available", "van-b": "available",
    }

    repeated = client.post("/replans", json={
        "base_plan_id": base["id"], "unavailable_vehicle_ids": ["van-a"],
    }).json()
    assert repeated["plan"] | {"id": 0} == body["plan"] | {"id": 0}
    assert repeated["comparison"] == body["comparison"]


def test_replan_with_every_vehicle_excluded_marks_every_order_unassigned(tmp_path) -> None:
    client = client_for(tmp_path)
    base = _plan_with_two_vehicles(client)

    response = client.post("/replans", json={
        "base_plan_id": base["id"], "unavailable_vehicle_ids": ["van-a", "van-b"],
    })

    assert response.status_code == 201
    assert response.json()["plan"]["routes"] == []
    assert response.json()["plan"]["unassigned"] == [
        {"order_external_id": "high", "reason": "no_available_vehicle"},
        {"order_external_id": "low", "reason": "no_available_vehicle"},
    ]


def test_replan_rejects_unknown_vehicle_and_stale_base_plan(tmp_path) -> None:
    client = client_for(tmp_path)
    base = _plan_with_two_vehicles(client)

    unknown = client.post("/replans", json={"base_plan_id": base["id"], "unavailable_vehicle_ids": ["missing"]})
    assert unknown.status_code == 404
    assert unknown.json()["detail"] == "Unknown vehicle ID: missing"

    client.post("/imports/orders", json=[
        {"external_id": "new", "latitude": 43.26, "longitude": 76.97, "demand": 1, "priority": 1},
    ])
    stale = client.post("/replans", json={"base_plan_id": base["id"], "unavailable_vehicle_ids": []})
    assert stale.status_code == 409
    assert stale.json()["detail"] == "Base route plan is stale; calculate a new plan first"


def test_replan_validates_base_plan_and_duplicate_vehicle_ids(tmp_path) -> None:
    client = client_for(tmp_path)

    missing_plan = client.post("/replans", json={"base_plan_id": 999, "unavailable_vehicle_ids": []})
    assert missing_plan.status_code == 404
    assert missing_plan.json()["detail"] == "Base route plan not found"

    base = _plan_with_two_vehicles(client)
    invalid = client.post("/replans", json={
        "base_plan_id": base["id"], "unavailable_vehicle_ids": ["van-a", "van-a"],
    })
    assert invalid.status_code == 422

    no_change = client.post("/replans", json={
        "base_plan_id": base["id"], "unavailable_vehicle_ids": [],
    })
    assert no_change.status_code == 201
    assert no_change.json()["comparison"]["delta"] == {
        "assigned_orders": 0,
        "unassigned_orders": 0,
        "distance_km": 0,
        "duration_minutes": 0,
    }


def test_agent_interpret_returns_503_when_unconfigured(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    client = client_for(tmp_path)
    base = _plan_with_two_vehicles(client)

    response = client.post("/agent/interpret", json={
        "message": "van-a сломалась",
        "base_plan_id": base["id"],
    })
    assert response.status_code == 503
    assert response.json() == {"detail": "AI is not configured"}


def test_agent_interpret_validates_base_plan_existence_and_staleness(tmp_path) -> None:
    client = client_for(tmp_path)
    missing = client.post("/agent/interpret", json={"message": "любое сообщение", "base_plan_id": 404})
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Base plan was not found"

    base = _plan_with_two_vehicles(client)
    # Invalidate plan with new import
    client.post("/imports/orders", json=[
        {"external_id": "ord-extra", "latitude": 43.24, "longitude": 76.95, "demand": 1, "priority": 1}
    ])
    stale = client.post("/agent/interpret", json={"message": "любое", "base_plan_id": base["id"]})
    assert stale.status_code == 409


def test_agent_interpret_to_replan_flow(tmp_path) -> None:
    from app.agent.schemas import ModelInterpretation
    from app.agent.service import AgentInterpreter

    class StubProvider:
        def interpret(self, message, context):
            return ModelInterpretation(
                intent="exclude_vehicles",
                vehicle_ids=["van-a"],
                explanation="Предлагаю пересчитать план без van-a.",
                question=None,
            )

    client = client_for(tmp_path)
    # inject stub interpreter into app state
    client.app.state.agent_interpreter = AgentInterpreter(StubProvider())
    base = _plan_with_two_vehicles(client)

    # 1. Dispatcher sends natural language message to AI
    ai_resp = client.post("/agent/interpret", json={
        "message": "Машина van-a вышла из строя",
        "base_plan_id": base["id"],
    })
    assert ai_resp.status_code == 200
    ai_data = ai_resp.json()
    assert ai_data["status"] == "ready"
    assert ai_data["action"]["type"] == "exclude_vehicles"
    assert ai_data["action"]["vehicle_ids"] == ["van-a"]

    # 2. UI applies action and triggers replanning
    replan_resp = client.post("/replans", json={
        "base_plan_id": base["id"],
        "unavailable_vehicle_ids": ai_data["action"]["vehicle_ids"],
    })
    assert replan_resp.status_code == 201
    replan_data = replan_resp.json()
    assert [r["vehicle_external_id"] for r in replan_data["plan"]["routes"]] == ["van-b"]
    assert replan_data["comparison"]["after"]["assigned_orders"] == 1
    assert replan_data["comparison"]["after"]["unassigned_orders"] == 1


def test_completed_orders_are_ignored_during_route_planning(tmp_path) -> None:
    client = client_for(tmp_path)
    client.post("/imports/orders", json=[
        {"external_id": "active", "latitude": 43.24, "longitude": 76.95, "demand": 2, "priority": 1, "status": "pending"},
        {"external_id": "done", "latitude": 43.24, "longitude": 76.95, "demand": 2, "priority": 3, "status": "completed"},
    ])
    client.post("/imports/vehicles", json=[
        {"external_id": "van", "latitude": 43.238, "longitude": 76.945, "capacity": 5, "status": "available"},
    ])
    created = client.post("/route-plans")
    assert created.status_code == 201
    plan = created.json()
    stops = [s["order_external_id"] for r in plan["routes"] for s in r["stops"]]
    unassigned = [u["order_external_id"] for u in plan["unassigned"]]
    assert stops == ["active"]
    assert unassigned == []

