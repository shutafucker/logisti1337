from fastapi.testclient import TestClient

from app.main import create_app


def client_for(tmp_path) -> TestClient:
    return TestClient(create_app(database_url=f"sqlite:///{tmp_path / 'replans.db'}"))


def seed(client: TestClient) -> int:
    client.post("/imports/orders", json=[
        {"external_id": "ORD-1", "latitude": 51.1, "longitude": 71.4, "demand": 3, "priority": 2},
        {"external_id": "ORD-2", "latitude": 51.2, "longitude": 71.5, "demand": 3, "priority": 1},
    ])
    client.post("/imports/vehicles", json=[
        {"external_id": "VAN-1", "latitude": 51.1, "longitude": 71.4, "capacity": 3, "status": "available"},
        {"external_id": "VAN-2", "latitude": 51.2, "longitude": 71.5, "capacity": 3, "status": "available"},
    ])
    return client.post("/route-plans").json()["id"]


def test_replan_excludes_vehicle_and_returns_a_comparison_without_changing_fleet(tmp_path) -> None:
    client = client_for(tmp_path)
    base_id = seed(client)

    response = client.post("/replans", json={"base_plan_id": base_id, "unavailable_vehicle_ids": ["VAN-1"]})

    assert response.status_code == 201
    body = response.json()
    assert body["base_plan_id"] == base_id
    assert body["plan"]["id"] != base_id
    assert {route["vehicle_external_id"] for route in body["plan"]["routes"]} == {"VAN-2"}
    assert body["comparison"]["before"]["assigned_orders"] == 2
    assert body["comparison"]["after"]["assigned_orders"] == 1
    assert body["comparison"]["delta"]["assigned_orders"] == -1
    assert client.get("/dashboard").json()["vehicles"][0]["status"] == "available"
    assert client.get(f"/route-plans/{base_id}").status_code == 200


def test_replan_rejects_unknown_and_stale_base_plans(tmp_path) -> None:
    client = client_for(tmp_path)
    base_id = seed(client)

    unknown = client.post("/replans", json={"base_plan_id": base_id, "unavailable_vehicle_ids": ["NOPE"]})
    assert unknown.status_code == 404
    assert unknown.json()["detail"] == "Unknown vehicle IDs: NOPE"

    created = client.post("/route-plans").json()["id"]
    stale = client.post("/replans", json={"base_plan_id": base_id, "unavailable_vehicle_ids": ["VAN-1"]})
    assert created != base_id
    assert stale.status_code == 409


def test_replan_validates_request_shape(tmp_path) -> None:
    client = client_for(tmp_path)
    response = client.post("/replans", json={"base_plan_id": 0, "unavailable_vehicle_ids": []})
    assert response.status_code == 422
