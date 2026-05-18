"""Coordinator for vehicle maintenance state."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DELETE_CONFIRMATION_WINDOW_SECONDS, DOMAIN
from .models import (
    MaintenanceTemplate,
    Vehicle,
    calculate_due_status,
    calculate_warranty_expiration_date,
    calculate_warranty_miles_remaining,
    event_to_dict,
    get_scheduled_items_for_mileage,
    summarize_due,
    template_from_dict,
)
from .store import VehicleMaintenanceStore
from .templates import SEED_TEMPLATES

LOGGER = logging.getLogger(__name__)


class VehicleMaintenanceCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate storage data and entity-backed odometer updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        store: VehicleMaintenanceStore,
        config_entry_id: str,
    ) -> None:
        super().__init__(hass, logger=LOGGER, name="vehicle_maintenance")
        self.store = store
        self.config_entry_id = config_entry_id
        self.templates: dict[str, MaintenanceTemplate] = {}
        self._unsubscribe_state_listener: Callable[[], None] | None = None
        self._delete_armed_until: dict[str, Any] = {}
        self._delete_disarm_callbacks: dict[str, Callable[[], None]] = {}

    async def async_initialize(self) -> None:
        """Initialize storage, templates, listeners, and first snapshot."""
        self.templates = {
            template_id: template_from_dict(template)
            for template_id, template in SEED_TEMPLATES.items()
        }
        await self.store.async_load()
        self._setup_entity_listener()
        await self.async_refresh()

    def _setup_entity_listener(self) -> None:
        entity_ids = [
            vehicle.odometer_entity_id
            for vehicle in self.store.vehicles.values()
            if vehicle.odometer_entity_id
        ]
        if self._unsubscribe_state_listener is not None:
            self._unsubscribe_state_listener()
            self._unsubscribe_state_listener = None
        if not entity_ids:
            return
        self._unsubscribe_state_listener = async_track_state_change_event(
            self.hass,
            entity_ids,
            self._handle_odometer_state_change,
        )

    @callback
    def _handle_odometer_state_change(self, event: Event[EventStateChangedData]) -> None:
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in {"unknown", "unavailable"}:
            return
        entity_id = new_state.entity_id
        for vehicle in self.store.vehicles.values():
            if vehicle.odometer_entity_id != entity_id:
                continue
            try:
                vehicle.current_odometer = int(float(new_state.state))
            except ValueError:
                continue
        self.hass.async_create_task(self.store.async_save())
        self.async_set_updated_data(self._build_snapshot())

    async def _async_update_data(self) -> dict[str, Any]:
        """Refresh the coordinator snapshot."""
        self._sync_entity_odometer_states()
        return self._build_snapshot()

    def _sync_entity_odometer_states(self) -> None:
        for vehicle in self.store.vehicles.values():
            if not vehicle.odometer_entity_id:
                continue
            state = self.hass.states.get(vehicle.odometer_entity_id)
            if state is None or state.state in {"unknown", "unavailable"}:
                continue
            try:
                vehicle.current_odometer = int(float(state.state))
            except ValueError:
                continue

    def _build_snapshot(self) -> dict[str, Any]:
        snapshot: dict[str, Any] = {"vehicles": {}}
        for vehicle in self.store.vehicles.values():
            due_statuses = [
                calculate_due_status(vehicle, item, self.store.service_events)
                for item in vehicle.schedule_items
            ]
            snapshot["vehicles"][vehicle.id] = {
                "vehicle": vehicle,
                "summary": summarize_due(due_statuses),
                "due_statuses": {status.item_id: status for status in due_statuses},
                "is_due": any(status.is_due for status in due_statuses),
                "warranty_expiration_date": calculate_warranty_expiration_date(vehicle),
                "warranty_miles_remaining": calculate_warranty_miles_remaining(vehicle),
                "recent_service_records": [
                    event_to_dict(event)
                    for event in sorted(
                        (
                            event
                            for event in self.store.service_events
                            if event.vehicle_id == vehicle.id
                        ),
                        key=lambda item: (item.date, item.odometer, item.id),
                        reverse=True,
                    )[:25]
                ],
            }
        return snapshot

    async def async_add_vehicle(self, data: dict[str, Any]) -> Vehicle:
        """Add a vehicle and refresh state."""
        template = self.templates.get(data.get("template_id"))
        vehicle = await self.store.async_add_vehicle(data, template)
        self._setup_entity_listener()
        await self.async_refresh()
        return vehicle

    async def async_edit_vehicle(self, vehicle_id: str, updates: dict[str, Any]) -> Vehicle:
        """Edit a vehicle and refresh state."""
        template = None
        if "template_id" in updates:
            template = self.templates.get(updates["template_id"])
        vehicle = await self.store.async_edit_vehicle(vehicle_id, updates, template)
        self._setup_entity_listener()
        await self.async_refresh()
        return vehicle

    async def async_delete_vehicle(self, vehicle_id: str) -> None:
        """Delete a vehicle and refresh state."""
        self.async_clear_delete_arm(vehicle_id)
        await self.store.async_delete_vehicle(vehicle_id)
        self._remove_vehicle_registry_entries(vehicle_id)
        self._setup_entity_listener()
        await self.async_refresh()

    async def async_update_odometer(self, vehicle_id: str, odometer: int) -> Vehicle:
        """Update odometer and refresh state."""
        vehicle = await self.store.async_update_odometer(vehicle_id, odometer)
        await self.async_refresh()
        return vehicle

    async def async_log_maintenance(self, data: dict[str, Any]) -> None:
        """Log maintenance and refresh state."""
        data.setdefault("event_type", "maintenance_item")
        data.setdefault("affects_schedule", True)
        await self.store.async_log_maintenance(data)
        await self.async_refresh()

    async def async_log_service_visit(self, data: dict[str, Any]) -> None:
        """Log a complete scheduled visit or a custom multi-item visit."""
        vehicle = self.store.vehicles[data["vehicle_id"]]
        item_ids: list[str]
        if data.get("item_ids"):
            item_ids = list(data["item_ids"])
        else:
            scheduled_mileage = int(data["scheduled_mileage"])
            item_ids = [
                item.id for item in get_scheduled_items_for_mileage(vehicle, scheduled_mileage)
            ]
        if not item_ids:
            return

        service_visit_id = f"{data['vehicle_id']}_{data['date']}_{data['odometer']}"
        events = []
        for item_id in item_ids:
            event_data = dict(data)
            event_data["item_id"] = item_id
            event_data["service_visit_id"] = service_visit_id
            event_data["event_type"] = "maintenance_item"
            event_data["affects_schedule"] = True
            if not event_data.get("title"):
                event_data["title"] = item_id
            events.append(event_data)
        await self.store.async_log_maintenance_events(events)
        await self.async_refresh()

    async def async_log_service_record(self, data: dict[str, Any]) -> None:
        """Log an ad hoc service record that does not need a schedule item."""
        payload = dict(data)
        payload["event_type"] = "service_record"
        payload["affects_schedule"] = bool(payload.get("affects_schedule", False))
        payload.setdefault("item_id", None)
        await self.store.async_log_maintenance(payload)
        await self.async_refresh()

    def get_vehicle_snapshot(self, vehicle_id: str) -> dict[str, Any]:
        """Return computed state for a vehicle."""
        return self.data["vehicles"][vehicle_id]

    def get_template_choices(self) -> dict[str, str]:
        """Expose template choices for config and services."""
        return {template_id: template.label for template_id, template in self.templates.items()}

    def is_delete_armed(self, vehicle_id: str) -> bool:
        """Return whether delete confirmation is currently armed."""
        armed_until = self._delete_armed_until.get(vehicle_id)
        return armed_until is not None and armed_until > dt_util.utcnow()

    def get_delete_armed_until(self, vehicle_id: str) -> str | None:
        """Return the confirmation expiry time."""
        armed_until = self._delete_armed_until.get(vehicle_id)
        return None if armed_until is None else armed_until.isoformat()

    def async_arm_delete(self, vehicle_id: str) -> None:
        """Arm delete confirmation for a short time window."""
        self.async_clear_delete_arm(vehicle_id)
        armed_until = dt_util.utcnow() + timedelta(seconds=DELETE_CONFIRMATION_WINDOW_SECONDS)
        self._delete_armed_until[vehicle_id] = armed_until
        self._delete_disarm_callbacks[vehicle_id] = async_call_later(
            self.hass,
            DELETE_CONFIRMATION_WINDOW_SECONDS,
            lambda _: self.async_clear_delete_arm(vehicle_id),
        )
        self.async_update_listeners()

    def async_clear_delete_arm(self, vehicle_id: str) -> None:
        """Clear delete confirmation state."""
        if unsub := self._delete_disarm_callbacks.pop(vehicle_id, None):
            unsub()
        if vehicle_id in self._delete_armed_until:
            self._delete_armed_until.pop(vehicle_id, None)
            self.async_update_listeners()

    def _remove_vehicle_registry_entries(self, vehicle_id: str) -> None:
        """Remove entity and device registry entries for a deleted vehicle."""
        entity_registry = er.async_get(self.hass)
        for entity_entry in er.async_entries_for_config_entry(entity_registry, self.config_entry_id):
            if entity_entry.unique_id.startswith(f"{vehicle_id}_"):
                entity_registry.async_remove(entity_entry.entity_id)

        device_registry = dr.async_get(self.hass)
        device_entry = device_registry.async_get_device(identifiers={(DOMAIN, vehicle_id)})
        if device_entry is not None:
            device_registry.async_remove_device(device_entry.id)
