"""Regenerate the PERT parity fixtures from the Python implementation.

Run from the repository root:

    uv run python examples/remote-mcp/scripts/generate_fixtures.py

The TypeScript port in ../src/pert.ts is tested against this output
(test/fixtures/pert-parity.json) with a ±0.005 tolerance on 2-dp fields.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pert.core import calculate_task

CASES = [
    (1, 2, 3),
    (0, 0, 0),
    (2, 4, 8),
    (0.5, 1.25, 2.75),
    (3.3, 3.3, 3.3),
    (1.05, 2.675, 4.125),
    (0.1, 0.25, 0.5),
    (5, 10, 30),
    (0, 2.5, 10),
    (7.77, 8.88, 9.99),
    (100, 250, 800),
    (0.01, 0.02, 0.03),
]

ERROR_CASES = [
    {
        "args": {"optimistic": -1, "most_likely": 2, "pessimistic": 3},
        "message": "All estimates must be non-negative",
    },
    {
        "args": {"optimistic": 3, "most_likely": 2, "pessimistic": 4},
        "message": "Optimistic (3) cannot exceed most likely (2)",
    },
    {
        "args": {"optimistic": 1, "most_likely": 5, "pessimistic": 4},
        "message": "Most likely (5) cannot exceed pessimistic (4)",
    },
]


def main() -> None:
    fixtures = [
        {
            "args": {"optimistic": o, "most_likely": m, "pessimistic": p},
            "expected": calculate_task(o, m, p),
        }
        for o, m, p in CASES
    ]
    out = {
        "generated_by": "app/pert/core.py calculate_task (tags=None)",
        "cases": fixtures,
        "errors": ERROR_CASES,
    }
    target = Path(__file__).parent.parent / "test" / "fixtures" / "pert-parity.json"
    target.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {len(fixtures)} parity cases + {len(ERROR_CASES)} error cases to {target}")


if __name__ == "__main__":
    main()
