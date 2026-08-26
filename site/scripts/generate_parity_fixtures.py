"""Regenerate the site calculator parity fixtures from the Python core.

Run from the repository root:

    uv run python site/scripts/generate_parity_fixtures.py

The site's interactive calculators (`site/src/lib/pert.ts`, `site/src/lib/tco.ts`)
reimplement maths that `app/*/core.py` owns. A visitor makes a decision on their
output, so the site is a product surface and its maths is netted in CI rather
than trusted.

**The generator is the contract.** Fixtures are always generated from the Python
core, never hand-written — a hand-edited expectation records what the TypeScript
currently does, which is exactly the thing under test.

Mirrors the pattern already used by `examples/remote-mcp/scripts/generate_fixtures.py`,
including its ±0.005 tolerance convention on 2-dp fields. Extends it with TCO
cases and the tag catalogue.

The tag catalogue matters most. `site/src/lib/pert.ts` hard-codes each tag's
multiplier range, duplicating `app/pert/core.py`. Those numbers are calibration
judgement — the product's actual value — so a silent divergence there changes
what the site tells a visitor while every test still passes.

`pert_display` covers the numbers a visitor actually reads off the tag panel,
which are not the same numbers the library returns. The panel used to compute
its own multipliers, so it could — and did — disagree with `applyTags` on the
same inputs. Severities step in 0.05 on the slider, so the cases below are
reachable rather than theoretical.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pert.core import DEFAULT_TAGS, calculate_task
from app.tco.core import calculate_tco

FIXTURE_PATH = Path(__file__).parent.parent / "test" / "fixtures" / "parity.json"

# (optimistic, most_likely, pessimistic) — no tags. Shared shape with the
# remote-mcp fixture set so the two nets stay comparable.
PERT_CASES = [
    (1, 2, 3),
    (0, 0, 0),
    (2, 4, 8),
    (0.5, 1.25, 2.75),
    (3.3, 3.3, 3.3),
    (1.05, 2.675, 4.125),
    (0.1, 0.25, 0.5),
    (5, 10, 30),
    (100, 250, 800),
    (0.01, 0.02, 0.03),
]

# (optimistic, most_likely, pessimistic, [(tag_name, severity), ...]).
# Severity 0 and 1 pin the ends of the interpolation; the awkward values in
# between are where a rounding difference shows up.
PERT_TAGGED_CASES = [
    (2, 4, 8, [("HIDDEN_DEPENDENCIES", 0.5)]),
    (2, 4, 8, [("HIDDEN_DEPENDENCIES", 0.0)]),
    (2, 4, 8, [("HIDDEN_DEPENDENCIES", 1.0)]),
    (5, 10, 30, [("FRAGMENTED_COMMUNICATION", 0.33)]),
    (5, 10, 30, [("MULTIPLE_STAKEHOLDERS", 0.67)]),
    (1, 2, 3, [("FRAGMENTED_COMMUNICATION", 0.5), ("MULTIPLE_STAKEHOLDERS", 0.5)]),
    (1.05, 2.675, 4.125, [("HIDDEN_DEPENDENCIES", 0.123)]),
    (
        100,
        250,
        800,
        [
            ("FRAGMENTED_COMMUNICATION", 0.9),
            ("MULTIPLE_STAKEHOLDERS", 0.1),
            ("HIDDEN_DEPENDENCIES", 0.45),
        ],
    ),
]

TCO_CASES = [
    # initial, life_years, residual, maintenance, operating, discount_rate
    (10_000, 5, 0, 0, 0, 0.03),
    (10_000, 5, 2_000, 500, 1_200, 0.03),
    (250_000, 10, 25_000, 12_000, 30_000, 0.05),
    (1_500, 3, 0, 100, 250, 0.0),  # zero discount — NPV must equal simple TCO
    (99_999.99, 7, 12_345.67, 1_111.11, 2_222.22, 0.075),
    (500, 1, 0, 0, 0, 0.03),  # single year
    (0, 4, 0, 1_000, 0, 0.02),  # no capital outlay, operating only
]


# The tag panel's slider steps in 0.05, so the first list is every severity a
# visitor can select. The second is off-slider: `effectiveMultiplier` is exported
# library API, not only a panel helper, and its scale-then-divide form left float
# noise in the return value (1.1079999999999999 for what the core calls 1.108).
# No 0.05 step reaches one, so a net built only from the slider could not go red.
DISPLAY_SEVERITIES = [round(i * 0.05, 2) for i in range(21)] + [
    0.02,
    0.04,
    0.11,
    0.123,
    0.48,
    0.71,
]

# Multi-tag selections for the combined chip. The first three were the ones that
# actually disagreed: the panel multiplied already-rounded factors and rounded
# the product a second time with half-away-from-zero, where the core rounds the
# raw product once. MULTIPLE_STAKEHOLDERS at 0.5 with HIDDEN_DEPENDENCIES at
# 0.75 showed 2.20x on the site against the core's 2.205.
DISPLAY_COMBINED_CASES = [
    [("FRAGMENTED_COMMUNICATION", 0.5), ("MULTIPLE_STAKEHOLDERS", 0.0)],
    [("FRAGMENTED_COMMUNICATION", 1.0), ("MULTIPLE_STAKEHOLDERS", 0.0)],
    [("MULTIPLE_STAKEHOLDERS", 0.5), ("HIDDEN_DEPENDENCIES", 0.75)],
    [("FRAGMENTED_COMMUNICATION", 0.5), ("MULTIPLE_STAKEHOLDERS", 0.5)],
    [("MULTIPLE_STAKEHOLDERS", 0.0), ("HIDDEN_DEPENDENCIES", 0.5)],
    [
        ("FRAGMENTED_COMMUNICATION", 0.5),
        ("MULTIPLE_STAKEHOLDERS", 0.5),
        ("HIDDEN_DEPENDENCIES", 0.5),
    ],
    [
        ("FRAGMENTED_COMMUNICATION", 0.35),
        ("MULTIPLE_STAKEHOLDERS", 0.85),
        ("HIDDEN_DEPENDENCIES", 0.15),
    ],
]


# Values chosen to separate the two failure modes the site's rounding had.
# A genuine tie (the double sits exactly on the midpoint) must round to even;
# a value that only *looks* like a tie after scaling must not. Getting the
# second case wrong is what made 51.585 come out as 51.58 instead of 51.59.
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


def _rounding_cases() -> list[dict]:
    """Pin the rounding helper directly, not only through the calculators.

    Python's round() is half-to-even on the double's exact value; JavaScript's
    Math.round is half-away-from-zero on a scaled value. The site diverged on
    both counts, so the port is worth checking on its own rather than only
    where a calculator happens to expose it.
    """
    return [{"value": v, "dp": dp, "expected": round(v, dp)} for v, dp in ROUNDING_CASES]


def _tag_catalogue() -> list[dict]:
    """Emit each tag's calibration numbers so the TS copy can be checked."""
    return [
        {
            "name": name,
            "description": tag.description,
            "min_multiplier": tag.min_multiplier,
            "max_multiplier": tag.max_multiplier,
        }
        for name, tag in sorted(DEFAULT_TAGS.items())
    ]


def _core_multipliers(tags: list[tuple[str, float]]) -> dict:
    """Return the core's own multiplier figures for one tag selection.

    Read out of ``calculate_task`` rather than recomputed here: the point is to
    pin what the core reports, and a second implementation in the generator
    would be a third copy of the maths to keep in step. The three-point inputs
    are irrelevant to the multipliers, hence (1, 2, 3).
    """
    return calculate_task(1, 2, 3, tags=[(DEFAULT_TAGS[n], s) for n, s in tags])["adjusted"]


def _display_cases() -> dict:
    """Emit the multipliers the tag panel renders, as the core computes them."""
    multipliers = [
        {
            "tag": name,
            "severity": severity,
            "expected": _core_multipliers([(name, severity)])["tags_applied"][0]["multiplier"],
        }
        for name in sorted(DEFAULT_TAGS)
        for severity in DISPLAY_SEVERITIES
    ]
    combined = [
        {
            "tags": [{"name": n, "severity": s} for n, s in case],
            "expected": _core_multipliers(case)["combined_multiplier"],
        }
        for case in DISPLAY_COMBINED_CASES
    ]
    return {"multipliers": multipliers, "combined": combined}


def build() -> dict:
    return {
        "generated_by": (
            "site/scripts/generate_parity_fixtures.py from app/pert/core.py "
            "and app/tco/core.py — do not hand-edit"
        ),
        "tolerance": 0.005,
        "rounding": _rounding_cases(),
        "tag_catalogue": _tag_catalogue(),
        "pert_display": _display_cases(),
        "pert": [
            {
                "args": {"optimistic": o, "most_likely": m, "pessimistic": p},
                "expected": calculate_task(o, m, p),
            }
            for o, m, p in PERT_CASES
        ],
        "pert_tagged": [
            {
                "args": {
                    "optimistic": o,
                    "most_likely": m,
                    "pessimistic": p,
                    "tags": [{"name": n, "severity": s} for n, s in tags],
                },
                "expected": calculate_task(o, m, p, tags=[(DEFAULT_TAGS[n], s) for n, s in tags]),
            }
            for o, m, p, tags in PERT_TAGGED_CASES
        ],
        "tco": [
            {
                "args": {
                    "initial_price": ip,
                    "useful_life_years": life,
                    "residual_value": res,
                    "annual_maintenance": maint,
                    "annual_operating_cost": op,
                    "discount_rate": rate,
                },
                "expected": calculate_tco(ip, life, res, maint, op, rate),
            }
            for ip, life, res, maint, op, rate in TCO_CASES
        ],
    }


if __name__ == "__main__":
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(build(), indent=2) + "\n")
    print(f"wrote {FIXTURE_PATH}")
