"""Regenerate the PERT parity fixtures from the Python implementation.

Run from the repository root:

    uv run python examples/remote-mcp/scripts/generate_fixtures.py

The TypeScript port in ../src/pert.ts is tested against this output
(test/fixtures/pert-parity.json) with a ±0.005 tolerance on 2-dp fields.

The tolerance is for accumulated float noise, not for rounding mode. A
rounding-mode divergence at 2 dp is always exactly 0.01, so the tolerance never
masks one — but it only ever sees the cases the table below reaches. Twelve
cases ran green for a year against a port that rounded the wrong way, because
none of them landed on a tie. Hence ROUNDING_CASES: the mode is pinned
directly, at exact equality, rather than inferred from whichever ties the PERT
inputs happen to produce.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pert.core import calculate_task

CASES = [
    (1, 2, 3),
    # Lands the expected value on 0.065, whose double sits just ABOVE the
    # midpoint. Python rounds it up to 0.07; a port that scales by 100 first
    # sees an exact 6.5 and rounds to even, giving 0.06. None of the other
    # cases reaches a tie, which is why twelve green fixtures said nothing
    # about the rounding mode.
    (0, 0.065, 0.13),
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

# Copied verbatim from site/scripts/generate_parity_fixtures.py — the two ports
# share one rounding implementation, so they share one table of cases for it.
# Values chosen to separate the two failure modes: a genuine tie (the double
# sits exactly on the midpoint) must round to even; a value that only *looks*
# like a tie after scaling must not.
ROUNDING_CASES = [
    (0.625, 2),  # exactly representable -> genuine tie -> even
    (0.635, 2),  # not exactly representable
    (2.675, 2),  # the classic float-rounding example
    (51.585, 2),  # scales to exactly 5158.5, but the double is above midpoint
    (-7.195, 2),
    (-0.625, 2),
    (1.005, 2),
    (0.5, 0),
    (1.5, 0),
    (2.5, 0),  # ties at 0 dp: 0, 2, 2
    (1.71950, 4),
    (1.14925, 4),
    (1.00005, 4),
    (0.0, 2),
    (123456.789, 2),
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
        "rounding": [{"value": v, "dp": dp, "expected": round(v, dp)} for v, dp in ROUNDING_CASES],
        "cases": fixtures,
        "errors": ERROR_CASES,
    }
    target = Path(__file__).parent.parent / "test" / "fixtures" / "pert-parity.json"
    target.write_text(json.dumps(out, indent=2) + "\n")
    print(
        f"wrote {len(fixtures)} parity cases + {len(ERROR_CASES)} error cases "
        f"+ {len(ROUNDING_CASES)} rounding cases to {target}"
    )


if __name__ == "__main__":
    main()
