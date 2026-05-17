"""Data model and maintenance rule calculations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from math import ceil
from typing import Any
from uuid import uuid4

from .const import (
    DEFAULT_DUE_SOON_MILES,
    DEFAULT_OVERDUE_MILES,
    ODOMETER_MODE_ENTITY,
    ODOMETER_MODE_MANUAL,
)


def _today() -> date:
    return date.today()


def _months_to_days(months: int) -> int:
    return months * 30


@dataclass(slots=True)
class MaintenanceItemDefinition:
    """Seed or custom maintenance item definition."""

    id: str
    name: str
    interval_miles: int | None = None
    interval_months: int | None = None
    manufacturer_anchor_miles: int | None = None
    flexible: bool = False
    due_soon_threshold_miles: int = DEFAULT_DUE_SOON_MILES
    overdue_threshold_miles: int = DEFAULT_OVERDUE_MILES


@dataclass(slots=True)
class MaintenanceTemplate:
    """Vehicle schedule template."""

    id: str
    label: str
    disclaimer: str
    items: list[MaintenanceItemDefinition] = field(default_factory=list)


@dataclass(slots=True)
class ServiceEvent:
    """Logged maintenance event."""

    id: str
    vehicle_id: str
    item_id: str
    date: str
    odometer: int
    notes: str = ""
    cost: float | None = None

    @property
    def parsed_date(self) -> date:
        return date.fromisoformat(self.date)


@dataclass(slots=True)
class Vehicle:
    """Tracked vehicle."""

    id: str
    name: str
    year: int
    make: str
    model: str
    trim: str
    engine: str
    vin: str | None = None
    current_odometer: int = 0
    odometer_source_mode: str = ODOMETER_MODE_MANUAL
    odometer_entity_id: str | None = None
    template_id: str | None = None
    schedule_items: list[MaintenanceItemDefinition] = field(default_factory=list)
    template_disclaimer: str | None = None


@dataclass(slots=True)
class DueStatus:
    """Calculated maintenance due state."""

    item_id: str
    name: str
    next_due_mileage: int | None
    next_due_date: str | None
    miles_remaining: int | None
    days_remaining: int | None
    is_due: bool
    is_due_soon: bool
    is_overdue: bool
    basis: str


def template_from_dict(data: dict[str, Any]) -> MaintenanceTemplate:
    """Build a template from dict data."""
    return MaintenanceTemplate(
        id=data["id"],
        label=data["label"],
        disclaimer=data["disclaimer"],
        items=[MaintenanceItemDefinition(**item) for item in data.get("items", [])],
    )


def vehicle_from_dict(data: dict[str, Any]) -> Vehicle:
    """Deserialize a vehicle."""
    payload = dict(data)
    payload["schedule_items"] = [
        MaintenanceItemDefinition(**item) for item in payload.get("schedule_items", [])
    ]
    return Vehicle(**payload)


def vehicle_to_dict(vehicle: Vehicle) -> dict[str, Any]:
    """Serialize a vehicle."""
    payload = asdict(vehicle)
    payload["schedule_items"] = [asdict(item) for item in vehicle.schedule_items]
    return payload


def event_from_dict(data: dict[str, Any]) -> ServiceEvent:
    """Deserialize a service event."""
    return ServiceEvent(**data)


def event_to_dict(event: ServiceEvent) -> dict[str, Any]:
    """Serialize a service event."""
    return asdict(event)


def due_status_to_dict(status: DueStatus) -> dict[str, Any]:
    """Serialize due status."""
    return asdict(status)


def make_vehicle(data: dict[str, Any], template: MaintenanceTemplate | None) -> Vehicle:
    """Create a new vehicle."""
    vehicle = Vehicle(
        id=data.get("id", uuid4().hex),
        name=data["name"],
        year=int(data["year"]),
        make=data["make"],
        model=data["model"],
        trim=data.get("trim", ""),
        engine=data.get("engine", ""),
        vin=data.get("vin"),
        current_odometer=int(data.get("current_odometer", 0)),
        odometer_source_mode=data.get("odometer_source_mode", ODOMETER_MODE_MANUAL),
        odometer_entity_id=data.get("odometer_entity_id"),
        template_id=template.id if template else data.get("template_id"),
        schedule_items=list(template.items) if template else [],
        template_disclaimer=template.disclaimer if template else None,
    )
    if vehicle.odometer_source_mode == ODOMETER_MODE_ENTITY and not vehicle.odometer_entity_id:
        msg = "Entity odometer mode requires odometer_entity_id"
        raise ValueError(msg)
    if vehicle.odometer_source_mode not in {ODOMETER_MODE_MANUAL, ODOMETER_MODE_ENTITY}:
        msg = f"Unsupported odometer mode: {vehicle.odometer_source_mode}"
        raise ValueError(msg)
    return vehicle


def make_service_event(data: dict[str, Any]) -> ServiceEvent:
    """Create a new service event."""
    return ServiceEvent(
        id=uuid4().hex,
        vehicle_id=data["vehicle_id"],
        item_id=data["item_id"],
        date=data["date"],
        odometer=int(data["odometer"]),
        notes=data.get("notes", ""),
        cost=float(data["cost"]) if data.get("cost") is not None else None,
    )


def _manufacturer_due_mileage(item: MaintenanceItemDefinition, current_odometer: int) -> int | None:
    if item.interval_miles is None and item.manufacturer_anchor_miles is None:
        return None
    anchor = item.manufacturer_anchor_miles or item.interval_miles or 0
    if current_odometer <= anchor:
        return anchor
    interval = item.interval_miles or anchor
    periods = ceil((current_odometer - anchor) / interval)
    return anchor + (periods * interval)


def _next_due_date_from_event(last_event: ServiceEvent, months: int) -> date:
    return last_event.parsed_date + timedelta(days=_months_to_days(months))


def calculate_due_status(
    vehicle: Vehicle,
    item: MaintenanceItemDefinition,
    events: list[ServiceEvent],
    today: date | None = None,
) -> DueStatus:
    """Calculate due state for a vehicle maintenance item."""
    reference_date = today or _today()
    item_events = sorted(
        (event for event in events if event.vehicle_id == vehicle.id and event.item_id == item.id),
        key=lambda event: (event.odometer, event.date),
    )
    last_event = item_events[-1] if item_events else None

    if item.flexible and last_event and item.interval_miles is not None:
        next_due_mileage = last_event.odometer + item.interval_miles
        basis = "last_service_event"
    else:
        next_due_mileage = _manufacturer_due_mileage(item, vehicle.current_odometer)
        basis = "manufacturer_anchor"

    if item.interval_months is not None and last_event:
        next_due_date = _next_due_date_from_event(last_event, item.interval_months)
    elif item.interval_months is not None and not last_event:
        next_due_date = reference_date + timedelta(days=_months_to_days(item.interval_months))
    else:
        next_due_date = None

    miles_remaining = (
        None if next_due_mileage is None else int(next_due_mileage - vehicle.current_odometer)
    )
    days_remaining = (
        None if next_due_date is None else (next_due_date - reference_date).days
    )
    due_by_miles = miles_remaining is not None and miles_remaining <= item.overdue_threshold_miles
    due_soon_by_miles = (
        miles_remaining is not None and miles_remaining <= item.due_soon_threshold_miles
    )
    due_by_date = days_remaining is not None and days_remaining <= 0
    due_soon_by_date = days_remaining is not None and days_remaining <= 30

    is_due = due_by_miles or due_by_date
    is_due_soon = due_soon_by_miles or due_soon_by_date
    is_overdue = (
        miles_remaining is not None and miles_remaining < item.overdue_threshold_miles
    ) or (days_remaining is not None and days_remaining < 0)

    return DueStatus(
        item_id=item.id,
        name=item.name,
        next_due_mileage=next_due_mileage,
        next_due_date=next_due_date.isoformat() if next_due_date else None,
        miles_remaining=miles_remaining,
        days_remaining=days_remaining,
        is_due=is_due,
        is_due_soon=is_due_soon,
        is_overdue=is_overdue,
        basis=basis,
    )


def summarize_due(statuses: list[DueStatus]) -> str:
    """Build a compact human-readable summary."""
    if not statuses:
        return "No maintenance items configured"
    ranked = sorted(
        statuses,
        key=lambda item: (
            0 if item.is_overdue else 1 if item.is_due else 2 if item.is_due_soon else 3,
            item.miles_remaining if item.miles_remaining is not None else 10**9,
            item.days_remaining if item.days_remaining is not None else 10**9,
        ),
    )
    next_item = ranked[0]
    if next_item.is_overdue:
        return f"{next_item.name} overdue"
    if next_item.is_due:
        return f"{next_item.name} due now"
    if next_item.next_due_mileage is not None:
        return f"{next_item.name} in {next_item.miles_remaining} mi"
    if next_item.next_due_date is not None:
        return f"{next_item.name} due {next_item.next_due_date}"
    return f"{next_item.name} scheduled"
