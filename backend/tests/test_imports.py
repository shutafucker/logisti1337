from app.imports import (
    parse_orders_csv,
    parse_orders_json,
    parse_vehicles_csv,
    parse_vehicles_json,
)


def test_json_import_keeps_valid_orders_and_reports_invalid_rows() -> None:
    result = parse_orders_json(
        [
            {
                "external_id": "order-1",
                "latitude": 43.238,
                "longitude": 76.945,
                "demand": 3,
                "priority": 2,
            },
            {
                "external_id": "order-2",
                "latitude": 91,
                "longitude": 76.945,
                "demand": "not-a-number",
                "priority": 1,
            },
        ]
    )

    assert [order.external_id for order in result.accepted] == ["order-1"]
    assert [(error.row, error.field) for error in result.errors] == [
        (2, "latitude"),
        (2, "demand"),
    ]


def test_json_import_rejects_duplicate_external_id_without_discarding_first_row() -> None:
    result = parse_orders_json(
        [
            {
                "external_id": "order-1",
                "latitude": 43.238,
                "longitude": 76.945,
                "demand": 3,
                "priority": 2,
            },
            {
                "external_id": "order-1",
                "latitude": 43.24,
                "longitude": 76.95,
                "demand": 2,
                "priority": 1,
            },
        ]
    )

    assert [order.external_id for order in result.accepted] == ["order-1"]
    assert [(error.row, error.field, error.reason) for error in result.errors] == [
        (2, "external_id", "duplicate_external_id"),
    ]


def test_csv_import_uses_source_line_numbers_and_keeps_valid_rows() -> None:
    result = parse_orders_csv(
        "external_id,latitude,longitude,demand,priority\n"
        "order-1,43.238,76.945,3,2\n"
        ",43.240,76.950,2,1\n"
    )

    assert [order.external_id for order in result.accepted] == ["order-1"]
    assert [(error.row, error.field, error.reason) for error in result.errors] == [
        (3, "external_id", "required"),
    ]


def test_vehicle_import_validates_capacity_and_duplicate_ids() -> None:
    result = parse_vehicles_json(
        [
            {
                "external_id": "vehicle-1",
                "latitude": 43.238,
                "longitude": 76.945,
                "capacity": 10,
                "status": "available",
            },
            {
                "external_id": "vehicle-1",
                "latitude": 43.240,
                "longitude": 76.950,
                "capacity": 0,
            },
        ]
    )

    assert [vehicle.external_id for vehicle in result.accepted] == ["vehicle-1"]
    assert [(error.row, error.field, error.reason) for error in result.errors] == [
        (2, "capacity", "must_be_positive"),
        (2, "external_id", "duplicate_external_id"),
    ]


def test_vehicle_csv_import_accepts_available_vehicle() -> None:
    result = parse_vehicles_csv(
        "external_id,latitude,longitude,capacity,status\n"
        "vehicle-1,43.238,76.945,10,available\n"
    )

    assert result.errors == []
    assert result.accepted[0].external_id == "vehicle-1"
    assert result.accepted[0].status == "available"


def test_order_import_preserves_optional_status() -> None:
    result = parse_orders_json(
        [
            {
                "external_id": "order-1",
                "latitude": 43.238,
                "longitude": 76.945,
                "demand": 3,
                "priority": 2,
                "status": "assigned",
            }
        ]
    )

    assert result.accepted[0].status == "assigned"
