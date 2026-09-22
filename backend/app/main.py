"""FastAPI application and its thin HTTP adapters."""

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, sessionmaker

from app.database import create_session_factory
from app.domain import Order, Vehicle
from app.imports import (
    ImportErrorDetail,
    parse_orders_csv,
    parse_orders_json,
    parse_vehicles_csv,
    parse_vehicles_json,
)
from app.models import RoutePlanRecord
from app.repository import (
    get_plan,
    has_imported_data,
    invalidate_plans,
    latest_plan,
    list_orders,
    list_vehicles,
    save_plan,
    upsert_orders,
    upsert_vehicles,
)
from app.routing import DeterministicRoutingProvider
from app.schemas import (
    DashboardResponse,
    DashboardSummary,
    ImportResponse,
    MetricsResponse,
    OptimizeRequest,
    PlanSnapshot,
    ReplanComparison,
    ReplanRequest,
    ReplanResponse,
    RoutePlanResponse,
    RouteResponse,
    RouteStopResponse,
    UnassignedResponse,
)

DEFAULT_DATABASE_URL = os.getenv(
    "LOGISTIAI_DATABASE_URL",
    f"sqlite:///{Path(__file__).resolve().parents[1] / 'data' / 'logistiai.db'}",
)


def create_app(database_url: str | None = None) -> FastAPI:
    sessions = create_session_factory(database_url or DEFAULT_DATABASE_URL)
    app = FastAPI(title="LogistiAI", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_session():
        session = sessions()
        try:
            yield session
        finally:
            session.close()

    @app.post("/imports/orders", response_model=ImportResponse)
    async def import_orders(request: Request, session: Session = Depends(get_session)) -> ImportResponse:
        result = await _parse_import(request, parse_orders_json, parse_orders_csv)
        upsert_orders(session, result.accepted)
        if result.accepted:
            invalidate_plans(session)
        return _import_response(result.accepted, result.errors)

    @app.post("/imports/vehicles", response_model=ImportResponse)
    async def import_vehicles(request: Request, session: Session = Depends(get_session)) -> ImportResponse:
        result = await _parse_import(request, parse_vehicles_json, parse_vehicles_csv)
        upsert_vehicles(session, result.accepted)
        if result.accepted:
            invalidate_plans(session)
        return _import_response(result.accepted, result.errors)

    @app.post("/route-plans", response_model=RoutePlanResponse, status_code=201)
    def create_route_plan(payload: OptimizeRequest = OptimizeRequest(), session: Session = Depends(get_session)) -> RoutePlanResponse:
        plan = DeterministicRoutingProvider().optimize(
            list_orders(session), list_vehicles(session),
            average_speed_kmh=payload.average_speed_kmh,
            service_minutes=payload.service_minutes,
        )
        return _plan_response(save_plan(session, plan, payload.average_speed_kmh, payload.service_minutes))

    @app.get("/route-plans/{plan_id}", response_model=RoutePlanResponse)
    def read_route_plan(plan_id: int, session: Session = Depends(get_session)) -> RoutePlanResponse:
        plan = get_plan(session, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Route plan not found")
        return _plan_response(plan)

    @app.post("/replans", response_model=ReplanResponse, status_code=201)
    def replan(payload: ReplanRequest, session: Session = Depends(get_session)) -> ReplanResponse:
        """Calculate a scenario without mutating the persistent vehicle statuses."""
        base_plan = get_plan(session, payload.base_plan_id)
        if base_plan is None:
            raise HTTPException(status_code=404, detail="Base route plan not found")
        latest = latest_plan(session)
        if latest is None or latest.id != base_plan.id:
            raise HTTPException(status_code=409, detail="Base route plan is no longer current")

        unavailable_ids = sorted(set(payload.unavailable_vehicle_ids))
        vehicles = list_vehicles(session)
        known_ids = {vehicle.external_id for vehicle in vehicles}
        unknown_ids = sorted(set(unavailable_ids) - known_ids)
        if unknown_ids:
            raise HTTPException(status_code=404, detail=f"Unknown vehicle IDs: {', '.join(unknown_ids)}")

        scenario_vehicles = [vehicle for vehicle in vehicles if vehicle.external_id not in unavailable_ids]
        route_plan = DeterministicRoutingProvider().optimize(
            list_orders(session), scenario_vehicles,
            average_speed_kmh=base_plan.average_speed_kmh,
            service_minutes=base_plan.service_minutes,
        )
        new_plan = _plan_response(save_plan(
            session, route_plan, base_plan.average_speed_kmh, base_plan.service_minutes,
        ))
        before = _snapshot(_plan_response(base_plan))
        after = _snapshot(new_plan)
        return ReplanResponse(
            base_plan_id=base_plan.id,
            plan=new_plan,
            comparison=ReplanComparison(
                before=before, after=after,
                delta=PlanSnapshot(
                    assigned_orders=after.assigned_orders - before.assigned_orders,
                    unassigned_orders=after.unassigned_orders - before.unassigned_orders,
                    distance_km=after.distance_km - before.distance_km,
                    duration_minutes=after.duration_minutes - before.duration_minutes,
                ),
            ),
            unavailable_vehicle_ids=unavailable_ids,
        )

    @app.get("/dashboard", response_model=DashboardResponse)
    def dashboard(session: Session = Depends(get_session)) -> DashboardResponse:
        if not has_imported_data(session):
            _seed_demo(session)
        orders, vehicles, plan = list_orders(session), list_vehicles(session), latest_plan(session)
        if plan is None:
            route_plan = DeterministicRoutingProvider().optimize(orders, vehicles)
            plan = save_plan(session, route_plan, 40, 10)
        plan_response = _plan_response(plan)
        assigned = sum(len(route.stops) for route in plan_response.routes)
        return DashboardResponse(
            summary=DashboardSummary(
                total_orders=len(orders), assigned_orders=assigned,
                unassigned_orders=len(plan_response.unassigned),
                active_vehicles=sum(vehicle.status.lower() == "available" for vehicle in vehicles),
            ),
            orders=[_order_payload(order) for order in orders],
            vehicles=[_vehicle_payload(vehicle) for vehicle in vehicles],
            metrics=plan_response.metrics,
            unassigned=plan_response.unassigned,
            route_plan=plan_response,
        )

    return app


async def _parse_import(request: Request, parse_json: Callable, parse_csv: Callable):
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        try:
            payload = await request.json()
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=400, detail="Invalid JSON payload") from error
        if not isinstance(payload, list):
            raise HTTPException(status_code=422, detail="JSON import must be an array")
        return parse_json([row if isinstance(row, dict) else {} for row in payload])
    form = await request.form()
    upload = form.get("file")
    if upload is None or not hasattr(upload, "read"):
        raise HTTPException(status_code=422, detail="Provide a CSV or JSON file in the file field")
    try:
        raw_payload = (await upload.read()).decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=400, detail="Import files must use UTF-8 encoding") from error
    filename = getattr(upload, "filename", "") or ""
    if filename.lower().endswith(".json"):
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=400, detail="Invalid JSON file") from error
        if not isinstance(payload, list):
            raise HTTPException(status_code=422, detail="JSON import must be an array")
        return parse_json([row if isinstance(row, dict) else {} for row in payload])
    return parse_csv(raw_payload)


def _import_response(accepted: list[Any], errors: list[ImportErrorDetail]) -> ImportResponse:
    return ImportResponse(accepted_count=len(accepted), errors=[error.model_dump() for error in errors])


def _plan_response(plan: RoutePlanRecord) -> RoutePlanResponse:
    routes = [
        RouteResponse(
            vehicle_external_id=route.vehicle_external_id,
            assigned_demand=route.assigned_demand,
            distance_km=sum(stop.distance_km for stop in route.stops),
            duration_minutes=max((stop.eta_minutes for stop in route.stops), default=0),
            stops=[RouteStopResponse(
                order_external_id=stop.order_external_id, latitude=stop.latitude, longitude=stop.longitude,
                sequence=stop.sequence, distance_km=stop.distance_km, eta_minutes=stop.eta_minutes,
            ) for stop in sorted(route.stops, key=lambda item: item.sequence)],
        )
        for route in sorted(plan.routes, key=lambda item: item.vehicle_external_id)
    ]
    unassigned = [
        UnassignedResponse(order_external_id=item.order_external_id, reason=item.reason)
        for item in sorted(plan.unassigned, key=lambda item: item.order_external_id)
    ]
    return RoutePlanResponse(
        id=plan.id, routes=routes,
        metrics=MetricsResponse(
            total_distance_km=sum(route.distance_km for route in routes),
            total_duration_minutes=sum(route.duration_minutes for route in routes),
        ),
        unassigned=unassigned,
    )


def _snapshot(plan: RoutePlanResponse) -> PlanSnapshot:
    return PlanSnapshot(
        assigned_orders=sum(len(route.stops) for route in plan.routes),
        unassigned_orders=len(plan.unassigned),
        distance_km=plan.metrics.total_distance_km,
        duration_minutes=plan.metrics.total_duration_minutes,
    )


def _order_payload(order: Order) -> dict[str, Any]:
    return {"external_id": order.external_id, "latitude": order.latitude, "longitude": order.longitude,
            "demand": order.demand, "priority": order.priority, "status": order.status}


def _vehicle_payload(vehicle: Vehicle) -> dict[str, Any]:
    return {"external_id": vehicle.external_id, "latitude": vehicle.latitude, "longitude": vehicle.longitude,
            "capacity": vehicle.capacity, "status": vehicle.status}


def _seed_demo(session: Session) -> None:
    upsert_orders(session, [
        Order("ALM-101", 43.2384, 76.9457, 4, 3),
        Order("ALM-102", 43.2550, 76.9200, 3, 2),
        Order("ALM-103", 43.2100, 76.8800, 5, 1),
    ])
    upsert_vehicles(session, [
        Vehicle("VAN-01", 43.2380, 76.9450, 6, "available"),
        Vehicle("VAN-02", 43.2350, 76.9400, 3, "available"),
    ])


app = create_app()
