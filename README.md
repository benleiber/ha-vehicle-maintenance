# ha-vehicle-maintenance

Home Assistant custom integration for tracking vehicle maintenance against seed manufacturer schedules and your own logged service history.

This MVP supports:

- Vehicles tracked manually or from an existing Home Assistant odometer sensor
- Storage-backed vehicles and maintenance history
- Purchase metadata and warranty tracking
- One-off maintenance logging and full scheduled service visit logging
- Ad hoc service records such as flat tire repair, alignment, glass repair, warranty work, and diagnostics
- A built-in Home Assistant panel for vehicle/service logging without YAML
- Seed maintenance templates for:
  - 2024 Subaru Outback 2.4T
  - 2021 Mazda CX-5 2.5
- Services for odometer updates, vehicle management, and maintenance logging
- Sensors and binary sensors for due-state visibility

## Important disclaimer

The included schedules are **seed templates only** and must be verified against the owner's manual, maintenance booklet, dealer guidance, and your specific driving conditions. This project does **not** claim the included schedules are exact manufacturer recommendations.

## Installation

1. Copy this repository's `custom_components/vehicle_maintenance` folder into your Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Go to `Settings -> Devices & Services -> Add Integration`.
4. Add `Vehicle Maintenance`.
5. Use the provided services to add vehicles and log maintenance.
6. Open the `Vehicle Maintenance` panel from the Home Assistant sidebar for the no-YAML logging UI.

HACS is not required for the MVP.

## Install from Studio Code Server

If you use the Studio Code Server add-on in Home Assistant, you can pull this repo directly onto your instance:

1. Open the Studio Code Server add-on.
2. Open a terminal in the Home Assistant config directory.
3. Clone the repository:

```bash
git clone https://github.com/benleiber/ha-vehicle-maintenance.git
```

4. Create the `custom_components` directory if it does not already exist:

```bash
mkdir -p custom_components
```

5. Copy the integration into Home Assistant's custom components folder:

```bash
cp -R ha-vehicle-maintenance/custom_components/vehicle_maintenance custom_components/
```

6. Restart Home Assistant.
7. In Home Assistant, go to `Settings -> Devices & Services -> Add Integration`.
8. Search for `Vehicle Maintenance` and add it.

If you prefer, you can also open the cloned repo in Studio Code Server and drag the `vehicle_maintenance` folder into `/config/custom_components/`.

## Example vehicles

### Manual odometer vehicle

```yaml
service: vehicle_maintenance.add_vehicle
data:
  name: Family Wagon
  year: 2024
  make: Subaru
  model: Outback
  trim: Onyx XT
  engine: 2.4T
  purchase_date: "2024-06-01"
  purchase_odometer: 14
  warranty_start_date: "2024-06-01"
  warranty_years: 8
  warranty_miles: 120000
  warranty_name: Subaru Added Security
  current_odometer: 18250
  odometer_source_mode: manual
  template_id: subaru_outback_2024_24t_seed
```

### Entity-backed odometer vehicle

```yaml
service: vehicle_maintenance.add_vehicle
data:
  name: Daily Driver
  year: 2021
  make: Mazda
  model: CX-5
  trim: Touring
  engine: 2.5
  odometer_source_mode: entity
  odometer_entity_id: sensor.cx5_odometer
  template_id: mazda_cx5_2021_25_seed
```

## Example services

### Update manual odometer

```yaml
service: vehicle_maintenance.update_odometer
data:
  vehicle_id: YOUR_VEHICLE_ID
  odometer: 19442
```

### Log maintenance

```yaml
service: vehicle_maintenance.log_maintenance
data:
  vehicle_id: YOUR_VEHICLE_ID
  item_id: engine_oil
  date: "2026-05-17"
  odometer: 19442
  service_source: self
  notes: Changed oil and filter
  cost: 72.50
```

### Log a complete scheduled visit

This is useful when a dealer completed the whole 6k, 12k, 24k, or 30k visit and you want all matching schedule items recorded at once.

```yaml
service: vehicle_maintenance.log_service_visit
data:
  vehicle_id: YOUR_VEHICLE_ID
  date: "2025-11-01"
  odometer: 24012
  scheduled_mileage: 24000
  service_source: dealer
  notes: Complete dealer 24k service
```

### Log a custom multi-item visit

```yaml
service: vehicle_maintenance.log_service_visit
data:
  vehicle_id: YOUR_VEHICLE_ID
  date: "2026-05-17"
  odometer: 26000
  item_ids:
    - engine_oil
    - engine_oil_filter
  service_source: self
  notes: Early oil change before 30k
```

### Log an ad hoc service record

Use this for repairs or visits that should be in the vehicle history but should not reset the maintenance schedule.

```yaml
service: vehicle_maintenance.log_service_record
data:
  vehicle_id: YOUR_VEHICLE_ID
  title: Flat tire repair
  category: tire
  date: "2026-05-18"
  odometer: 26102
  service_source: Discount Tire
  notes: Patched puncture in rear tire
  cost: 28.00
```

### Edit a vehicle

```yaml
service: vehicle_maintenance.edit_vehicle
data:
  vehicle_id: YOUR_VEHICLE_ID
  current_odometer: 20010
  odometer_source_mode: manual
```

### Delete a vehicle

```yaml
service: vehicle_maintenance.delete_vehicle
data:
  vehicle_id: YOUR_VEHICLE_ID
```

## Entities

Per vehicle the integration exposes:

- Odometer sensor
- Next maintenance summary sensor
- Warranty miles remaining sensor
- Warranty expiration date sensor
- Overall maintenance due binary sensor
- Warranty active binary sensor
- Per-maintenance-item due mileage sensors
- Per-maintenance-item due date sensors
- Per-maintenance-item due binary sensors
- A convenience button to log the next-due item using today's date and the current odometer
- A sidebar panel for logging scheduled visits, one-off maintenance, and ad hoc service records

## In-HA UI

After installing and restarting Home Assistant, the integration registers a `Vehicle Maintenance` panel in the sidebar.

From that panel you can:

- Pick a vehicle from a dropdown
- Log a complete scheduled visit by mileage milestone
- Log a one-off maintenance item such as an early oil change
- Log an ad hoc service record such as a flat tire repair
- Review recent service history
- Delete a vehicle with confirmation

## Dashboard use

If you want a dashboard entry point for less technical users, add an `Iframe` card to a Home Assistant dashboard and point it at:

```text
/api/vehicle_maintenance/panel
```

That gives you a dashboard tile that opens the same maintenance workflow UI without needing Developer Tools.

## Roadmap

- Full options flow and config-entry UI vehicle management
- Better template editing UI
- Notifications and dashboard cards
- Import/export history
- HACS metadata and release packaging
- More vehicle templates and condition-specific schedules
- Smarter flexible-service heuristics

## Notes on schedule behavior

The integration keeps the seed manufacturer schedule separate from the user's actual service cadence.

Example:

- If oil changes are logged every 5,000 or 6,000 miles by preference, oil can reset from the last oil event
- But another item seeded at 30,000 miles remains independent
- Logging oil early does not mark unrelated 30,000-mile items complete
- A complete scheduled visit can be logged in one action when the whole manufacturer interval was performed
