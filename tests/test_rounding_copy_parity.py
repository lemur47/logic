"""The rounding port exists twice; this stops the copies drifting apart.

`site/src/lib/round.ts` is where the implementation was first got right, and
`examples/remote-mcp/src/round.ts` is a copy of it. Until 2026-08-26 the example
carried a scale-then-compare version instead and returned 0.06 where the Python
core returns 0.07 — for a year, against twelve green fixtures, because none of
them landed on a tie.

The parity fixtures do not close this. Each copy is netted against fixtures
generated from `app.pert.core`, never against the other, so the nets catch a
*wrong* implementation but not a *thin* one: a rounding case added to one
generator and forgotten in the other leaves that port under-tested with nothing
going red. That is the same shape as the bug the copies were introduced to fix,
one level up — the divergence is in the coverage rather than in the code.

So compare the bytes, as `test_pr_auditor_prompt_parity.py` does for the other
pair of documents this repository keeps in step by hand. Comparing them by eye
is what failed the first time: places and mode look alike.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

REPO = Path(__file__).resolve().parent.parent

SITE_ROUND = REPO / "site" / "src" / "lib" / "round.ts"
EXAMPLE_ROUND = REPO / "examples" / "remote-mcp" / "src" / "round.ts"

SITE_GENERATOR = REPO / "site" / "scripts" / "generate_parity_fixtures.py"
EXAMPLE_GENERATOR = REPO / "examples" / "remote-mcp" / "scripts" / "generate_fixtures.py"

# The module header is the one part that legitimately differs: each copy points
# at the other, and the site's version speaks for two calculators where the
# example's speaks for one. Everything below it is the implementation.
MODULE_HEADER = re.compile(r"\A\s*/\*\*.*?\*/\s*", re.DOTALL)

# Named so a failure says which helper went missing rather than only that a
# string was absent.
EXPORTED_HELPERS = ("roundHalfEven", "round2", "round4")


def implementation_of(path: Path) -> str:
    """A `round.ts` with its module header stripped — the part that must match."""
    source = path.read_text(encoding="utf-8")
    header = MODULE_HEADER.match(source)
    assert header is not None, (
        f"No leading /** */ module header in {path}. This test strips that header "
        "because it is the one part allowed to differ; without a match it would "
        "compare the headers too and fail for the wrong reason."
    )
    return source[header.end() :]


def load_generator(path: Path) -> ModuleType:
    """Import a fixture generator as a module.

    Both generators guard their writes behind `if __name__ == "__main__"`, so
    importing one reads its tables without touching any fixture file.
    """
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None, f"Cannot import {path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_both_copies_still_contain_an_implementation() -> None:
    """Guard the guard: two empty strings are equal, and that is not parity.

    If a copy were emptied, renamed away, or reduced to a re-export, the equality
    check below would still pass. It would mean "nothing was compared", which is
    indistinguishable from "the copies agree" in a green test run.
    """
    for path in (SITE_ROUND, EXAMPLE_ROUND):
        body = implementation_of(path)
        for helper in EXPORTED_HELPERS:
            assert f"export function {helper}(" in body, (
                f"{path} no longer exports {helper}. Either the port moved, or "
                "this test is comparing something that is no longer the port."
            )


def test_both_generators_declare_a_non_empty_rounding_table() -> None:
    """Guard the guard, again: two empty tables are equal too."""
    for path in (SITE_GENERATOR, EXAMPLE_GENERATOR):
        cases = getattr(load_generator(path), "ROUNDING_CASES", None)
        assert cases, (
            f"{path} has no non-empty ROUNDING_CASES. That table is what pins the "
            "rounding *mode* directly instead of hoping a PERT input lands on a "
            "tie; an empty one silently un-pins it."
        )


def test_the_two_round_ts_implementations_are_byte_identical() -> None:
    """The example is a copy of the site's file, and must stay one."""
    assert implementation_of(SITE_ROUND) == implementation_of(EXAMPLE_ROUND), (
        f"{SITE_ROUND} and {EXAMPLE_ROUND} have diverged below their module "
        "headers. The example is a copy of the site's file; port the change to "
        "both, or extract one shared module. Do not fix this by editing the "
        "expected fixtures — each copy is netted against the Python core, so a "
        "divergence here means one of the two ports is now wrong."
    )


def test_the_two_generators_pin_the_same_rounding_cases() -> None:
    """Coverage drift is the gap the fixture gate cannot see.

    Each fixture set is regenerated from the core and diffed in CI, so a changed
    *expectation* goes red. A case present in one table and absent from the other
    does not: both files regenerate cleanly, and one port simply stops being
    checked on that case.
    """
    site_cases = load_generator(SITE_GENERATOR).ROUNDING_CASES
    example_cases = load_generator(EXAMPLE_GENERATOR).ROUNDING_CASES
    assert site_cases == example_cases, (
        "The two ROUNDING_CASES tables have drifted. They pin the rounding mode "
        "for two copies of the same port, so a case in one and not the other "
        "leaves that port untested on exactly the input most likely to break it. "
        f"Only in {SITE_GENERATOR.name}: {sorted(set(site_cases) - set(example_cases))}. "
        f"Only in {EXAMPLE_GENERATOR.name}: "
        f"{sorted(set(example_cases) - set(site_cases))}."
    )
