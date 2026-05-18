# Template Generation Prompt

Use this prompt with an LLM after pasting or attaching a vehicle maintenance schedule:

```text
Convert the attached vehicle maintenance schedule into a JSON object for the Home Assistant `ha-vehicle-maintenance` integration.

Return JSON only. Do not include markdown fences. Do not explain anything outside the JSON.

Output format:
{
  "format": "vehicle_maintenance_template",
  "version": 1,
  "template": {
    "id": "lowercase_unique_template_id",
    "label": "Human readable vehicle label",
    "disclaimer": "Seed template only. Verify maintenance schedule against the manufacturer guidance.",
    "items": [
      {
        "id": "lowercase_snake_case_item_id",
        "name": "Exact or near-exact maintenance item label",
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

Rules:
1. Preserve the manufacturer schedule structure. Do not invent maintenance items that are not present.
2. Use one item object per scheduled maintenance line item.
3. `id` values must be lowercase snake_case and stable.
4. `label` should include year, make, model, engine or trim when helpful.
5. Set `manufacturer_anchor_miles` to the first mileage when the item appears in the schedule.
6. Set `interval_miles` to the repeat interval in miles when it is clear. If the schedule is mileage-only but irregular, choose the recurring interval only when the pattern is explicit.
7. Set `interval_months` to the repeat interval in months when it is clear. Use `null` when the source does not define a month interval.
8. For regular replace/service items like oil, filters, plugs, and tire rotations, set `resets_on_service` to `true`.
9. For inspection items, set `resets_on_service` to `true` unless the schedule clearly anchors the inspection to a fixed milestone regardless of when it was last done.
10. For milestone-bound items that should stay near the manufacturer anchor even if other work is done early, such as some transmission or differential fluids, set `resets_on_service` to `false`.
11. Leave `flexible` as `false` unless the source explicitly describes flexible or condition-based timing and you are certain it should float from the last service event.
12. Use `due_soon_threshold_miles` of `500` for short-interval items around 5k-10k miles, and `1000` for longer-interval items around 12k+ miles unless the source strongly suggests something else.
13. Keep `overdue_threshold_miles` at `0` unless there is a clear reason not to.
14. If a value is unknown, use `null` rather than guessing.
15. Do not output comments, trailing commas, or explanatory text.
```

Tip:
- After generating the JSON, compare it against `examples/template_import_example.json` in this repo and then import it from the `Vehicle Maintenance` panel using `Import template`.
