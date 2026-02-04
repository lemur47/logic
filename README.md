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
# Clone
git clone https://github.com/lemur47/logic.git
cd logic

# Install (using uv)
uv pip install -e ".[dev]"

# Run API
uv run uvicorn app.main:app --reload

# Run standalone TCO
python examples/standalone/tco/tco.py
```

## API Endpoints

```
GET  /              → API info
GET  /health        → Health check
POST /tco/calculate → Calculate TCO
POST /tco/compare   → Compare options
POST /tco/breakeven → Break-even analysis
```

## Development

```bash
# Install pre-commit hooks
pre-commit install

# Run checks
pre-commit run --all-files

# Type check
pyright
```

## Security Pipeline

Local pre-commit and GitHub Actions run:

- **gitleaks** — Secret detection (sk-ant-* patterns included)
- **ruff** — Linting + formatting
- **bandit** — Python security audit
- **pyright** — Type checking

## License

MIT
