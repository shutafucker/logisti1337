"""Pydantic transport schemas for the public HTTP API."""

from pydantic import BaseModel, ConfigDict, Field


class OrderPayload(BaseModel):
    external_id: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    demand: float = Field(gt=0)
    priority: int
    status: str = "pending"


class VehiclePayload(BaseModel):
    external_id: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    capacity: float = Field(gt=0)
    status: str = "available"


class ImportErrorResponse(BaseModel):
    row: int
    field: str
    reason: str


class ImportResponse(BaseModel):
    accepted_count: int
    errors: list[ImportErrorResponse]


class OptimizeRequest(BaseModel):
    average_speed_kmh: float = Field(default=40, gt=0)
    service_minutes: float = Field(default=10, ge=0)


class RouteStopResponse(BaseModel):
    order_external_id: str
    latitude: float
    longitude: float
    sequence: int
    distance_km: float
    eta_minutes: float


class RouteResponse(BaseModel):
    vehicle_external_id: str
    assigned_demand: float
    distance_km: float
    duration_minutes: float
    stops: list[RouteStopResponse]


class MetricsResponse(BaseModel):
    total_distance_km: float
    total_duration_minutes: float


class UnassignedResponse(BaseModel):
    order_external_id: str
    reason: str


class RoutePlanResponse(BaseModel):
    id: int
    routes: list[RouteResponse]
    metrics: MetricsResponse
    unassigned: list[UnassignedResponse]


class ReplanRequest(BaseModel):
    base_plan_id: int = Field(gt=0)
    unavailable_vehicle_ids: list[str] = Field(min_length=1)


class PlanSnapshot(BaseModel):
    assigned_orders: int
    unassigned_orders: int
    distance_km: float
    duration_minutes: float


class ReplanComparison(BaseModel):
    before: PlanSnapshot
    after: PlanSnapshot
    delta: PlanSnapshot


class ReplanResponse(BaseModel):
    base_plan_id: int
    plan: RoutePlanResponse
    comparison: ReplanComparison
    unavailable_vehicle_ids: list[str]


class DashboardSummary(BaseModel):
    total_orders: int
    assigned_orders: int
    unassigned_orders: int
    active_vehicles: int


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    orders: list[OrderPayload]
    vehicles: list[VehiclePayload]
    metrics: MetricsResponse
    unassigned: list[UnassignedResponse]
    route_plan: RoutePlanResponse
