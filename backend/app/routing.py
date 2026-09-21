"""Framework-free deterministic routing application service."""

from collections.abc import Sequence
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Protocol, runtime_checkable

from app.domain import Order, RoutePlan, RouteStop, UnassignedOrder, Vehicle, VehicleRoute


@runtime_checkable
class RoutingProvider(Protocol):
    def optimize(
        self,
        orders: Sequence[Order],
        vehicles: Sequence[Vehicle],
        *,
        average_speed_kmh: float = 40.0,
        service_minutes: float = 10.0,
    ) -> RoutePlan: ...


@runtime_checkable
class EtaProvider(Protocol):
    def travel_minutes(self, distance_km: float, average_speed_kmh: float) -> float: ...


@runtime_checkable
class DemandForecastProvider(Protocol):
    def demand_for(self, order: Order) -> float: ...


@dataclass(frozen=True, slots=True)
class HaversineEtaProvider:
    """ETA conversion for a known travel distance at a constant average speed."""

    def travel_minutes(self, distance_km: float, average_speed_kmh: float) -> float:
        if average_speed_kmh <= 0:
            raise ValueError("average_speed_kmh must be positive")
        return distance_km / average_speed_kmh * 60.0


@dataclass(frozen=True, slots=True)
class CurrentDemandForecastProvider:
    """v1 forecast: use each order's submitted demand without prediction."""

    def demand_for(self, order: Order) -> float:
        return order.demand


@dataclass(slots=True)
class DeterministicRoutingProvider:
    """v1 assignment and route ordering with stable tie-breaking by external ID."""

    eta_provider: EtaProvider = HaversineEtaProvider()
    demand_forecast_provider: DemandForecastProvider = CurrentDemandForecastProvider()

    def optimize(
        self,
        orders: Sequence[Order],
        vehicles: Sequence[Vehicle],
        *,
        average_speed_kmh: float = 40.0,
        service_minutes: float = 10.0,
    ) -> RoutePlan:
        if average_speed_kmh <= 0:
            raise ValueError("average_speed_kmh must be positive")
        if service_minutes < 0:
            raise ValueError("service_minutes must not be negative")

        available = sorted(
            (vehicle for vehicle in vehicles if vehicle.status.strip().lower() == "available"),
            key=lambda vehicle: vehicle.external_id,
        )
        assigned: dict[str, list[Order]] = {vehicle.external_id: [] for vehicle in available}
        remaining = {vehicle.external_id: vehicle.capacity for vehicle in available}
        unassigned: list[UnassignedOrder] = []

        for order in sorted(orders, key=lambda item: (-item.priority, item.external_id)):
            if not available:
                unassigned.append(UnassignedOrder(order, "no_available_vehicle"))
                continue
            demand = self.demand_forecast_provider.demand_for(order)
            matching = next(
                (vehicle for vehicle in available if remaining[vehicle.external_id] >= demand),
                None,
            )
            if matching is None:
                unassigned.append(UnassignedOrder(order, "capacity_exceeded"))
                continue
            assigned[matching.external_id].append(order)
            remaining[matching.external_id] -= demand

        routes = tuple(
            self._build_route(
                vehicle,
                assigned[vehicle.external_id],
                average_speed_kmh,
                service_minutes,
            )
            for vehicle in available
            if assigned[vehicle.external_id]
        )
        return RoutePlan(routes=routes, unassigned=tuple(unassigned))

    def _build_route(
        self,
        vehicle: Vehicle,
        orders: Sequence[Order],
        average_speed_kmh: float,
        service_minutes: float,
    ) -> VehicleRoute:
        unvisited = list(orders)
        current_latitude, current_longitude = vehicle.latitude, vehicle.longitude
        elapsed_minutes = 0.0
        stops: list[RouteStop] = []
        while unvisited:
            next_order = min(
                unvisited,
                key=lambda order: (
                    haversine_km(
                        current_latitude, current_longitude, order.latitude, order.longitude
                    ),
                    order.external_id,
                ),
            )
            distance_km = haversine_km(
                current_latitude, current_longitude, next_order.latitude, next_order.longitude
            )
            elapsed_minutes += self.eta_provider.travel_minutes(distance_km, average_speed_kmh)
            elapsed_minutes += service_minutes
            stops.append(
                RouteStop(
                    order=next_order,
                    sequence=len(stops) + 1,
                    distance_km=distance_km,
                    eta_minutes=elapsed_minutes,
                )
            )
            current_latitude, current_longitude = next_order.latitude, next_order.longitude
            unvisited.remove(next_order)
        return VehicleRoute(
            vehicle=vehicle,
            stops=tuple(stops),
            assigned_demand=sum(self.demand_forecast_provider.demand_for(order) for order in orders),
        )


def haversine_km(
    latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float
) -> float:
    """Return great-circle distance in kilometres between two latitude/longitude points."""
    earth_radius_km = 6371.0088
    delta_latitude = radians(latitude_b - latitude_a)
    delta_longitude = radians(longitude_b - longitude_a)
    a = (
        sin(delta_latitude / 2) ** 2
        + cos(radians(latitude_a))
        * cos(radians(latitude_b))
        * sin(delta_longitude / 2) ** 2
    )
    return 2 * earth_radius_km * asin(sqrt(a))
