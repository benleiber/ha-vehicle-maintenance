"""Vehicle maintenance integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_COST,
    CONF_CURRENT_ODOMETER,
    CONF_DATE,
    CONF_ENGINE,
    CONF_ITEM_ID,
    CONF_MAKE,
    CONF_MODEL,
    CONF_NAME,
    CONF_NOTES,
    CONF_ODOMETER,
    CONF_ODOMETER_ENTITY_ID,
    CONF_ODOMETER_SOURCE_MODE,
    CONF_TEMPLATE_ID,
    CONF_TRIM,
    CONF_VEHICLE_ID,
    CONF_VIN,
    CONF_YEAR,
    DOMAIN,
    PLATFORMS,
    SERVICE_ADD_VEHICLE,
    SERVICE_DELETE_VEHICLE,
    SERVICE_EDIT_VEHICLE,
    SERVICE_LOG_MAINTENANCE,
    SERVICE_UPDATE_ODOMETER,
)
from .coordinator import VehicleMaintenanceCoordinator
from .store import VehicleMaintenanceStore

PLATFORMS_ENUM: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]

ADD_VEHICLE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_YEAR): vol.Coerce(int),
        vol.Required(CONF_MAKE): cv.string,
        vol.Required(CONF_MODEL): cv.string,
        vol.Optional(CONF_TRIM, default=""): cv.string,
        vol.Optional(CONF_ENGINE, default=""): cv.string,
        vol.Optional(CONF_VIN): cv.string,
        vol.Optional(CONF_CURRENT_ODOMETER, default=0): vol.Coerce(int),
        vol.Required(CONF_ODOMETER_SOURCE_MODE): cv.string,
        vol.Optional(CONF_ODOMETER_ENTITY_ID): cv.entity_id,
        vol.Optional(CONF_TEMPLATE_ID): cv.string,
    }
)

EDIT_VEHICLE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_VEHICLE_ID): cv.string,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_YEAR): vol.Coerce(int),
        vol.Optional(CONF_MAKE): cv.string,
        vol.Optional(CONF_MODEL): cv.string,
        vol.Optional(CONF_TRIM): cv.string,
        vol.Optional(CONF_ENGINE): cv.string,
        vol.Optional(CONF_VIN): vol.Any(None, cv.string),
        vol.Optional(CONF_CURRENT_ODOMETER): vol.Coerce(int),
        vol.Optional(CONF_ODOMETER_SOURCE_MODE): cv.string,
        vol.Optional(CONF_ODOMETER_ENTITY_ID): vol.Any(None, cv.entity_id),
        vol.Optional(CONF_TEMPLATE_ID): cv.string,
    }
)

DELETE_VEHICLE_SCHEMA = vol.Schema({vol.Required(CONF_VEHICLE_ID): cv.string})
UPDATE_ODOMETER_SCHEMA = vol.Schema(
    {vol.Required(CONF_VEHICLE_ID): cv.string, vol.Required(CONF_ODOMETER): vol.Coerce(int)}
)
LOG_MAINTENANCE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_VEHICLE_ID): cv.string,
        vol.Required(CONF_ITEM_ID): cv.string,
        vol.Required(CONF_DATE): cv.date,
        vol.Required(CONF_ODOMETER): vol.Coerce(int),
        vol.Optional(CONF_NOTES, default=""): cv.string,
        vol.Optional(CONF_COST): vol.Coerce(float),
    }
)


async def async_setup(hass: HomeAssistant, config: Mapping[str, Any]) -> bool:
    """Set up the integration domain."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    store = VehicleMaintenanceStore(hass)
    coordinator = VehicleMaintenanceCoordinator(hass, store)
    await coordinator.async_initialize()
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_register_services(hass, coordinator)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS_ENUM)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def _async_register_services(
    hass: HomeAssistant, coordinator: VehicleMaintenanceCoordinator
) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_ADD_VEHICLE):
        return

    async def async_add_vehicle(call: ServiceCall) -> None:
        await coordinator.async_add_vehicle(dict(call.data))

    async def async_edit_vehicle(call: ServiceCall) -> None:
        data = dict(call.data)
        vehicle_id = data.pop(CONF_VEHICLE_ID)
        await coordinator.async_edit_vehicle(vehicle_id, data)

    async def async_delete_vehicle(call: ServiceCall) -> None:
        await coordinator.async_delete_vehicle(call.data[CONF_VEHICLE_ID])

    async def async_update_odometer(call: ServiceCall) -> None:
        await coordinator.async_update_odometer(
            call.data[CONF_VEHICLE_ID], call.data[CONF_ODOMETER]
        )

    async def async_log_maintenance(call: ServiceCall) -> None:
        if call.data[CONF_VEHICLE_ID] not in coordinator.store.vehicles:
            msg = f"Unknown vehicle_id {call.data[CONF_VEHICLE_ID]}"
            raise HomeAssistantError(msg)
        data = dict(call.data)
        data[CONF_DATE] = data[CONF_DATE].isoformat()
        await coordinator.async_log_maintenance(data)

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_VEHICLE,
        async_add_vehicle,
        schema=ADD_VEHICLE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_EDIT_VEHICLE,
        async_edit_vehicle,
        schema=EDIT_VEHICLE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_VEHICLE,
        async_delete_vehicle,
        schema=DELETE_VEHICLE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_ODOMETER,
        async_update_odometer,
        schema=UPDATE_ODOMETER_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LOG_MAINTENANCE,
        async_log_maintenance,
        schema=LOG_MAINTENANCE_SCHEMA,
    )
