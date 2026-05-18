"""Constants for the vehicle maintenance integration."""

from __future__ import annotations

DOMAIN = "vehicle_maintenance"
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1

PLATFORMS = ["sensor", "binary_sensor", "button"]

CONF_VEHICLE_ID = "vehicle_id"
CONF_NAME = "name"
CONF_YEAR = "year"
CONF_MAKE = "make"
CONF_MODEL = "model"
CONF_TRIM = "trim"
CONF_ENGINE = "engine"
CONF_VIN = "vin"
CONF_PURCHASE_DATE = "purchase_date"
CONF_PURCHASE_ODOMETER = "purchase_odometer"
CONF_WARRANTY_START_DATE = "warranty_start_date"
CONF_WARRANTY_YEARS = "warranty_years"
CONF_WARRANTY_MILES = "warranty_miles"
CONF_WARRANTY_NAME = "warranty_name"
CONF_CURRENT_ODOMETER = "current_odometer"
CONF_ODOMETER = "odometer"
CONF_ODOMETER_SOURCE_MODE = "odometer_source_mode"
CONF_ODOMETER_ENTITY_ID = "odometer_entity_id"
CONF_TEMPLATE_ID = "template_id"
CONF_ITEM_ID = "item_id"
CONF_ITEM_IDS = "item_ids"
CONF_SCHEDULED_MILEAGE = "scheduled_mileage"
CONF_SERVICE_SOURCE = "service_source"
CONF_VEHICLE_ENTITY_ID = "vehicle_entity_id"
CONF_TITLE = "title"
CONF_CATEGORY = "category"
CONF_AFFECTS_SCHEDULE = "affects_schedule"
CONF_DATE = "date"
CONF_NOTES = "notes"
CONF_COST = "cost"

ODOMETER_MODE_MANUAL = "manual"
ODOMETER_MODE_ENTITY = "entity"

ATTR_SCHEDULE_DISCLAIMER = (
    "Seed template only. Verify maintenance schedule against the manufacturer guidance."
)

SERVICE_ADD_VEHICLE = "add_vehicle"
SERVICE_EDIT_VEHICLE = "edit_vehicle"
SERVICE_DELETE_VEHICLE = "delete_vehicle"
SERVICE_UPDATE_ODOMETER = "update_odometer"
SERVICE_LOG_MAINTENANCE = "log_maintenance"
SERVICE_LOG_SERVICE_VISIT = "log_service_visit"
SERVICE_LOG_SERVICE_RECORD = "log_service_record"

DEFAULT_DUE_SOON_MILES = 500
DEFAULT_OVERDUE_MILES = 0
DELETE_CONFIRMATION_WINDOW_SECONDS = 30
