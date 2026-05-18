"""Shared entity helpers."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import VehicleMaintenanceCoordinator


class VehicleMaintenanceCoordinatorEntity(CoordinatorEntity[VehicleMaintenanceCoordinator]):
    """Base coordinator entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: VehicleMaintenanceCoordinator, vehicle_id: str) -> None:
        super().__init__(coordinator)
        self.vehicle_id = vehicle_id

    @property
    def vehicle_snapshot(self) -> dict | None:
        """Return cached vehicle snapshot."""
        return self.coordinator.data["vehicles"].get(self.vehicle_id)

    @property
    def vehicle(self):
        """Return the tracked vehicle."""
        snapshot = self.vehicle_snapshot
        return None if snapshot is None else snapshot["vehicle"]

    @property
    def vehicle_attributes(self) -> dict[str, str | int | None]:
        """Return common vehicle metadata for entity attributes."""
        if self.vehicle is None:
            return {"vehicle_id": self.vehicle_id}
        return {
            "vehicle_id": self.vehicle_id,
            "vehicle_name": self.vehicle.name,
            "vehicle_year": self.vehicle.year,
            "vehicle_make": self.vehicle.make,
            "vehicle_model": self.vehicle.model,
            "vehicle_trim": self.vehicle.trim,
            "vehicle_engine": self.vehicle.engine,
            "purchase_date": self.vehicle.purchase_date,
            "purchase_odometer": self.vehicle.purchase_odometer,
            "warranty_start_date": self.vehicle.warranty_start_date,
            "warranty_years": self.vehicle.warranty_years,
            "warranty_miles": self.vehicle.warranty_miles,
            "warranty_name": self.vehicle.warranty_name,
            "template_id": self.vehicle.template_id,
        }

    @property
    def available(self) -> bool:
        """Return availability based on coordinator data."""
        return super().available and self.vehicle_snapshot is not None

    @property
    def device_info(self) -> DeviceInfo | None:
        """Group entities by vehicle."""
        if self.vehicle is None:
            return None
        return DeviceInfo(
            identifiers={("vehicle_maintenance", self.vehicle_id)},
            name=self.vehicle.name,
            manufacturer=self.vehicle.make,
            model=f"{self.vehicle.year} {self.vehicle.model}",
        )
