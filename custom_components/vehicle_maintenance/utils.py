"""Utility helpers."""

from __future__ import annotations


def redact_vin(vin: str | None) -> str | None:
    """Redact a VIN for diagnostics output."""
    if not vin:
        return vin
    if len(vin) <= 4:
        return "***"
    return f"{'*' * (len(vin) - 4)}{vin[-4:]}"
