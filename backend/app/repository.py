"""Persistence adapter translating SQLAlchemy records to the routing domain."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain import Order, RoutePlan, Vehicle
from app.models import (
    OrderRecord,
    RoutePlanRecord,
    RouteRecord,
    RouteStopRecord,
    UnassignedRecord,
    VehicleRecord,
)


def list_orders(session: Session) -> list[Order]:
    return [
        Order(record.external_id, record.latitude, record.longitude, record.demand, record.priority, record.status)
        for record in session.scalars(select(OrderRecord).order_by(OrderRecord.external_id))
    ]


def list_vehicles(session: Session) -> list[Vehicle]:
    return [
        Vehicle(record.external_id, record.latitude, record.longitude, record.capacity, record.status)
        for record in session.scalars(select(VehicleRecord).order_by(VehicleRecord.external_id))
    ]


def upsert_orders(session: Session, orders: list[Order]) -> None:
    existing = {record.external_id: record for record in session.scalars(select(OrderRecord))}
    for order in orders:
        record = existing.get(order.external_id)
        if record is None:
            session.add(OrderRecord(
                external_id=order.external_id, latitude=order.latitude, longitude=order.longitude,
                demand=order.demand, priority=order.priority, status=order.status,
            ))
        else:
            record.latitude, record.longitude = order.latitude, order.longitude
            record.demand, record.priority, record.status = order.demand, order.priority, order.status
    session.commit()


def upsert_vehicles(session: Session, vehicles: list[Vehicle]) -> None:
    existing = {record.external_id: record for record in session.scalars(select(VehicleRecord))}
    for vehicle in vehicles:
        record = existing.get(vehicle.external_id)
        if record is None:
            session.add(VehicleRecord(
                external_id=vehicle.external_id, latitude=vehicle.latitude, longitude=vehicle.longitude,
                capacity=vehicle.capacity, status=vehicle.status,
            ))
        else:
            record.latitude, record.longitude = vehicle.latitude, vehicle.longitude
            record.capacity, record.status = vehicle.capacity, vehicle.status
    session.commit()


def save_plan(session: Session, plan: RoutePlan, average_speed_kmh: float, service_minutes: float) -> RoutePlanRecord:
    record = RoutePlanRecord(average_speed_kmh=average_speed_kmh, service_minutes=service_minutes)
    for route in plan.routes:
        route_record = RouteRecord(vehicle_external_id=route.vehicle.external_id, assigned_demand=route.assigned_demand)
        for stop in route.stops:
            route_record.stops.append(RouteStopRecord(
                order_external_id=stop.order.external_id,
                latitude=stop.order.latitude,
                longitude=stop.order.longitude,
                sequence=stop.sequence,
                distance_km=stop.distance_km,
                eta_minutes=stop.eta_minutes,
            ))
        record.routes.append(route_record)
    record.unassigned.extend(
        UnassignedRecord(order_external_id=item.order.external_id, reason=item.reason)
        for item in plan.unassigned
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def get_plan(session: Session, plan_id: int) -> RoutePlanRecord | None:
    query = (
        select(RoutePlanRecord)
        .where(RoutePlanRecord.id == plan_id)
        .options(selectinload(RoutePlanRecord.routes).selectinload(RouteRecord.stops), selectinload(RoutePlanRecord.unassigned))
    )
    return session.scalar(query)


def latest_plan(session: Session) -> RoutePlanRecord | None:
    query = (
        select(RoutePlanRecord)
        .order_by(RoutePlanRecord.id.desc())
        .options(selectinload(RoutePlanRecord.routes).selectinload(RouteRecord.stops), selectinload(RoutePlanRecord.unassigned))
    )
    return session.scalar(query)


def has_imported_data(session: Session) -> bool:
    return session.scalar(select(OrderRecord.id).limit(1)) is not None or session.scalar(select(VehicleRecord.id).limit(1)) is not None


def invalidate_plans(session: Session) -> None:
    """Discard derived plans after source orders or vehicles have changed."""
    for plan in session.scalars(select(RoutePlanRecord)):
        session.delete(plan)
    session.commit()
