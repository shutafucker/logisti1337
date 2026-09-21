from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Order:
    external_id: str
    latitude: float
    longitude: float
    demand: float
    priority: int
    status: str = "pending"


@dataclass(frozen=True, slots=True)
class Vehicle:
    external_id: str
    latitude: float
    longitude: float
    capacity: float
    status: str = "available"


@dataclass(frozen=True, slots=True)
class RouteStop:
    order: Order
    sequence: int
    distance_km: float
    eta_minutes: float


@dataclass(frozen=True, slots=True)
class VehicleRoute:
    vehicle: Vehicle
    stops: tuple[RouteStop, ...]
    assigned_demand: float


@dataclass(frozen=True, slots=True)
class UnassignedOrder:
    order: Order
    reason: str


@dataclass(frozen=True, slots=True)
class RoutePlan:
    routes: tuple[VehicleRoute, ...]
    unassigned: tuple[UnassignedOrder, ...]
