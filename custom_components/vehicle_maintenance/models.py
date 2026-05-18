"""Data model and maintenance rule calculations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from math import ceil
import re
from typing import Any
from uuid import uuid4

from .const import (
    ATTR_SCHEDULE_DISCLAIMER,
    DEFAULT_DUE_SOON_MILES,
    DEFAULT_OVERDUE_MILES,
    ODOMETER_MODE_ENTITY,
    ODOMETER_MODE_MANUAL,
)


def _today() -> date:
    return date.today()


def _months_to_days(months: int) -> int:
    return months * 30


def _slugify_identifier(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    return slug or uuid4().hex


@dataclass(slots=True)
class MaintenanceItemDefinition:
    """Seed or custom maintenance item definition."""

    id: str
    name: str
    interval_miles: int | None = None
    interval_months: int | None = None
    manufacturer_anchor_miles: int | None = None
    flexible: bool = False
    resets_on_service: bool = False
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
class VehicleSubscription:
    """Optional vehicle subscription or plan."""

    id: str
    name: str
    category: str | None = None
    provider: str | None = None
    start_date: str | None = None
    renewal_date: str | None = None
    cost: float | None = None
    notes: str = ""


@dataclass(slots=True)
class SubscriptionStatus:
    """Calculated status for a vehicle subscription."""

    id: str
    name: str
    category: str | None
    provider: str | None
    start_date: str | None
    renewal_date: str | None
    cost: float | None
    notes: str
    is_active: bool
    days_remaining: int | None


@dataclass(slots=True)
class ServiceEvent:
    """Logged maintenance event."""

    id: str
    vehicle_id: str
    item_id: str | None
    date: str
    odometer: int
    event_type: str = "maintenance_item"
    title: str | None = None
    category: str | None = None
    affects_schedule: bool = False
    source: str | None = None
    scheduled_mileage: int | None = None
    service_visit_id: str | None = None
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
    purchase_date: str | None = None
    purchase_odometer: int | None = None
    warranty_start_date: str | None = None
    warranty_years: int | None = None
    warranty_miles: int | None = None
    warranty_name: str | None = None
    current_odometer: int = 0
    odometer_source_mode: str = ODOMETER_MODE_MANUAL
    odometer_entity_id: str | None = None
    template_id: str | None = None
    schedule_items: list[MaintenanceItemDefinition] = field(default_factory=list)
    subscriptions: list[VehicleSubscription] = field(default_factory=list)
    template_disclaimer: str | None = None


@dataclass(slots=True)
class DueStatus:
    """Calculated maintenance due state."""

    item_id: str
    name: str
    manual_next_due_mileage: int | None
    manual_next_due_date: str | None
    adjusted_next_due_mileage: int | None
    adjusted_next_due_date: str | None
    next_due_mileage: int | None
    next_due_date: str | None
    miles_remaining: int | None
    days_remaining: int | None
    is_due: bool
    is_due_soon: bool
    is_overdue: bool
    basis: str
    last_service_date: str | None = None
    last_service_odometer: int | None = None


def template_from_dict(data: dict[str, Any]) -> MaintenanceTemplate:
    """Build a template from dict data."""
    return MaintenanceTemplate(
        id=data["id"],
        label=data["label"],
        disclaimer=data["disclaimer"],
        items=[MaintenanceItemDefinition(**item) for item in data.get("items", [])],
    )


def template_to_dict(template: MaintenanceTemplate) -> dict[str, Any]:
    """Serialize a maintenance template."""
    return asdict(template)


def template_from_import(
    data: dict[str, Any],
    existing_ids: set[str] | None = None,
) -> MaintenanceTemplate:
    """Build a custom template from an imported package or raw template dict."""
    template_payload = dict(data.get("template", data))
    label = str(template_payload.get("label", "")).strip()
    if not label:
        msg = "Imported template requires a non-empty label"
        raise ValueError(msg)

    template_id = _slugify_identifier(str(template_payload.get("id") or label))
    existing_ids = existing_ids or set()
    base_template_id = template_id
    suffix = 2
    while template_id in existing_ids:
        template_id = f"{base_template_id}_{suffix}"
        suffix += 1

    items_payload = template_payload.get("items")
    if not isinstance(items_payload, list) or not items_payload:
        msg = "Imported template requires a non-empty items list"
        raise ValueError(msg)

    items: list[MaintenanceItemDefinition] = []
    seen_item_ids: set[str] = set()
    for raw_item in items_payload:
        if not isinstance(raw_item, dict):
            msg = "Every imported item must be an object"
            raise ValueError(msg)
        item_name = str(raw_item.get("name", "")).strip()
        if not item_name:
            msg = "Every imported item requires a non-empty name"
            raise ValueError(msg)
        item_id = _slugify_identifier(str(raw_item.get("id") or item_name))
        if item_id in seen_item_ids:
            msg = f"Duplicate imported item id: {item_id}"
            raise ValueError(msg)
        seen_item_ids.add(item_id)
        items.append(
            MaintenanceItemDefinition(
                id=item_id,
                name=item_name,
                interval_miles=(
                    None
                    if raw_item.get("interval_miles") is None
                    else int(raw_item["interval_miles"])
                ),
                interval_months=(
                    None
                    if raw_item.get("interval_months") is None
                    else int(raw_item["interval_months"])
                ),
                manufacturer_anchor_miles=(
                    None
                    if raw_item.get("manufacturer_anchor_miles") is None
                    else int(raw_item["manufacturer_anchor_miles"])
                ),
                flexible=bool(raw_item.get("flexible", False)),
                resets_on_service=bool(raw_item.get("resets_on_service", False)),
                due_soon_threshold_miles=int(
                    raw_item.get("due_soon_threshold_miles", DEFAULT_DUE_SOON_MILES)
                ),
                overdue_threshold_miles=int(
                    raw_item.get("overdue_threshold_miles", DEFAULT_OVERDUE_MILES)
                ),
            )
        )

    disclaimer = str(template_payload.get("disclaimer") or ATTR_SCHEDULE_DISCLAIMER).strip()
    return MaintenanceTemplate(
        id=template_id,
        label=label,
        disclaimer=disclaimer,
        items=items,
    )


def subscription_from_dict(data: dict[str, Any]) -> VehicleSubscription:
    """Deserialize a vehicle subscription."""
    payload = dict(data)
    payload.setdefault("id", uuid4().hex)
    if payload.get("cost") is not None:
        payload["cost"] = float(payload["cost"])
    payload["notes"] = payload.get("notes", "")
    return VehicleSubscription(**payload)


def vehicle_from_dict(data: dict[str, Any]) -> Vehicle:
    """Deserialize a vehicle."""
    payload = dict(data)
    payload["schedule_items"] = [
        MaintenanceItemDefinition(**item) for item in payload.get("schedule_items", [])
    ]
    payload["subscriptions"] = [
        subscription_from_dict(item) for item in payload.get("subscriptions", [])
    ]
    return Vehicle(**payload)


def vehicle_to_dict(vehicle: Vehicle) -> dict[str, Any]:
    """Serialize a vehicle."""
    payload = asdict(vehicle)
    payload["schedule_items"] = [asdict(item) for item in vehicle.schedule_items]
    payload["subscriptions"] = [asdict(item) for item in vehicle.subscriptions]
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
        purchase_date=data.get("purchase_date"),
        purchase_odometer=(
            int(data["purchase_odometer"]) if data.get("purchase_odometer") is not None else None
        ),
        warranty_start_date=data.get("warranty_start_date") or data.get("purchase_date"),
        warranty_years=(
            int(data["warranty_years"]) if data.get("warranty_years") is not None else None
        ),
        warranty_miles=(
            int(data["warranty_miles"]) if data.get("warranty_miles") is not None else None
        ),
        warranty_name=data.get("warranty_name"),
        current_odometer=int(data.get("current_odometer", 0)),
        odometer_source_mode=data.get("odometer_source_mode", ODOMETER_MODE_MANUAL),
        odometer_entity_id=data.get("odometer_entity_id"),
        template_id=template.id if template else data.get("template_id"),
        schedule_items=list(template.items) if template else [],
        subscriptions=[
            subscription_from_dict(item)
            for item in data.get("subscriptions", [])
        ],
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
        item_id=data.get("item_id"),
        date=data["date"],
        odometer=int(data["odometer"]),
        event_type=data.get("event_type", "maintenance_item"),
        title=data.get("title"),
        category=data.get("category"),
        affects_schedule=bool(data.get("affects_schedule", False)),
        source=data.get("source") or data.get("service_source"),
        scheduled_mileage=(
            int(data["scheduled_mileage"]) if data.get("scheduled_mileage") is not None else None
        ),
        service_visit_id=data.get("service_visit_id"),
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


def item_resets_on_service(item: MaintenanceItemDefinition) -> bool:
    """Return whether a matching event resets the next due interval."""
    return item.resets_on_service or item.flexible


def is_item_scheduled_for_mileage(
    item: MaintenanceItemDefinition,
    scheduled_mileage: int,
) -> bool:
    """Return whether a maintenance item belongs to a scheduled mileage visit."""
    anchor = item.manufacturer_anchor_miles or item.interval_miles
    if anchor is None or scheduled_mileage < anchor:
        return False
    if scheduled_mileage == anchor:
        return True
    interval = item.interval_miles or anchor
    return (scheduled_mileage - anchor) % interval == 0


def get_scheduled_items_for_mileage(
    vehicle: Vehicle,
    scheduled_mileage: int,
) -> list[MaintenanceItemDefinition]:
    """Return all schedule items associated with a scheduled mileage visit."""
    return [
        item
        for item in vehicle.schedule_items
        if is_item_scheduled_for_mileage(item, scheduled_mileage)
    ]


def get_schedule_window_mileages(vehicle: Vehicle) -> list[int]:
    """Return a sorted list of candidate schedule mileages around the current odometer."""
    current_odometer = vehicle.current_odometer
    mileages: set[int] = set()
    for item in vehicle.schedule_items:
        anchor = item.manufacturer_anchor_miles or item.interval_miles
        if anchor is None:
            continue
        interval = item.interval_miles or anchor
        if current_odometer <= anchor:
            mileages.add(anchor)
            mileages.add(anchor + interval)
            continue
        periods = ceil((current_odometer - anchor) / interval)
        current_window = anchor + (periods * interval)
        mileages.add(current_window)
        if current_window - interval >= anchor:
            mileages.add(current_window - interval)
        mileages.add(current_window + interval)
    return sorted(mileage for mileage in mileages if mileage >= 0)


def get_service_windows(vehicle: Vehicle) -> list[dict[str, Any]]:
    """Return previous/current/next mileage windows for checklist logging."""
    candidate_mileages = get_schedule_window_mileages(vehicle)
    if not candidate_mileages:
        return []

    current_odometer = vehicle.current_odometer
    current_index = 0
    for index, mileage in enumerate(candidate_mileages):
        current_index = index
        if mileage >= current_odometer:
            break
    labels = ["previous", "current", "next"]
    windows: list[dict[str, Any]] = []
    for label, offset in zip(labels, (-1, 0, 1), strict=True):
        index = current_index + offset
        if index < 0 or index >= len(candidate_mileages):
            continue
        mileage = candidate_mileages[index]
        windows.append(
            {
                "label": label,
                "scheduled_mileage": mileage,
                "items": get_scheduled_items_for_mileage(vehicle, mileage),
            }
        )
    return windows


def calculate_warranty_expiration_date(vehicle: Vehicle) -> str | None:
    """Return the projected warranty expiration date."""
    if vehicle.warranty_start_date is None or vehicle.warranty_years is None:
        return None
    start_date = date.fromisoformat(vehicle.warranty_start_date)
    return (start_date + timedelta(days=vehicle.warranty_years * 365)).isoformat()


def calculate_warranty_miles_remaining(vehicle: Vehicle) -> int | None:
    """Return remaining warranty miles."""
    if vehicle.warranty_miles is None:
        return None
    return vehicle.warranty_miles - vehicle.current_odometer


def calculate_subscription_statuses(
    vehicle: Vehicle,
    today: date | None = None,
) -> list[SubscriptionStatus]:
    """Return computed subscription and plan statuses for a vehicle."""
    reference_date = today or _today()
    statuses: list[SubscriptionStatus] = []
    for subscription in vehicle.subscriptions:
        if subscription.renewal_date is None:
            days_remaining = None
            is_active = True
        else:
            renewal_date = date.fromisoformat(subscription.renewal_date)
            days_remaining = (renewal_date - reference_date).days
            is_active = days_remaining >= 0
        statuses.append(
            SubscriptionStatus(
                id=subscription.id,
                name=subscription.name,
                category=subscription.category,
                provider=subscription.provider,
                start_date=subscription.start_date,
                renewal_date=subscription.renewal_date,
                cost=subscription.cost,
                notes=subscription.notes,
                is_active=is_active,
                days_remaining=days_remaining,
            )
        )
    return sorted(
        statuses,
        key=lambda item: (
            item.days_remaining is None,
            item.days_remaining if item.days_remaining is not None else 10**9,
            item.name.lower(),
        ),
    )


def calculate_total_maintenance_cost(
    vehicle_id: str,
    events: list[ServiceEvent],
) -> float:
    """Return the total logged maintenance cost for a vehicle."""
    return round(
        sum(
            event.cost or 0
            for event in events
            if event.vehicle_id == vehicle_id
        ),
        2,
    )


def calculate_due_status(
    vehicle: Vehicle,
    item: MaintenanceItemDefinition,
    events: list[ServiceEvent],
    today: date | None = None,
) -> DueStatus:
    """Calculate due state for a vehicle maintenance item."""
    reference_date = today or _today()
    item_events = sorted(
        (
            event
            for event in events
            if event.vehicle_id == vehicle.id
            and event.item_id == item.id
            and event.affects_schedule
        ),
        key=lambda event: (event.odometer, event.date),
    )
    last_event = item_events[-1] if item_events else None

    manual_next_due_mileage = _manufacturer_due_mileage(item, vehicle.current_odometer)
    if item_resets_on_service(item) and last_event and item.interval_miles is not None:
        adjusted_next_due_mileage = last_event.odometer + item.interval_miles
        basis = "last_service_event"
    else:
        adjusted_next_due_mileage = manual_next_due_mileage
        basis = "manufacturer_anchor"

    if item.interval_months is not None and last_event:
        adjusted_next_due_date = _next_due_date_from_event(last_event, item.interval_months)
    elif item.interval_months is not None and not last_event:
        adjusted_next_due_date = reference_date + timedelta(days=_months_to_days(item.interval_months))
    else:
        adjusted_next_due_date = None

    if (
        item.interval_months is not None
        and item.manufacturer_anchor_miles is not None
        and manual_next_due_mileage is not None
        and item.interval_miles
    ):
        remaining_intervals = max(
            0,
            (manual_next_due_mileage - item.manufacturer_anchor_miles) // item.interval_miles,
        )
        manual_next_due_date = reference_date + timedelta(
            days=_months_to_days(item.interval_months * remaining_intervals),
        )
    else:
        manual_next_due_date = adjusted_next_due_date

    next_due_mileage = adjusted_next_due_mileage
    next_due_date = adjusted_next_due_date

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
        manual_next_due_mileage=manual_next_due_mileage,
        manual_next_due_date=manual_next_due_date.isoformat() if manual_next_due_date else None,
        adjusted_next_due_mileage=adjusted_next_due_mileage,
        adjusted_next_due_date=(
            adjusted_next_due_date.isoformat() if adjusted_next_due_date else None
        ),
        next_due_mileage=next_due_mileage,
        next_due_date=next_due_date.isoformat() if next_due_date else None,
        miles_remaining=miles_remaining,
        days_remaining=days_remaining,
        is_due=is_due,
        is_due_soon=is_due_soon,
        is_overdue=is_overdue,
        basis=basis,
        last_service_date=None if last_event is None else last_event.date,
        last_service_odometer=None if last_event is None else last_event.odometer,
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
