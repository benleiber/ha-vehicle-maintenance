# Template Import Guide

Use this when your vehicle is not covered by one of the built-in seed templates.

## What a template does

A maintenance template defines:

- the maintenance items for a vehicle
- the manufacturer mileage anchors
- the repeat intervals in miles and months
- whether an item should reset from the last service event or stay anchored to the manual milestone

Imported templates are stored persistently and become available in the vehicle form.

## Import flow

1. Open the `Vehicle Maintenance` panel
2. Open the snapshot overflow menu
3. Choose `Import template`
4. Upload a JSON file in the template package format
5. Open `Add vehicle` or `Edit vehicle`
6. Choose the imported template from the `Template` dropdown

## JSON package format

The import accepts either:

- a full package with `format`, `version`, and `template`
- or a raw template object

Preferred package format:

```json
{
  "format": "vehicle_maintenance_template",
  "version": 1,
  "template": {
    "id": "2023_honda_cr_v_15t_custom",
    "label": "2023 Honda CR-V 1.5T (custom import)",
    "disclaimer": "Seed template only. Verify maintenance schedule against the manufacturer guidance.",
    "items": [
      {
        "id": "engine_oil",
        "name": "Engine Oil",
        "interval_miles": 7500,
        "interval_months": 12,
        "manufacturer_anchor_miles": 7500,
        "flexible": false,
        "resets_on_service": true,
        "due_soon_threshold_miles": 500,
        "overdue_threshold_miles": 0
      }
    ]
  }
}
```

Reference example:

- [template_import_example.json](C:/Users/benle/projects/homeassistantcarmaintenance/examples/template_import_example.json)

## Field meanings

### Template fields

- `id`: stable template identifier; if omitted or duplicated, the import flow normalizes it
- `label`: user-facing vehicle template name
- `disclaimer`: note shown with the template
- `items`: list of maintenance items

### Item fields

- `id`: stable lowercase snake_case item ID
- `name`: user-facing maintenance item label
- `interval_miles`: recurring interval in miles, or `null`
- `interval_months`: recurring interval in months, or `null`
- `manufacturer_anchor_miles`: first mileage where the item appears in the manual
- `flexible`: usually `false`
- `resets_on_service`: whether doing the item resets its next due point
- `due_soon_threshold_miles`: when to start flagging the item as due soon
- `overdue_threshold_miles`: usually `0`

## Practical guidance

Use `resets_on_service: true` for:

- oil
- oil filter
- air filters
- spark plugs
- tire rotations
- inspection items that should follow the last time you actually performed them

Use `resets_on_service: false` for:

- milestone-bound items you want to keep near the manual anchor
- fluids or services where doing another item early should not drag the milestone forward

## Building a template with an LLM

Use:

- [template_generation_prompt.md](C:/Users/benle/projects/homeassistantcarmaintenance/docs/template_generation_prompt.md)

Workflow:

1. Copy the maintenance table text from the manual, PDF, or service booklet
2. Paste it into the LLM along with the prompt
3. Save the JSON output as a file
4. Compare it to the example JSON
5. Import it through the panel

## Validation notes

The import path checks that:

- the template has a non-empty label
- the template has at least one item
- each item has a name
- duplicate item IDs are rejected

If the template ID already exists, the import path creates a suffixed ID automatically.
