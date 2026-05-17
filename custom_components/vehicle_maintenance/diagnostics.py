"""Diagnostics support with VIN redaction."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN
from .models import vehicle_to_dict
from .utils import redact_vin


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    vehicles = []
    for vehicle in coordinator.store.vehicles.values():
        payload = vehicle_to_dict(vehicle)
        payload["vin"] = redact_vin(payload.get("vin"))
        vehicles.append(payload)
    return {
        "entry": entry.as_dict(),
        "vehicles": vehicles,
        "service_event_count": len(coordinator.store.service_events),
        "templates": coordinator.get_template_choices(),
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
    device: DeviceEntry,
) -> dict[str, Any]:
    """Return device diagnostics."""
    return await async_get_config_entry_diagnostics(hass, entry)
