# API reference

Base URL in local development: `http://localhost:8000/api`

Interactive Swagger docs: `http://localhost:8000/docs`

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health, AI availability, and demo-reset availability |
| GET | `/ai/status` | Whether optional provider-backed AI is configured |
| GET | `/templates` | Curated project templates and BOM requirements |
| GET | `/inventory` | List/search/filter stock (`search`, `category`, `status`, `include_zero`) |
| POST | `/inventory` | Create a component |
| GET | `/inventory/{id}` | Retrieve a component |
| PATCH | `/inventory/{id}` | Update component details |
| DELETE | `/inventory/{id}` | Remove an inventory record; historical name snapshots remain |
| POST | `/inventory/{id}/verify` | Mark a component verified (quarantined items are rejected) |
| POST | `/plans` | Generate a reuse-first plan (`template_id`, `goal`, `project_name`) |
| POST | `/builds` | Log a completed build; validates verified status/stock, deducts stock, writes impact event |
| GET | `/builds` | List completed builds; supports `limit` and `include_demo` |
| GET | `/builds/{id}` | Get a build and its component snapshots |
| GET | `/dashboard` | Workspace metrics, recent builds, categories and project recommendations |
| GET | `/impact/summary` | Impact ledger, monthly aggregation, methodology notes |
| GET | `/exports/inventory.csv` | Export all component records |
| GET | `/exports/impact.csv` | Export completed-build impact records |
| POST | `/assistant` | Inventory-aware assistant; local rules mode by default, optional AI when configured |
| POST | `/ai/scan` | Optional multimodal component-photo suggestion; requires `OPENAI_API_KEY` |
| POST | `/demo/reset` | Restore demo seed; disabled outside development mode |

## Example: generate a plan

```json
{
  "template_id": "soil-monitor",
  "goal": "Use salvaged parts to make a soil moisture monitor",
  "project_name": "Hostel plant buddy"
}
```

When `template_id` is omitted, a local keyword matcher selects the closest supported template. Always review the result; inference is a convenience, not an engineering guarantee.

## Example: log a completed build

```json
{
  "project_name": "Hostel plant buddy",
  "template_id": "soil-monitor",
  "parts_reused": [
    { "component_id": 1, "quantity": 1 },
    { "component_id": 3, "quantity": 1 }
  ],
  "parts_purchased": 1,
  "notes": "Prototype bench-tested; add calibration details here.",
  "is_demo": false
}
```

A completed-build request must include at least one reused part. Every referenced part must exist, have status `verified`, and have enough remaining quantity. Invalid requests roll back with a clear error; inventory stock changes only within the same transaction as the build and impact records.

## Data model summary

- **components:** current stock and metadata.
- **builds:** project, date, aggregated outcomes, impact-factor coverage, notes, demo flag.
- **build_parts:** component-name snapshots and quantity per build.
- **reuse_events:** impact-ledger event associated with a completed build.

This is a single-workspace prototype; there is no authentication or multi-user tenancy yet.
