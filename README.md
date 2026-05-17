# ha-vehicle-maintenance

Home Assistant custom integration for tracking vehicle maintenance against seed manufacturer schedules and your own logged service history.

This MVP supports:

- Vehicles tracked manually or from an existing Home Assistant odometer sensor
- Storage-backed vehicles and maintenance history
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
  notes: Changed oil and filter
  cost: 72.50
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
- Overall maintenance due binary sensor
- Per-maintenance-item due mileage sensors
- Per-maintenance-item due date sensors
- Per-maintenance-item due binary sensors
- A convenience button to log the next-due item using today's date and the current odometer

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

- If oil changes are logged every 5,000 miles by preference
- But another item is seeded at 30,000 miles
- The 30,000-mile item continues tracking from its own anchor and service history
- It does not advance merely because five oil changes were logged
