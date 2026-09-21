from pathlib import Path

from app.imports import parse_orders_csv, parse_vehicles_csv

ROOT = Path(__file__).resolve().parents[2]


def test_demo_assets_are_valid_and_match_capacity_claims() -> None:
    orders = parse_orders_csv((ROOT / "demo/orders.csv").read_text())
    short_orders = parse_orders_csv((ROOT / "demo/orders-capacity-short.csv").read_text())
    vehicles = parse_vehicles_csv((ROOT / "demo/vehicles.csv").read_text())

    assert orders.errors == []
    assert vehicles.errors == []
    assert len(orders.accepted) == 12
    assert len(vehicles.accepted) == 4
    assert sum(order.demand for order in orders.accepted) == 17
    assert sum(order.demand for order in short_orders.accepted) == 25
    assert sum(vehicle.capacity for vehicle in vehicles.accepted if vehicle.external_id != "VAN-02") == 20


def test_invalid_demo_file_has_one_rejected_row_and_preserves_the_valid_row() -> None:
    result = parse_orders_csv((ROOT / "demo/orders-invalid.csv").read_text())

    assert [order.external_id for order in result.accepted] == ["AST-VALID"]
    assert [(error.row, error.field, error.reason) for error in result.errors] == [
        (3, "latitude", "out_of_range")
    ]
