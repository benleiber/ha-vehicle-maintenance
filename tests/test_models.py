from __future__ import annotations

from datetime import date

from custom_components.vehicle_maintenance.models import (
    MaintenanceItemDefinition,
    ServiceEvent,
    Vehicle,
    VehicleSubscription,
    calculate_subscription_statuses,
    calculate_due_status,
    calculate_total_maintenance_cost,
    calculate_warranty_expiration_date,
    calculate_warranty_miles_remaining,
    get_scheduled_items_for_mileage,
    get_service_windows,
    summarize_due,
    template_from_import,
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


def test_subscription_statuses_support_optional_vehicle_plans() -> None:
    vehicle = Vehicle(
        id="veh1",
        name="Subaru",
        year=2024,
        make="Subaru",
        model="Outback",
        trim="Onyx XT",
        engine="2.4T",
        subscriptions=[
            VehicleSubscription(
                id="sub1",
                name="SiriusXM",
                category="entertainment",
                provider="SiriusXM",
                renewal_date="2026-06-01",
            ),
            VehicleSubscription(
                id="sub2",
                name="Roadside Plus",
                category="roadside",
                provider="AAA",
                renewal_date="2026-05-01",
            ),
        ],
    )

    statuses = calculate_subscription_statuses(vehicle, today=date(2026, 5, 17))

    assert statuses[0].name == "Roadside Plus"
    assert statuses[0].is_active is False
    assert statuses[0].days_remaining == -16
    assert statuses[1].name == "SiriusXM"
    assert statuses[1].is_active is True
    assert statuses[1].days_remaining == 15


def test_total_maintenance_cost_adds_logged_costs_for_vehicle() -> None:
    events = [
        ServiceEvent(
            id="evt1",
            vehicle_id="veh1",
            item_id="engine_oil",
            date="2026-01-01",
            odometer=12000,
            cost=72.50,
        ),
        ServiceEvent(
            id="evt2",
            vehicle_id="veh1",
            item_id=None,
            event_type="service_record",
            title="Flat tire repair",
            date="2026-02-01",
            odometer=12500,
            cost=33.25,
        ),
        ServiceEvent(
            id="evt3",
            vehicle_id="veh2",
            item_id="engine_oil",
            date="2026-03-01",
            odometer=14000,
            cost=10.00,
        ),
    ]

    assert calculate_total_maintenance_cost("veh1", events) == 105.75


def test_template_from_import_normalizes_template_package() -> None:
    template = template_from_import(
        {
            "format": "vehicle_maintenance_template",
            "version": 1,
            "template": {
                "label": "2023 Honda CR-V 1.5T (custom import)",
                "items": [
                    {
                        "name": "Engine Oil",
                        "interval_miles": 7500,
                        "interval_months": 12,
                        "manufacturer_anchor_miles": 7500,
                        "resets_on_service": True,
                    }
                ],
            },
        },
        existing_ids={"2023_honda_cr_v_1_5t_custom_import"},
    )

    assert template.id == "2023_honda_cr_v_1_5t_custom_import_2"
    assert template.label == "2023 Honda CR-V 1.5T (custom import)"
    assert template.items[0].id == "engine_oil"
    assert template.items[0].interval_miles == 7500


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


def test_service_windows_surround_current_odometer() -> None:
    vehicle = Vehicle(
        id="veh1",
        name="Subaru",
        year=2024,
        make="Subaru",
        model="Outback",
        trim="Onyx XT",
        engine="2.4T",
        current_odometer=26000,
        schedule_items=[
            MaintenanceItemDefinition(
                id="engine_oil",
                name="Engine Oil",
                interval_miles=6000,
                manufacturer_anchor_miles=6000,
                resets_on_service=True,
            ),
            MaintenanceItemDefinition(
                id="air_cleaner_element",
                name="Air Cleaner Element",
                interval_miles=30000,
                manufacturer_anchor_miles=30000,
            ),
        ],
    )

    windows = get_service_windows(vehicle)

    assert [window["label"] for window in windows] == ["previous", "current", "next"]
    assert [window["scheduled_mileage"] for window in windows] == [24000, 30000, 36000]
