# logic

**Atomic logic for decision-making.**
Turning abstract ideas into executable functions.

## Philosophy

- **Executable:** Ideas are just hypotheses until they're code.
- **Composable:** Functions designed to be imported or piped.
- **Lean:** External dependencies are a last resort.
- **Privacy-first:** Your secrets stay local. Always.

## Modules

### Finance

| Tool | Status | Description |
|------|--------|-------------|
| TCO | ✅ Live | Total Cost of Ownership calculator with NPV adjustment |
| NPV | 📋 Planned | Net Present Value analysis |
| IRR | 📋 Planned | Internal Rate of Return |

### P3M/P3G

| Tool | Status | Description |
|------|--------|-------------|
| PERT | 📋 Planned | For estimation |
| Base-rate | 📋 Planned | Reduce subjective bias |
| Bayesian | 📋 Planned | For base-rate learning |

### Privacy

- *Upcoming: Image metadata removal...*

## Quick Start

```bash
git clone https://github.com/lemur47/logic.git && cd logic
uv pip install -e ".[dev]"
uv run uvicorn app.main:app --reload   # API at http://127.0.0.1:8000
```

## API Endpoints

```
GET    /                       API info
GET    /health                 Health check
POST   /tco/calculate          Calculate TCO (stateless)
POST   /tco/compare            Compare options, ranked by annual cost
POST   /tco/breakeven          Break-even analysis between two options
POST   /tco/scenarios          Save a scenario
GET    /tco/scenarios          List scenarios (paginated, searchable)
GET    /tco/scenarios/{id}     Get a scenario
PATCH  /tco/scenarios/{id}     Update a scenario (auto-recalculates)
DELETE /tco/scenarios/{id}     Delete a scenario
GET    /tco/scenarios/stats    Aggregate statistics
```

## Development

Commands, architecture, and code style conventions are documented in [`CLAUDE.md`](CLAUDE.md).

## License

MIT
