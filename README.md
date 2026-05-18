# ha-vehicle-maintenance

Home Assistant custom integration for tracking vehicle maintenance against manufacturer schedules, your real service history, and optional ownership details like warranty coverage and subscriptions.

## What it does

- Track vehicles manually or from an existing Home Assistant odometer sensor
- Log scheduled services, one-off maintenance, and ad hoc repairs
- Keep the manufacturer schedule separate from your actual service cadence
- Show due-state entities and a built-in in-HA maintenance panel
- Track purchase date, warranty, subscriptions, and total maintenance cost
- Import and export full vehicle history packages
- Import custom maintenance templates for vehicles that are not built in

Built-in seed templates:

- `2024 Subaru Outback 2.4T`
- `2021 Mazda CX-5 2.5`

## Important disclaimer

The included schedules are `seed templates only`. Verify them against the owner's manual, maintenance booklet, dealer guidance, and your driving conditions before relying on them.

## Quick start

1. Install the integration into `/config/custom_components/vehicle_maintenance`
2. Restart Home Assistant
3. Add `Vehicle Maintenance` in `Settings -> Devices & Services`
4. Open the `Vehicle Maintenance` panel from the sidebar
5. Use `Add vehicle` from the snapshot overflow menu
6. Pick a built-in or imported template if you have one
7. Start logging service from the panel

## Installation

### Standard install

1. Copy `custom_components/vehicle_maintenance` into your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add the integration from `Settings -> Devices & Services`

### Studio Code Server install

From `/config`:

```bash
git clone https://github.com/benleiber/ha-vehicle-maintenance.git
mkdir -p custom_components
cp -R ha-vehicle-maintenance/custom_components/vehicle_maintenance custom_components/
```

Then restart Home Assistant and add the integration.

HACS is not required for the MVP.

## Getting started

The easiest path is to use the built-in panel instead of YAML or Developer Tools.

### Add a vehicle

In the `Vehicle Maintenance` panel:

1. Open the snapshot overflow menu
2. Choose `Add vehicle`
3. Fill in whatever you know now
4. Save it

You can start generic and fill in details later with `Edit vehicle`.

### Log service

The main panel workflow is:

- Select a vehicle
- Review `Current`, `Previous`, and `Next`
- Check off the items that were actually done
- Enter date, odometer, source, and optional cost
- Save the visit

Use the separate `Ad Hoc Service Record` form for things like:

- flat tire repair
- alignment
- windshield replacement
- warranty repair
- diagnostic visits

### Vehicle snapshot

The snapshot shows:

- odometer
- length of ownership
- miles per year
- total maintenance cost
- warranty status
- template in use
- tracked subscriptions like SiriusXM, roadside, or connected services

## Template support

There is now a built-in custom template import path.

From the panel:

1. Open the snapshot overflow menu
2. Choose `Import template`
3. Upload a JSON template package
4. Use that template in `Add vehicle` or `Edit vehicle`

See the detailed template docs:

- [Template import guide](C:/Users/benle/projects/homeassistantcarmaintenance/docs/template_import.md)
- [LLM template prompt](C:/Users/benle/projects/homeassistantcarmaintenance/docs/template_generation_prompt.md)
- [Template example JSON](C:/Users/benle/projects/homeassistantcarmaintenance/examples/template_import_example.json)

## Services and entities

The integration also exposes Home Assistant services and entities if you want to automate around it.

Highlights:

- Vehicle management services
- Odometer update service
- Maintenance logging services
- Odometer sensor
- Next maintenance summary sensor
- Per-item due sensors and due binary sensors
- Warranty sensors and binary sensor

For service examples and more detailed behavior notes, see:

- [Getting started details](C:/Users/benle/projects/homeassistantcarmaintenance/docs/getting_started.md)

## Current status

This project is usable now, but still evolving. The current focus is:

- improving the in-HA UX
- adding better custom template workflows
- growing the library of vehicle templates

## Roadmap

- Better template editing UI
- Notifications and dashboard cards
- HACS metadata and release packaging
- More vehicle templates
- Condition-specific schedule variants
- Smarter flexible-service heuristics
