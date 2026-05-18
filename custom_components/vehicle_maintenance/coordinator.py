"""Coordinator for vehicle maintenance state."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any

from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .models import MaintenanceTemplate, Vehicle, calculate_due_status, summarize_due, template_from_dict
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
        await self.store.async_log_maintenance(data)
        await self.async_refresh()

    def get_vehicle_snapshot(self, vehicle_id: str) -> dict[str, Any]:
        """Return computed state for a vehicle."""
        return self.data["vehicles"][vehicle_id]

    def get_template_choices(self) -> dict[str, str]:
        """Expose template choices for config and services."""
        return {template_id: template.label for template_id, template in self.templates.items()}

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
