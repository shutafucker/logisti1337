"""SQLAlchemy records for imported logistics data and calculated plans."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrderRecord(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    demand: Mapped[float] = mapped_column(Float)
    priority: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="pending")


class VehicleRecord(Base):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    capacity: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="available")


class RoutePlanRecord(Base):
    __tablename__ = "route_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    average_speed_kmh: Mapped[float] = mapped_column(Float)
    service_minutes: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    routes: Mapped[list[RouteRecord]] = relationship(back_populates="plan", cascade="all, delete-orphan")
    unassigned: Mapped[list[UnassignedRecord]] = relationship(back_populates="plan", cascade="all, delete-orphan")


class RouteRecord(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("route_plans.id"), index=True)
    vehicle_external_id: Mapped[str] = mapped_column(String(128))
    assigned_demand: Mapped[float] = mapped_column(Float)
    plan: Mapped[RoutePlanRecord] = relationship(back_populates="routes")
    stops: Mapped[list[RouteStopRecord]] = relationship(back_populates="route", cascade="all, delete-orphan")


class RouteStopRecord(Base):
    __tablename__ = "route_stops"

    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), index=True)
    order_external_id: Mapped[str] = mapped_column(String(128))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    sequence: Mapped[int] = mapped_column(Integer)
    distance_km: Mapped[float] = mapped_column(Float)
    eta_minutes: Mapped[float] = mapped_column(Float)
    route: Mapped[RouteRecord] = relationship(back_populates="stops")


class UnassignedRecord(Base):
    __tablename__ = "unassigned_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("route_plans.id"), index=True)
    order_external_id: Mapped[str] = mapped_column(String(128))
    reason: Mapped[str] = mapped_column(String(64))
    plan: Mapped[RoutePlanRecord] = relationship(back_populates="unassigned")
