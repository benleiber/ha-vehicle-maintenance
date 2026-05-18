"""In-Home-Assistant panel and API views for vehicle maintenance."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from aiohttp import web
from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .models import event_to_dict, vehicle_to_dict

PANEL_URL_PATH = "vehicle-maintenance"
PANEL_HTML_PATH = "/api/vehicle_maintenance/panel"
PANEL_DATA_PATH = "/api/vehicle_maintenance/ui-data"
PANEL_ACTION_PATH = "/api/vehicle_maintenance/ui-action"
PANEL_STATIC_PATH = "/api/vehicle_maintenance/static"


async def async_setup_panel(hass: HomeAssistant) -> None:
    """Register panel assets and views once."""
    if hass.data[DOMAIN].get("panel_registered"):
        return

    frontend_path = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_STATIC_PATH, str(frontend_path), False)]
    )
    hass.http.register_view(VehicleMaintenancePanelView(hass))
    hass.http.register_view(VehicleMaintenancePanelDataView(hass))
    hass.http.register_view(VehicleMaintenancePanelActionView(hass))
    async_register_built_in_panel(
        hass,
        "iframe",
        "Vehicle Maintenance",
        "mdi:car-wrench",
        PANEL_URL_PATH,
        {"url": PANEL_HTML_PATH},
        update=True,
    )
    hass.data[DOMAIN]["panel_registered"] = True


def _get_coordinator(hass: HomeAssistant):
    entries = hass.data.get(DOMAIN, {})
    for entry_id, value in entries.items():
        if entry_id == "panel_registered":
            continue
        return value
    return None


def _serialize_vehicle_panel_data(coordinator) -> dict[str, Any]:
    vehicles = []
    for vehicle_id, snapshot in coordinator.data["vehicles"].items():
        vehicle = snapshot["vehicle"]
        schedule_items = [
            {
                **asdict(item),
                "due_status": (
                    None
                    if item.id not in snapshot["due_statuses"]
                    else asdict(snapshot["due_statuses"][item.id])
                ),
            }
            for item in vehicle.schedule_items
        ]
        vehicles.append(
            {
                "vehicle_id": vehicle_id,
                "vehicle": vehicle_to_dict(vehicle),
                "summary": snapshot["summary"],
                "is_due": snapshot["is_due"],
                "warranty_expiration_date": snapshot["warranty_expiration_date"],
                "warranty_miles_remaining": snapshot["warranty_miles_remaining"],
                "schedule_items": schedule_items,
                "recent_service_records": snapshot["recent_service_records"],
                "delete_confirmation_armed": coordinator.is_delete_armed(vehicle_id),
                "delete_confirmation_armed_until": coordinator.get_delete_armed_until(vehicle_id),
            }
        )
    vehicles.sort(key=lambda item: item["vehicle"]["name"].lower())
    return {
        "templates": coordinator.get_template_choices(),
        "vehicles": vehicles,
    }


class VehicleMaintenancePanelView(HomeAssistantView):
    """Serve the panel shell."""

    requires_auth = True
    url = PANEL_HTML_PATH
    name = "api:vehicle_maintenance:panel"

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request: web.Request) -> web.Response:
        html_path = Path(__file__).parent / "frontend" / "panel.html"
        return web.Response(
            text=html_path.read_text(encoding="utf-8"),
            content_type="text/html",
        )


class VehicleMaintenancePanelDataView(HomeAssistantView):
    """Serve UI data."""

    requires_auth = True
    url = PANEL_DATA_PATH
    name = "api:vehicle_maintenance:ui_data"

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request: web.Request) -> web.Response:
        coordinator = _get_coordinator(self.hass)
        if coordinator is None:
            return web.json_response({"vehicles": [], "templates": {}}, status=200)
        return web.json_response(_serialize_vehicle_panel_data(coordinator))


class VehicleMaintenancePanelActionView(HomeAssistantView):
    """Handle panel actions."""

    requires_auth = True
    url = PANEL_ACTION_PATH
    name = "api:vehicle_maintenance:ui_action"

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def post(self, request: web.Request) -> web.Response:
        coordinator = _get_coordinator(self.hass)
        if coordinator is None:
            return web.json_response({"error": "Integration not loaded"}, status=400)

        payload = await request.json()
        action = payload.get("action")

        if action == "log_service_visit":
            await coordinator.async_log_service_visit(payload["data"])
        elif action == "log_maintenance":
            await coordinator.async_log_maintenance(payload["data"])
        elif action == "log_service_record":
            await coordinator.async_log_service_record(payload["data"])
        elif action == "delete_vehicle":
            vehicle_id = payload["data"]["vehicle_id"]
            if not coordinator.is_delete_armed(vehicle_id):
                coordinator.async_arm_delete(vehicle_id)
            else:
                await coordinator.async_delete_vehicle(vehicle_id)
        else:
            return web.json_response({"error": f"Unsupported action {action}"}, status=400)

        return web.json_response(_serialize_vehicle_panel_data(coordinator))
