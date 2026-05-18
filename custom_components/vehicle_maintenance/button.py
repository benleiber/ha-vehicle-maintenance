"""Buttons for quick maintenance actions."""

from __future__ import annotations

from datetime import date
from typing import Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import VehicleMaintenanceCoordinatorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up buttons."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    known_ids: set[str] = set()

    @callback
    def _async_sync_entities() -> None:
        new_entities: list[ButtonEntity] = []
        for vehicle_id in coordinator.data["vehicles"]:
            log_unique_id = f"{vehicle_id}_log_next_due"
            if log_unique_id not in known_ids:
                known_ids.add(log_unique_id)
                new_entities.append(LogNextDueMaintenanceButton(coordinator, vehicle_id))
            delete_unique_id = f"{vehicle_id}_delete_vehicle"
            if delete_unique_id not in known_ids:
                known_ids.add(delete_unique_id)
                new_entities.append(DeleteVehicleButton(coordinator, vehicle_id))
        if new_entities:
            async_add_entities(new_entities)

    _async_sync_entities()
    remove_listener: Callable[[], None] = coordinator.async_add_listener(_async_sync_entities)
    entry.async_on_unload(remove_listener)


class LogNextDueMaintenanceButton(VehicleMaintenanceCoordinatorEntity, ButtonEntity):
    """Log the next-due maintenance item with current odometer and today's date."""

    def __init__(self, coordinator, vehicle_id: str) -> None:
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_log_next_due"

    @property
    def name(self) -> str:
        return (
            f"{self.vehicle.name} log next due maintenance"
            if self.vehicle is not None
            else f"{self.vehicle_id} log next due maintenance"
        )

    async def async_press(self) -> None:
        if self.vehicle_snapshot is None or self.vehicle is None:
            return
        statuses = list(self.vehicle_snapshot["due_statuses"].values())
        ranked = sorted(
            statuses,
            key=lambda item: (
                0 if item.is_overdue else 1 if item.is_due else 2 if item.is_due_soon else 3,
                item.miles_remaining if item.miles_remaining is not None else 10**9,
            ),
        )
        if not ranked:
            return
        item = ranked[0]
        await self.coordinator.async_log_maintenance(
            {
                "vehicle_id": self.vehicle_id,
                "item_id": item.item_id,
                "date": date.today().isoformat(),
                "odometer": self.vehicle.current_odometer,
                "notes": "Logged from quick action button",
            }
        )

    @property
    def extra_state_attributes(self) -> dict[str, str | int | None]:
        return self.vehicle_attributes


class DeleteVehicleButton(VehicleMaintenanceCoordinatorEntity, ButtonEntity):
    """Delete the tracked vehicle and remove its entities."""

    _attr_icon = "mdi:trash-can"

    def __init__(self, coordinator, vehicle_id: str) -> None:
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_delete_vehicle"

    @property
    def name(self) -> str:
        return (
            f"{self.vehicle.name} delete vehicle"
            if self.vehicle is not None
            else f"{self.vehicle_id} delete vehicle"
        )

    @property
    def extra_state_attributes(self) -> dict[str, str | int | None]:
        return self.vehicle_attributes

    async def async_press(self) -> None:
        await self.coordinator.async_delete_vehicle(self.vehicle_id)
