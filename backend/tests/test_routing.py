from math import isclose

from app.domain import Order, Vehicle
from app.routing import (
    CurrentDemandForecastProvider,
    DemandForecastProvider,
    DeterministicRoutingProvider,
    EtaProvider,
    HaversineEtaProvider,
    RoutingProvider,
)


def order(
    external_id: str, *, latitude: float = 43.238, longitude: float = 76.945,
    demand: float = 1, priority: int = 1,
) -> Order:
    return Order(external_id, latitude, longitude, demand, priority)


def vehicle(
    external_id: str, *, latitude: float = 43.238, longitude: float = 76.945,
    capacity: float = 10, status: str = "available",
) -> Vehicle:
    return Vehicle(external_id, latitude, longitude, capacity, status)


def test_assigns_descending_priority_before_lower_priority_when_capacity_is_limited() -> None:
    plan = DeterministicRoutingProvider().optimize(
        [
            order("low", demand=3, priority=1),
            order("high", demand=4, priority=3),
        ],
        [vehicle("van", capacity=5)],
    )

    assert [stop.order.external_id for stop in plan.routes[0].stops] == ["high"]
    assert [(item.order.external_id, item.reason) for item in plan.unassigned] == [
        ("low", "capacity_exceeded"),
    ]


def test_marks_orders_no_available_vehicle_when_every_vehicle_is_unavailable() -> None:
    plan = DeterministicRoutingProvider().optimize(
        [order("order-1")], [vehicle("van", status="maintenance")]
    )

    assert plan.routes == ()
    assert [(item.order.external_id, item.reason) for item in plan.unassigned] == [
        ("order-1", "no_available_vehicle"),
    ]


def test_marks_order_capacity_exceeded_when_available_vehicle_cannot_fit_it() -> None:
    plan = DeterministicRoutingProvider().optimize(
        [order("order-1", demand=3)], [vehicle("van", capacity=2)]
    )

    assert [(item.order.external_id, item.reason) for item in plan.unassigned] == [
        ("order-1", "capacity_exceeded"),
    ]


def test_orders_assigned_stops_by_nearest_neighbor_and_accumulates_eta() -> None:
    plan = DeterministicRoutingProvider().optimize(
        [
            order("far", latitude=0, longitude=1),
            order("near", latitude=0, longitude=0.1),
        ],
        [vehicle("van", latitude=0, longitude=0)],
        average_speed_kmh=60,
        service_minutes=5,
    )

    stops = plan.routes[0].stops
    assert [stop.order.external_id for stop in stops] == ["near", "far"]
    assert isclose(stops[0].eta_minutes, 16.1195, rel_tol=0.001)
    assert isclose(stops[1].eta_minutes, 121.195, rel_tol=0.001)


def test_produces_identical_output_for_permuted_input_orders_and_vehicles() -> None:
    orders = [
        order("b", latitude=43.24, priority=2),
        order("a", latitude=43.239, priority=2),
        order("c", latitude=43.241, priority=1),
    ]
    vehicles = [vehicle("van-b", capacity=2), vehicle("van-a", capacity=2)]
    router = DeterministicRoutingProvider()

    first = router.optimize(orders, vehicles)
    second = router.optimize(list(reversed(orders)), list(reversed(vehicles)))

    assert first == second


def test_v1_components_implement_explicit_routing_protocols() -> None:
    assert isinstance(DeterministicRoutingProvider(), RoutingProvider)
    assert isinstance(HaversineEtaProvider(), EtaProvider)
    assert isinstance(CurrentDemandForecastProvider(), DemandForecastProvider)
