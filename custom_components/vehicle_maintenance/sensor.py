"""Sensors for vehicle maintenance."""

from __future__ import annotations

from datetime import date
from typing import Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
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
    """Set up sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    known_ids: set[str] = set()

    @callback
    def _async_sync_entities() -> None:
        new_entities: list[SensorEntity] = []
        for vehicle_id, vehicle_data in coordinator.data["vehicles"].items():
            vehicle = vehicle_data["vehicle"]
            odometer_id = f"{vehicle_id}_odometer"
            if odometer_id not in known_ids:
                known_ids.add(odometer_id)
                new_entities.append(VehicleOdometerSensor(coordinator, vehicle_id))
            summary_id = f"{vehicle_id}_next_maintenance_summary"
            if summary_id not in known_ids:
                known_ids.add(summary_id)
                new_entities.append(VehicleNextMaintenanceSummarySensor(coordinator, vehicle_id))
            for item_id in vehicle_data["due_statuses"]:
                mileage_id = f"{vehicle_id}_{item_id}_due_mileage"
                if mileage_id not in known_ids:
                    known_ids.add(mileage_id)
                    new_entities.append(VehicleItemDueMileageSensor(coordinator, vehicle_id, item_id))
                date_id = f"{vehicle_id}_{item_id}_due_date"
                if date_id not in known_ids:
                    known_ids.add(date_id)
                    new_entities.append(VehicleItemDueDateSensor(coordinator, vehicle_id, item_id))
        if new_entities:
            async_add_entities(new_entities)

    _async_sync_entities()
    remove_listener: Callable[[], None] = coordinator.async_add_listener(_async_sync_entities)
    entry.async_on_unload(remove_listener)


class VehicleOdometerSensor(VehicleMaintenanceCoordinatorEntity, SensorEntity):
    """Vehicle odometer sensor."""

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.MILES

    def __init__(self, coordinator, vehicle_id: str) -> None:
        super().__init__(coordinator, vehicle_id)
        self._attr_translation_key = "odometer"
        self._attr_unique_id = f"{vehicle_id}_odometer"

    @property
    def name(self) -> str:
        return (
            f"{self.vehicle.name} odometer" if self.vehicle is not None else f"{self.vehicle_id} odometer"
        )

    @property
    def native_value(self) -> int:
        return 0 if self.vehicle is None else self.vehicle.current_odometer

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        if self.vehicle is None:
            return self.vehicle_attributes
        return {
            **self.vehicle_attributes,
            "schedule_disclaimer": self.vehicle.template_disclaimer,
            "odometer_source_mode": self.vehicle.odometer_source_mode,
            "odometer_entity_id": self.vehicle.odometer_entity_id,
        }


class VehicleNextMaintenanceSummarySensor(VehicleMaintenanceCoordinatorEntity, SensorEntity):
    """Summary sensor."""

    def __init__(self, coordinator, vehicle_id: str) -> None:
        super().__init__(coordinator, vehicle_id)
        self._attr_translation_key = "next_maintenance_summary"
        self._attr_unique_id = f"{vehicle_id}_next_maintenance_summary"

    @property
    def name(self) -> str:
        return (
            f"{self.vehicle.name} next maintenance"
            if self.vehicle is not None
            else f"{self.vehicle_id} next maintenance"
        )

    @property
    def native_value(self) -> str:
        return "Vehicle not found" if self.vehicle_snapshot is None else self.vehicle_snapshot["summary"]

    @property
    def extra_state_attributes(self) -> dict:
        return self.vehicle_attributes if self.vehicle_snapshot is None else {
            **self.vehicle_attributes,
            "items": {
                item_id: due_status_to_dict(status)
                for item_id, status in self.vehicle_snapshot["due_statuses"].items()
            },
            "schedule_disclaimer": self.vehicle.template_disclaimer,
        }


class VehicleItemDueMileageSensor(VehicleMaintenanceCoordinatorEntity, SensorEntity):
    """Per-item due mileage sensor."""

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.MILES

    def __init__(self, coordinator, vehicle_id: str, item_id: str) -> None:
        super().__init__(coordinator, vehicle_id)
        self.item_id = item_id
        self._attr_unique_id = f"{vehicle_id}_{item_id}_due_mileage"

    @property
    def entity_description(self) -> SensorEntityDescription:
        return SensorEntityDescription(key=f"{self.item_id}_due_mileage")

    @property
    def name(self) -> str:
        if self.vehicle_snapshot is None or self.item_id not in self.vehicle_snapshot["due_statuses"]:
            return f"{self.vehicle_id} {self.item_id} due mileage"
        status = self.vehicle_snapshot["due_statuses"][self.item_id]
        return f"{self.vehicle.name} {status.name} due mileage"

    @property
    def native_value(self) -> int | None:
        if self.vehicle_snapshot is None:
            return None
        status = self.vehicle_snapshot["due_statuses"].get(self.item_id)
        return None if status is None else status.next_due_mileage

    @property
    def extra_state_attributes(self) -> dict:
        if self.vehicle_snapshot is None:
            return self.vehicle_attributes
        status = self.vehicle_snapshot["due_statuses"].get(self.item_id)
        return self.vehicle_attributes if status is None else {
            **self.vehicle_attributes,
            **due_status_to_dict(status),
        }


class VehicleItemDueDateSensor(VehicleMaintenanceCoordinatorEntity, SensorEntity):
    """Per-item due date sensor."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator, vehicle_id: str, item_id: str) -> None:
        super().__init__(coordinator, vehicle_id)
        self.item_id = item_id
        self._attr_unique_id = f"{vehicle_id}_{item_id}_due_date"

    @property
    def name(self) -> str:
        if self.vehicle_snapshot is None or self.item_id not in self.vehicle_snapshot["due_statuses"]:
            return f"{self.vehicle_id} {self.item_id} due date"
        status = self.vehicle_snapshot["due_statuses"][self.item_id]
        return f"{self.vehicle.name} {status.name} due date"

    @property
    def native_value(self) -> date | None:
        if self.vehicle_snapshot is None:
            return None
        status = self.vehicle_snapshot["due_statuses"].get(self.item_id)
        value = None if status is None else status.next_due_date
        return date.fromisoformat(value) if value else None

    @property
    def extra_state_attributes(self) -> dict:
        if self.vehicle_snapshot is None:
            return self.vehicle_attributes
        status = self.vehicle_snapshot["due_statuses"].get(self.item_id)
        return self.vehicle_attributes if status is None else {
            **self.vehicle_attributes,
            **due_status_to_dict(status),
        }
