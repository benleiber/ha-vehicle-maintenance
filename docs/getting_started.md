# Getting Started

This page covers the practical details that are useful after the initial install.

## Add a vehicle

Preferred path:

1. Open the `Vehicle Maintenance` sidebar panel
2. Open the snapshot overflow menu
3. Choose `Add vehicle`
4. Fill in the vehicle details
5. Save

Important fields:

- `name`: what you want to call the vehicle in Home Assistant
- `odometer_source_mode`: `manual` or `entity`
- `odometer_entity_id`: required when using entity mode
- `template_id`: optional, but recommended when you have a matching schedule
- `purchase_date` and `purchase_odometer`: used for ownership length and miles/year
- `warranty_*`: used for warranty tracking

You can leave some details blank and come back later with `Edit vehicle`.

## Log a service visit

Use the checklist workflow in the panel:

1. Select a vehicle
2. Review `Current`, `Previous`, and `Next`
3. Check the items actually completed
4. Enter:
   - date
   - odometer
   - source
   - optional cost
   - optional notes
5. Save the visit

This is the best flow for:

- dealer milestone services
- your own oil changes
- partial visits where only some scheduled items were done

## Log ad hoc work

Use `Ad Hoc Service Record` for work that belongs in the history but should not automatically reset scheduled maintenance:

- flat tire repair
- alignment
- windshield replacement
- warranty repair
- diagnostic visit

## Snapshot metrics

The vehicle snapshot currently shows:

- `Odometer`
- `Length of ownership`
- `Miles per year`
- `Total maintenance cost`
- `Warranty miles remaining`
- `Warranty expiration`
- `Template`
- `Tracked subscriptions`

`Miles per year` uses `purchase_date` and, when available, `purchase_odometer`.

## Services

If you prefer Home Assistant services or automations, the main services are:

- `vehicle_maintenance.add_vehicle`
- `vehicle_maintenance.edit_vehicle`
- `vehicle_maintenance.delete_vehicle`
- `vehicle_maintenance.update_odometer`
- `vehicle_maintenance.log_maintenance`
- `vehicle_maintenance.log_service_visit`
- `vehicle_maintenance.log_service_record`

## Example service payloads

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

### Entity-backed vehicle

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

### Log a one-off maintenance item

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

## Notes on schedule behavior

The integration keeps the manufacturer schedule separate from your actual service cadence.

Examples:

- Early oil changes reset oil without automatically marking unrelated 30k items done
- Manufacturer milestone items can stay anchored to their own interval
- A full scheduled visit can be logged as one grouped service event
