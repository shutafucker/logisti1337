from app.schemas import OrderPayload, VehiclePayload


def test_payload_schemas_supply_domain_status_defaults() -> None:
    order = OrderPayload.model_validate(
        {
            "external_id": "order-1",
            "latitude": 43.238,
            "longitude": 76.945,
            "demand": 3,
            "priority": 2,
        }
    )
    vehicle = VehiclePayload.model_validate(
        {
            "external_id": "vehicle-1",
            "latitude": 43.238,
            "longitude": 76.945,
            "capacity": 10,
        }
    )

    assert order.status == "pending"
    assert vehicle.status == "available"
