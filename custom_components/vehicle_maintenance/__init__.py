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
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_AFFECTS_SCHEDULE,
    CONF_CATEGORY,
    CONF_COST,
    CONF_CURRENT_ODOMETER,
    CONF_DATE,
    CONF_ENGINE,
    CONF_ITEM_ID,
    CONF_ITEM_IDS,
    CONF_MAKE,
    CONF_MODEL,
    CONF_NAME,
    CONF_NOTES,
    CONF_ODOMETER,
    CONF_ODOMETER_ENTITY_ID,
    CONF_ODOMETER_SOURCE_MODE,
    CONF_PURCHASE_DATE,
    CONF_PURCHASE_ODOMETER,
    CONF_SCHEDULED_MILEAGE,
    CONF_SERVICE_SOURCE,
    CONF_TEMPLATE_ID,
    CONF_TITLE,
    CONF_TRIM,
    CONF_VEHICLE_ID,
    CONF_VEHICLE_ENTITY_ID,
    CONF_VIN,
    CONF_WARRANTY_MILES,
    CONF_WARRANTY_NAME,
    CONF_WARRANTY_START_DATE,
    CONF_WARRANTY_YEARS,
    CONF_YEAR,
    DOMAIN,
    PLATFORMS,
    SERVICE_ADD_VEHICLE,
    SERVICE_DELETE_VEHICLE,
    SERVICE_EDIT_VEHICLE,
    SERVICE_LOG_MAINTENANCE,
    SERVICE_LOG_SERVICE_RECORD,
    SERVICE_LOG_SERVICE_VISIT,
    SERVICE_UPDATE_ODOMETER,
)
from .coordinator import VehicleMaintenanceCoordinator
from .panel import async_setup_panel
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
        vol.Optional(CONF_PURCHASE_DATE): cv.date,
        vol.Optional(CONF_PURCHASE_ODOMETER): vol.Coerce(int),
        vol.Optional(CONF_WARRANTY_START_DATE): cv.date,
        vol.Optional(CONF_WARRANTY_YEARS): vol.Coerce(int),
        vol.Optional(CONF_WARRANTY_MILES): vol.Coerce(int),
        vol.Optional(CONF_WARRANTY_NAME): cv.string,
        vol.Optional(CONF_CURRENT_ODOMETER, default=0): vol.Coerce(int),
        vol.Required(CONF_ODOMETER_SOURCE_MODE): cv.string,
        vol.Optional(CONF_ODOMETER_ENTITY_ID): cv.entity_id,
        vol.Optional(CONF_TEMPLATE_ID): cv.string,
    }
)

EDIT_VEHICLE_SCHEMA = vol.Schema(
    {
        vol.Exclusive(CONF_VEHICLE_ID, "vehicle_ref"): cv.string,
        vol.Exclusive(CONF_VEHICLE_ENTITY_ID, "vehicle_ref"): cv.entity_id,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_YEAR): vol.Coerce(int),
        vol.Optional(CONF_MAKE): cv.string,
        vol.Optional(CONF_MODEL): cv.string,
        vol.Optional(CONF_TRIM): cv.string,
        vol.Optional(CONF_ENGINE): cv.string,
        vol.Optional(CONF_VIN): vol.Any(None, cv.string),
        vol.Optional(CONF_PURCHASE_DATE): vol.Any(None, cv.date),
        vol.Optional(CONF_PURCHASE_ODOMETER): vol.Any(None, vol.Coerce(int)),
        vol.Optional(CONF_WARRANTY_START_DATE): vol.Any(None, cv.date),
        vol.Optional(CONF_WARRANTY_YEARS): vol.Any(None, vol.Coerce(int)),
        vol.Optional(CONF_WARRANTY_MILES): vol.Any(None, vol.Coerce(int)),
        vol.Optional(CONF_WARRANTY_NAME): vol.Any(None, cv.string),
        vol.Optional(CONF_CURRENT_ODOMETER): vol.Coerce(int),
        vol.Optional(CONF_ODOMETER_SOURCE_MODE): cv.string,
        vol.Optional(CONF_ODOMETER_ENTITY_ID): vol.Any(None, cv.entity_id),
        vol.Optional(CONF_TEMPLATE_ID): cv.string,
    }
)

DELETE_VEHICLE_SCHEMA = vol.Schema(
    {
        vol.Exclusive(CONF_VEHICLE_ID, "vehicle_ref"): cv.string,
        vol.Exclusive(CONF_VEHICLE_ENTITY_ID, "vehicle_ref"): cv.entity_id,
    }
)
UPDATE_ODOMETER_SCHEMA = vol.Schema(
    {
        vol.Exclusive(CONF_VEHICLE_ID, "vehicle_ref"): cv.string,
        vol.Exclusive(CONF_VEHICLE_ENTITY_ID, "vehicle_ref"): cv.entity_id,
        vol.Required(CONF_ODOMETER): vol.Coerce(int),
    }
)
LOG_MAINTENANCE_SCHEMA = vol.Schema(
    {
        vol.Exclusive(CONF_VEHICLE_ID, "vehicle_ref"): cv.string,
        vol.Exclusive(CONF_VEHICLE_ENTITY_ID, "vehicle_ref"): cv.entity_id,
        vol.Required(CONF_ITEM_ID): cv.string,
        vol.Required(CONF_DATE): cv.date,
        vol.Required(CONF_ODOMETER): vol.Coerce(int),
        vol.Optional(CONF_NOTES, default=""): cv.string,
        vol.Optional(CONF_COST): vol.Coerce(float),
        vol.Optional(CONF_SERVICE_SOURCE): cv.string,
    }
)
LOG_SERVICE_VISIT_SCHEMA = vol.Schema(
    {
        vol.Exclusive(CONF_VEHICLE_ID, "vehicle_ref"): cv.string,
        vol.Exclusive(CONF_VEHICLE_ENTITY_ID, "vehicle_ref"): cv.entity_id,
        vol.Required(CONF_DATE): cv.date,
        vol.Required(CONF_ODOMETER): vol.Coerce(int),
        vol.Optional(CONF_SCHEDULED_MILEAGE): vol.Coerce(int),
        vol.Optional(CONF_ITEM_IDS): [cv.string],
        vol.Optional(CONF_NOTES, default=""): cv.string,
        vol.Optional(CONF_COST): vol.Coerce(float),
        vol.Optional(CONF_SERVICE_SOURCE): cv.string,
    }
)
LOG_SERVICE_RECORD_SCHEMA = vol.Schema(
    {
        vol.Exclusive(CONF_VEHICLE_ID, "vehicle_ref"): cv.string,
        vol.Exclusive(CONF_VEHICLE_ENTITY_ID, "vehicle_ref"): cv.entity_id,
        vol.Required(CONF_TITLE): cv.string,
        vol.Required(CONF_DATE): cv.date,
        vol.Required(CONF_ODOMETER): vol.Coerce(int),
        vol.Optional(CONF_CATEGORY): cv.string,
        vol.Optional(CONF_NOTES, default=""): cv.string,
        vol.Optional(CONF_COST): vol.Coerce(float),
        vol.Optional(CONF_SERVICE_SOURCE): cv.string,
        vol.Optional(CONF_AFFECTS_SCHEDULE, default=False): cv.boolean,
        vol.Optional(CONF_ITEM_IDS): [cv.string],
    }
)


def _resolve_vehicle_id(
    hass: HomeAssistant,
    coordinator: VehicleMaintenanceCoordinator,
    call: ServiceCall,
) -> str:
    """Resolve vehicle id from explicit id or selected entity."""
    if CONF_VEHICLE_ID in call.data:
        return call.data[CONF_VEHICLE_ID]
    entity_id = call.data.get(CONF_VEHICLE_ENTITY_ID)
    if entity_id is None:
        msg = "vehicle_id or vehicle_entity_id is required"
        raise HomeAssistantError(msg)
    registry = er.async_get(hass)
    entity_entry = registry.async_get(entity_id)
    if entity_entry is None:
        msg = f"Unknown entity_id {entity_id}"
        raise HomeAssistantError(msg)
    unique_id = entity_entry.unique_id
    for vehicle_id in coordinator.store.vehicles:
        if unique_id.startswith(f"{vehicle_id}_"):
            return vehicle_id
    msg = f"Could not resolve vehicle from entity_id {entity_id}"
    raise HomeAssistantError(msg)


async def async_setup(hass: HomeAssistant, config: Mapping[str, Any]) -> bool:
    """Set up the integration domain."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    store = VehicleMaintenanceStore(hass)
    coordinator = VehicleMaintenanceCoordinator(hass, store, entry.entry_id)
    await coordinator.async_initialize()
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await async_setup_panel(hass)
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
        data = dict(call.data)
        for key in (CONF_PURCHASE_DATE, CONF_WARRANTY_START_DATE):
            if data.get(key) is not None:
                data[key] = data[key].isoformat()
        await coordinator.async_add_vehicle(data)

    async def async_edit_vehicle(call: ServiceCall) -> None:
        data = dict(call.data)
        vehicle_id = _resolve_vehicle_id(hass, coordinator, call)
        data.pop(CONF_VEHICLE_ID, None)
        data.pop(CONF_VEHICLE_ENTITY_ID, None)
        for key in (CONF_PURCHASE_DATE, CONF_WARRANTY_START_DATE):
            if data.get(key) is not None:
                data[key] = data[key].isoformat()
        await coordinator.async_edit_vehicle(vehicle_id, data)

    async def async_delete_vehicle(call: ServiceCall) -> None:
        await coordinator.async_delete_vehicle(_resolve_vehicle_id(hass, coordinator, call))

    async def async_update_odometer(call: ServiceCall) -> None:
        vehicle_id = _resolve_vehicle_id(hass, coordinator, call)
        await coordinator.async_update_odometer(vehicle_id, call.data[CONF_ODOMETER])

    async def async_log_maintenance(call: ServiceCall) -> None:
        vehicle_id = _resolve_vehicle_id(hass, coordinator, call)
        if vehicle_id not in coordinator.store.vehicles:
            msg = f"Unknown vehicle_id {vehicle_id}"
            raise HomeAssistantError(msg)
        data = dict(call.data)
        data.pop(CONF_VEHICLE_ENTITY_ID, None)
        data[CONF_VEHICLE_ID] = vehicle_id
        data[CONF_DATE] = data[CONF_DATE].isoformat()
        await coordinator.async_log_maintenance(data)

    async def async_log_service_visit(call: ServiceCall) -> None:
        vehicle_id = _resolve_vehicle_id(hass, coordinator, call)
        if vehicle_id not in coordinator.store.vehicles:
            msg = f"Unknown vehicle_id {vehicle_id}"
            raise HomeAssistantError(msg)
        if CONF_SCHEDULED_MILEAGE not in call.data and not call.data.get(CONF_ITEM_IDS):
            msg = "Provide scheduled_mileage or item_ids for log_service_visit"
            raise HomeAssistantError(msg)
        data = dict(call.data)
        data.pop(CONF_VEHICLE_ENTITY_ID, None)
        data[CONF_VEHICLE_ID] = vehicle_id
        data[CONF_DATE] = data[CONF_DATE].isoformat()
        await coordinator.async_log_service_visit(data)

    async def async_log_service_record(call: ServiceCall) -> None:
        vehicle_id = _resolve_vehicle_id(hass, coordinator, call)
        if vehicle_id not in coordinator.store.vehicles:
            msg = f"Unknown vehicle_id {vehicle_id}"
            raise HomeAssistantError(msg)
        data = dict(call.data)
        data.pop(CONF_VEHICLE_ENTITY_ID, None)
        data[CONF_VEHICLE_ID] = vehicle_id
        data[CONF_DATE] = data[CONF_DATE].isoformat()
        await coordinator.async_log_service_record(data)

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
    hass.services.async_register(
        DOMAIN,
        SERVICE_LOG_SERVICE_VISIT,
        async_log_service_visit,
        schema=LOG_SERVICE_VISIT_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LOG_SERVICE_RECORD,
        async_log_service_record,
        schema=LOG_SERVICE_RECORD_SCHEMA,
    )
