"""Storage-backed manager for vehicles and service events."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from dataclasses import asdict

from .models import (
    MaintenanceTemplate,
    ServiceEvent,
    Vehicle,
    event_from_dict,
    event_to_dict,
    make_service_event,
    make_vehicle,
    vehicle_from_dict,
    vehicle_to_dict,
)


class VehicleMaintenanceStore:
    """Persistence wrapper around Home Assistant storage."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.vehicles: dict[str, Vehicle] = {}
        self.service_events: list[ServiceEvent] = []

    async def async_load(self) -> None:
        """Load stored data."""
        data = await self._store.async_load() or {}
        self.vehicles = {
            item["id"]: vehicle_from_dict(item) for item in data.get("vehicles", [])
        }
        self.service_events = [event_from_dict(item) for item in data.get("service_events", [])]

    async def async_save(self) -> None:
        """Persist current state."""
        payload = {
            "vehicles": [vehicle_to_dict(vehicle) for vehicle in self.vehicles.values()],
            "service_events": [event_to_dict(event) for event in self.service_events],
        }
        await self._store.async_save(payload)

    async def async_add_vehicle(
        self,
        vehicle_data: dict[str, Any],
        template: MaintenanceTemplate | None,
    ) -> Vehicle:
        """Add a vehicle."""
        vehicle = make_vehicle(vehicle_data, template)
        self.vehicles[vehicle.id] = vehicle
        await self.async_save()
        return vehicle

    async def async_edit_vehicle(
        self,
        vehicle_id: str,
        updates: dict[str, Any],
        template: MaintenanceTemplate | None = None,
    ) -> Vehicle:
        """Edit a vehicle."""
        vehicle = self.vehicles[vehicle_id]
        current = deepcopy(vehicle_to_dict(vehicle))
        current.update(updates)
        if template is not None:
            current["template_id"] = template.id
            current["schedule_items"] = [asdict(item) for item in template.items]
            current["template_disclaimer"] = template.disclaimer
        updated = vehicle_from_dict(current)
        self.vehicles[vehicle_id] = updated
        await self.async_save()
        return updated

    async def async_delete_vehicle(self, vehicle_id: str) -> None:
        """Delete a vehicle and its events."""
        self.vehicles.pop(vehicle_id, None)
        self.service_events = [
            event for event in self.service_events if event.vehicle_id != vehicle_id
        ]
        await self.async_save()

    async def async_update_odometer(self, vehicle_id: str, odometer: int) -> Vehicle:
        """Update a vehicle odometer."""
        vehicle = self.vehicles[vehicle_id]
        vehicle.current_odometer = int(odometer)
        self.vehicles[vehicle_id] = vehicle
        await self.async_save()
        return vehicle

    async def async_log_maintenance(self, event_data: dict[str, Any]) -> ServiceEvent:
        """Log a maintenance event."""
        event = make_service_event(event_data)
        self.service_events.append(event)
        await self.async_save()
        return event

    async def async_log_maintenance_events(
        self,
        events_data: list[dict[str, Any]],
    ) -> list[ServiceEvent]:
        """Log multiple maintenance events as one save operation."""
        events = [make_service_event(event_data) for event_data in events_data]
        self.service_events.extend(events)
        await self.async_save()
        return events
