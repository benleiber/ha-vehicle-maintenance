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
            unique_id = f"{vehicle_id}_log_next_due"
            if unique_id in known_ids:
                continue
            known_ids.add(unique_id)
            new_entities.append(LogNextDueMaintenanceButton(coordinator, vehicle_id))
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
