from __future__ import annotations

from datetime import date

from custom_components.vehicle_maintenance.models import (
    MaintenanceItemDefinition,
    ServiceEvent,
    Vehicle,
    calculate_due_status,
    calculate_warranty_expiration_date,
    calculate_warranty_miles_remaining,
    get_scheduled_items_for_mileage,
    summarize_due,
)


def test_strict_item_uses_manufacturer_anchor_not_oil_cadence() -> None:
    vehicle = Vehicle(
        id="veh1",
        name="Car",
        year=2024,
        make="Subaru",
        model="Outback",
        trim="XT",
        engine="2.4T",
        current_odometer=25500,
    )
    item = MaintenanceItemDefinition(
        id="cvt_fluid",
        name="CVT Fluid",
        interval_miles=30000,
        manufacturer_anchor_miles=30000,
        flexible=False,
        due_soon_threshold_miles=1000,
    )
    oil_events = [
        ServiceEvent(
            id=f"oil{i}",
            vehicle_id="veh1",
            item_id="engine_oil",
            date="2026-01-01",
            odometer=i,
        )
        for i in (5000, 10000, 15000, 20000, 25000)
    ]

    status = calculate_due_status(vehicle, item, oil_events, today=date(2026, 5, 17))

    assert status.next_due_mileage == 30000
    assert status.miles_remaining == 4500
    assert status.basis == "manufacturer_anchor"


def test_flexible_item_uses_last_matching_service_event() -> None:
    vehicle = Vehicle(
        id="veh1",
        name="Car",
        year=2021,
        make="Mazda",
        model="CX-5",
        trim="Touring",
        engine="2.5",
        current_odometer=19500,
    )
    item = MaintenanceItemDefinition(
        id="engine_oil",
        name="Engine Oil",
        interval_miles=7500,
        flexible=True,
    )
    events = [
        ServiceEvent(
            id="evt1",
            vehicle_id="veh1",
            item_id="engine_oil",
            date="2026-02-01",
            odometer=14000,
        )
    ]

    status = calculate_due_status(vehicle, item, events, today=date(2026, 5, 17))

    assert status.next_due_mileage == 21500
    assert status.miles_remaining == 2000
    assert status.basis == "last_service_event"


def test_summary_prefers_due_or_overdue_items() -> None:
    vehicle = Vehicle(
        id="veh1",
        name="Car",
        year=2021,
        make="Mazda",
        model="CX-5",
        trim="Touring",
        engine="2.5",
        current_odometer=30010,
    )
    overdue_item = MaintenanceItemDefinition(
        id="brakes",
        name="Brake Inspection",
        interval_miles=30000,
        manufacturer_anchor_miles=30000,
        flexible=False,
    )
    later_item = MaintenanceItemDefinition(
        id="oil",
        name="Oil",
        interval_miles=37500,
        manufacturer_anchor_miles=37500,
        flexible=False,
    )
    statuses = [
        calculate_due_status(vehicle, overdue_item, [], today=date(2026, 5, 17)),
        calculate_due_status(vehicle, later_item, [], today=date(2026, 5, 17)),
    ]

    assert summarize_due(statuses) == "Brake Inspection overdue"


def test_scheduled_service_visit_expands_matching_items() -> None:
    vehicle = Vehicle(
        id="veh1",
        name="Subaru",
        year=2024,
        make="Subaru",
        model="Outback",
        trim="Onyx XT",
        engine="2.4T",
        schedule_items=[
            MaintenanceItemDefinition(
                id="engine_oil",
                name="Engine Oil",
                interval_miles=6000,
                interval_months=6,
                manufacturer_anchor_miles=6000,
                resets_on_service=True,
            ),
            MaintenanceItemDefinition(
                id="air_cleaner_element",
                name="Air Cleaner Element",
                interval_miles=30000,
                interval_months=30,
                manufacturer_anchor_miles=30000,
            ),
        ],
    )

    items = get_scheduled_items_for_mileage(vehicle, 30000)

    assert [item.id for item in items] == ["engine_oil", "air_cleaner_element"]


def test_warranty_projection_uses_purchase_and_mileage() -> None:
    vehicle = Vehicle(
        id="veh1",
        name="Subaru",
        year=2024,
        make="Subaru",
        model="Outback",
        trim="Onyx XT",
        engine="2.4T",
        current_odometer=26000,
        purchase_date="2024-06-01",
        warranty_start_date="2024-06-01",
        warranty_years=8,
        warranty_miles=120000,
    )

    assert calculate_warranty_expiration_date(vehicle) == "2032-05-30"
    assert calculate_warranty_miles_remaining(vehicle) == 94000


def test_ad_hoc_service_record_does_not_reset_schedule() -> None:
    vehicle = Vehicle(
        id="veh1",
        name="Car",
        year=2024,
        make="Subaru",
        model="Outback",
        trim="XT",
        engine="2.4T",
        current_odometer=26000,
    )
    item = MaintenanceItemDefinition(
        id="engine_oil",
        name="Engine Oil",
        interval_miles=6000,
        interval_months=6,
        manufacturer_anchor_miles=6000,
        resets_on_service=True,
    )
    events = [
        ServiceEvent(
            id="evt1",
            vehicle_id="veh1",
            item_id=None,
            title="Flat tire repair",
            category="tire",
            event_type="service_record",
            affects_schedule=False,
            date="2026-05-17",
            odometer=25990,
        )
    ]

    status = calculate_due_status(vehicle, item, events, today=date(2026, 5, 17))

    assert status.next_due_mileage == 30000
    assert status.basis == "manufacturer_anchor"
