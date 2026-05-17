from __future__ import annotations

from custom_components.vehicle_maintenance.utils import redact_vin


def test_redact_vin_keeps_only_last_four() -> None:
    assert redact_vin("4S4BTGUD6R3123456") == "*************3456"
    assert redact_vin("1234") == "***"
