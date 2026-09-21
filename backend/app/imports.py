import csv
from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Generic, Iterable, TypeVar

from pydantic import BaseModel

from app.domain import Order, Vehicle

T = TypeVar("T")


class ImportErrorDetail(BaseModel):
    row: int
    field: str
    reason: str


@dataclass(slots=True)
class ImportResult(Generic[T]):
    accepted: list[T] = field(default_factory=list)
    errors: list[ImportErrorDetail] = field(default_factory=list)


def parse_orders_json(rows: Iterable[dict[str, Any]]) -> ImportResult[Order]:
    result: ImportResult[Order] = ImportResult()
    external_ids: set[str] = set()
    for row_number, raw in enumerate(rows, start=1):
        errors: list[ImportErrorDetail] = []
        external_id = _required_text(raw, "external_id", row_number, errors)
        latitude = _coordinate(raw, "latitude", -90, 90, row_number, errors)
        longitude = _coordinate(raw, "longitude", -180, 180, row_number, errors)
        demand = _positive_number(raw, "demand", row_number, errors)
        priority = _integer(raw, "priority", row_number, errors)
        status = _optional_text(raw, "status", "pending")
        if external_id is not None and external_id in external_ids:
            errors.append(
                ImportErrorDetail(
                    row=row_number,
                    field="external_id",
                    reason="duplicate_external_id",
                )
            )
        if errors:
            result.errors.extend(errors)
            continue
        external_ids.add(external_id)
        result.accepted.append(
            Order(external_id, latitude, longitude, demand, priority, status)  # type: ignore[arg-type]
        )
    return result


def parse_orders_csv(payload: str) -> ImportResult[Order]:
    """Parse an orders CSV, retaining source line numbers (including the header)."""
    result: ImportResult[Order] = ImportResult()
    external_ids: set[str] = set()
    for row_number, raw in enumerate(csv.DictReader(payload.splitlines()), start=2):
        errors: list[ImportErrorDetail] = []
        external_id = _required_text(raw, "external_id", row_number, errors)
        latitude = _coordinate(raw, "latitude", -90, 90, row_number, errors)
        longitude = _coordinate(raw, "longitude", -180, 180, row_number, errors)
        demand = _positive_number(raw, "demand", row_number, errors)
        priority = _integer(raw, "priority", row_number, errors)
        status = _optional_text(raw, "status", "pending")
        if external_id is not None and external_id in external_ids:
            errors.append(ImportErrorDetail(row=row_number, field="external_id", reason="duplicate_external_id"))
        if errors:
            result.errors.extend(errors)
            continue
        external_ids.add(external_id)
        result.accepted.append(Order(external_id, latitude, longitude, demand, priority, status))  # type: ignore[arg-type]
    return result


def parse_vehicles_json(rows: Iterable[dict[str, Any]]) -> ImportResult[Vehicle]:
    result: ImportResult[Vehicle] = ImportResult()
    external_ids: set[str] = set()
    for row_number, raw in enumerate(rows, start=1):
        errors: list[ImportErrorDetail] = []
        external_id = _required_text(raw, "external_id", row_number, errors)
        latitude = _coordinate(raw, "latitude", -90, 90, row_number, errors)
        longitude = _coordinate(raw, "longitude", -180, 180, row_number, errors)
        capacity = _positive_number(raw, "capacity", row_number, errors)
        status = _optional_text(raw, "status", "available")
        if external_id is not None and external_id in external_ids:
            errors.append(
                ImportErrorDetail(row=row_number, field="external_id", reason="duplicate_external_id")
            )
        if errors:
            result.errors.extend(errors)
            continue
        external_ids.add(external_id)
        result.accepted.append(Vehicle(external_id, latitude, longitude, capacity, status))  # type: ignore[arg-type]
    return result


def parse_vehicles_csv(payload: str) -> ImportResult[Vehicle]:
    """Parse a vehicles CSV, retaining source line numbers (including the header)."""
    result: ImportResult[Vehicle] = ImportResult()
    external_ids: set[str] = set()
    for row_number, raw in enumerate(csv.DictReader(payload.splitlines()), start=2):
        errors: list[ImportErrorDetail] = []
        external_id = _required_text(raw, "external_id", row_number, errors)
        latitude = _coordinate(raw, "latitude", -90, 90, row_number, errors)
        longitude = _coordinate(raw, "longitude", -180, 180, row_number, errors)
        capacity = _positive_number(raw, "capacity", row_number, errors)
        status = _optional_text(raw, "status", "available")
        if external_id is not None and external_id in external_ids:
            errors.append(
                ImportErrorDetail(row=row_number, field="external_id", reason="duplicate_external_id")
            )
        if errors:
            result.errors.extend(errors)
            continue
        external_ids.add(external_id)
        result.accepted.append(Vehicle(external_id, latitude, longitude, capacity, status))  # type: ignore[arg-type]
    return result


def _required_text(
    raw: dict[str, Any], field_name: str, row: int, errors: list[ImportErrorDetail]
) -> str | None:
    value = raw.get(field_name)
    if not isinstance(value, str) or not value.strip():
        errors.append(ImportErrorDetail(row=row, field=field_name, reason="required"))
        return None
    return value.strip()


def _optional_text(raw: dict[str, Any], field_name: str, default: str) -> str:
    value = raw.get(field_name)
    return value.strip() if isinstance(value, str) and value.strip() else default


def _coordinate(
    raw: dict[str, Any], field_name: str, minimum: float, maximum: float,
    row: int, errors: list[ImportErrorDetail],
) -> float | None:
    value = _number(raw, field_name, row, errors)
    if value is not None and not minimum <= value <= maximum:
        errors.append(ImportErrorDetail(row=row, field=field_name, reason="out_of_range"))
        return None
    return value


def _positive_number(
    raw: dict[str, Any], field_name: str, row: int, errors: list[ImportErrorDetail]
) -> float | None:
    value = _number(raw, field_name, row, errors)
    if value is not None and value <= 0:
        errors.append(ImportErrorDetail(row=row, field=field_name, reason="must_be_positive"))
        return None
    return value


def _number(
    raw: dict[str, Any], field_name: str, row: int, errors: list[ImportErrorDetail]
) -> float | None:
    value = raw.get(field_name)
    if value is None or value == "":
        errors.append(ImportErrorDetail(row=row, field=field_name, reason="required"))
        return None
    if isinstance(value, bool):
        errors.append(ImportErrorDetail(row=row, field=field_name, reason="invalid_number"))
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        errors.append(ImportErrorDetail(row=row, field=field_name, reason="invalid_number"))
        return None
    if not isfinite(parsed):
        errors.append(ImportErrorDetail(row=row, field=field_name, reason="invalid_number"))
        return None
    return parsed


def _integer(
    raw: dict[str, Any], field_name: str, row: int, errors: list[ImportErrorDetail]
) -> int | None:
    value = _number(raw, field_name, row, errors)
    if value is not None and not value.is_integer():
        errors.append(ImportErrorDetail(row=row, field=field_name, reason="invalid_integer"))
        return None
    return int(value) if value is not None else None
