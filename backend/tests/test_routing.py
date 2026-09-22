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


def test_non_routable_order_statuses_are_excluded_from_routing_and_unassigned() -> None:
    active_order = Order("active-1", 43.24, 76.95, demand=2, priority=2, status="pending")
    completed_order = Order("done-1", 43.24, 76.95, demand=2, priority=3, status="completed")
    cancelled_order = Order("cancel-1", 43.24, 76.95, demand=2, priority=3, status="cancelled")
    delivered_order = Order("delivered-1", 43.24, 76.95, demand=2, priority=3, status="delivered")

    plan = DeterministicRoutingProvider().optimize(
        [active_order, completed_order, cancelled_order, delivered_order],
        [vehicle("van", capacity=10)],
    )

    assigned_ids = [stop.order.external_id for r in plan.routes for stop in r.stops]
    unassigned_ids = [item.order.external_id for item in plan.unassigned]

    assert assigned_ids == ["active-1"]
    assert unassigned_ids == []


def test_capacity_is_strictly_respected_across_vehicles() -> None:
    orders = [
        order("ord-1", demand=3, priority=2),
        order("ord-2", demand=3, priority=2),
        order("ord-3", demand=3, priority=1),
    ]
    vehicles = [vehicle("van-1", capacity=5), vehicle("van-2", capacity=2)]
    plan = DeterministicRoutingProvider().optimize(orders, vehicles)

    for route in plan.routes:
        assert route.assigned_demand <= route.vehicle.capacity

    assert len(plan.routes) == 1
    assert [stop.order.external_id for stop in plan.routes[0].stops] == ["ord-1"]
    assert [(item.order.external_id, item.reason) for item in plan.unassigned] == [
        ("ord-2", "capacity_exceeded"),
        ("ord-3", "capacity_exceeded"),
    ]


def test_each_routable_order_appears_exactly_once() -> None:
    orders = [order(f"ord-{i}", demand=2, priority=i) for i in range(10)]
    vehicles = [vehicle("v-1", capacity=6), vehicle("v-2", capacity=4)]
    plan = DeterministicRoutingProvider().optimize(orders, vehicles)

    assigned_ids = [stop.order.external_id for route in plan.routes for stop in route.stops]
    unassigned_ids = [item.order.external_id for item in plan.unassigned]
    all_processed = assigned_ids + unassigned_ids

    assert len(all_processed) == len(set(all_processed)) == len(orders)
    assert set(all_processed) == {o.external_id for o in orders}


def test_haversine_km_handles_antipodal_extremes_without_domain_error() -> None:
    from app.routing import haversine_km
    distance = haversine_km(-90.0, 0.0, 90.0, 0.0)
    assert distance > 20000

