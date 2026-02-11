---
title: "API Overview"
description: "Getting started with the PMO logic API — endpoints, authentication, and examples."
order: 1
---

## Base URL

```
https://api.pmo.run
```

## Available Endpoints

### TCO (Total Cost of Ownership)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/tco/calculate` | Stateless TCO calculation |
| `POST` | `/tco/scenarios` | Create a saved scenario |
| `GET` | `/tco/scenarios` | List saved scenarios |
| `GET` | `/tco/scenarios/{id}` | Get a scenario by ID |
| `PUT` | `/tco/scenarios/{id}` | Update a scenario |
| `DELETE` | `/tco/scenarios/{id}` | Delete a scenario |

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |

## Request Format

All endpoints accept and return JSON. Include `Content-Type: application/json` in your requests.

## Example

```bash
curl -X POST https://api.pmo.run/tco/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "options": [
      {
        "name": "Option A",
        "initial_cost": 200,
        "annual_costs": [{ "name": "Toner", "amount": 180 }],
        "years": 5
      }
    ]
  }'
```

More modules (NPV, IRR, PERT) are coming soon.
