"""Seed maintenance templates that require user verification."""

from __future__ import annotations

from typing import Any

from .const import ATTR_SCHEDULE_DISCLAIMER

SEED_TEMPLATES: dict[str, dict[str, Any]] = {
    "subaru_outback_2024_24t_seed": {
        "id": "subaru_outback_2024_24t_seed",
        "label": "2024 Subaru Outback 2.4T (seed template)",
        "disclaimer": ATTR_SCHEDULE_DISCLAIMER,
        "items": [
            {
                "id": "engine_oil",
                "name": "Engine Oil",
                "interval_miles": 6000,
                "interval_months": 6,
                "manufacturer_anchor_miles": 6000,
                "flexible": False,
                "due_soon_threshold_miles": 500,
                "overdue_threshold_miles": 0,
            },
            {
                "id": "tire_rotation",
                "name": "Tire Rotation",
                "interval_miles": 6000,
                "interval_months": 6,
                "manufacturer_anchor_miles": 6000,
                "flexible": False,
                "due_soon_threshold_miles": 500,
                "overdue_threshold_miles": 0,
            },
            {
                "id": "cvt_fluid",
                "name": "CVT Fluid",
                "interval_miles": 30000,
                "interval_months": None,
                "manufacturer_anchor_miles": 30000,
                "flexible": False,
                "due_soon_threshold_miles": 1000,
                "overdue_threshold_miles": 0,
            }
        ],
    },
    "mazda_cx5_2021_25_seed": {
        "id": "mazda_cx5_2021_25_seed",
        "label": "2021 Mazda CX-5 2.5 (seed template)",
        "disclaimer": ATTR_SCHEDULE_DISCLAIMER,
        "items": [
            {
                "id": "engine_oil",
                "name": "Engine Oil",
                "interval_miles": 7500,
                "interval_months": 12,
                "manufacturer_anchor_miles": 7500,
                "flexible": True,
                "due_soon_threshold_miles": 500,
                "overdue_threshold_miles": 0,
            },
            {
                "id": "tire_rotation",
                "name": "Tire Rotation",
                "interval_miles": 7500,
                "interval_months": 12,
                "manufacturer_anchor_miles": 7500,
                "flexible": False,
                "due_soon_threshold_miles": 500,
                "overdue_threshold_miles": 0,
            },
            {
                "id": "brake_inspection",
                "name": "Brake Inspection",
                "interval_miles": 15000,
                "interval_months": 12,
                "manufacturer_anchor_miles": 15000,
                "flexible": False,
                "due_soon_threshold_miles": 1000,
                "overdue_threshold_miles": 0,
            }
        ],
    },
}
