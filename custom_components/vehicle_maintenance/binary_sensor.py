"""Binary sensors for maintenance due state."""

from __future__ import annotations

from typing import Callable

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import VehicleMaintenanceCoordinatorEntity
from .models import due_status_to_dict


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    known_ids: set[str] = set()

    @callback
    def _async_sync_entities() -> None:
        new_entities: list[BinarySensorEntity] = []
        for vehicle_id, vehicle_data in coordinator.data["vehicles"].items():
            overall_id = f"{vehicle_id}_maintenance_due"
            if overall_id not in known_ids:
                known_ids.add(overall_id)
                new_entities.append(VehicleMaintenanceDueBinarySensor(coordinator, vehicle_id))
            for item_id in vehicle_data["due_statuses"]:
                item_unique_id = f"{vehicle_id}_{item_id}_due"
                if item_unique_id not in known_ids:
                    known_ids.add(item_unique_id)
                    new_entities.append(VehicleItemDueBinarySensor(coordinator, vehicle_id, item_id))
        if new_entities:
            async_add_entities(new_entities)

    _async_sync_entities()
    remove_listener: Callable[[], None] = coordinator.async_add_listener(_async_sync_entities)
    entry.async_on_unload(remove_listener)


class VehicleMaintenanceDueBinarySensor(VehicleMaintenanceCoordinatorEntity, BinarySensorEntity):
    """Overall due sensor."""

    def __init__(self, coordinator, vehicle_id: str) -> None:
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_maintenance_due"

    @property
    def name(self) -> str:
        return (
            f"{self.vehicle.name} maintenance due"
            if self.vehicle is not None
            else f"{self.vehicle_id} maintenance due"
        )

    @property
    def is_on(self) -> bool:
        return False if self.vehicle_snapshot is None else self.vehicle_snapshot["is_due"]


class VehicleItemDueBinarySensor(VehicleMaintenanceCoordinatorEntity, BinarySensorEntity):
    """Per-item due sensor."""

    def __init__(self, coordinator, vehicle_id: str, item_id: str) -> None:
        super().__init__(coordinator, vehicle_id)
        self.item_id = item_id
        self._attr_unique_id = f"{vehicle_id}_{item_id}_due"

    @property
    def name(self) -> str:
        if self.vehicle_snapshot is None or self.item_id not in self.vehicle_snapshot["due_statuses"]:
            return f"{self.vehicle_id} {self.item_id} due"
        status = self.vehicle_snapshot["due_statuses"][self.item_id]
        return f"{self.vehicle.name} {status.name} due"

    @property
    def is_on(self) -> bool:
        if self.vehicle_snapshot is None:
            return False
        status = self.vehicle_snapshot["due_statuses"].get(self.item_id)
        return False if status is None else status.is_due

    @property
    def extra_state_attributes(self) -> dict:
        if self.vehicle_snapshot is None:
            return self.vehicle_attributes
        status = self.vehicle_snapshot["due_statuses"].get(self.item_id)
        return self.vehicle_attributes if status is None else {
            **self.vehicle_attributes,
            **due_status_to_dict(status),
        }
