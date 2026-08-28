"""Every npm `overrides` entry carries a reason and a re-check date.

An override forces a dependency past the range its parent declared. That is
sometimes the only way to reach a transitive advisory — and it is also how this
repository has twice broken itself, because **npm `overrides` silently beat a
dependency's declared range**:

* `js-yaml` was pinned to exactly `4.3.0` while astro declared `^4.3.0`. Our own
  override *was* the update path, so Dependabot reported the advisory as
  unfixable and nothing said why.
* `vite` sat below the floor Astro 7 declared, so the major bump failed inside
  vite naming an option we do not set. No error named the override.

`osv-scanner.toml` requires a reason and a review-by date of every suppression.
An override is the same kind of promise — "we are overriding upstream's
judgement, here is why, ask again by this date" — so it is held to the same
standard here rather than by convention.

This is a canary. Each assertion was proved by breaking the manifest on purpose
and watching it go red; a passing run only says today is fine.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
MANIFESTS = [REPO / "site" / "package.json", REPO / "examples" / "remote-mcp" / "package.json"]

# Long enough that "transitive" or "security" alone cannot satisfy it. Every
# real reason names the path the dependency arrives by, or the advisory.
MINIMUM_REASON = 60

# Length alone is a weak proxy — sixty characters of nothing still passes — so
# a reason must also cite something a reader can go and check: the advisory it
# answers, or the pull request that introduced the override. Raised by the
# automated reviewer, which was right that the length check cannot fail for a
# bad-but-long reason.
CITATION = re.compile(r"GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}|#\d+", re.IGNORECASE)


@pytest.mark.parametrize("manifest", MANIFESTS, ids=lambda p: p.parent.name)
def test_every_override_is_explained(manifest: Path) -> None:
    package = json.loads(manifest.read_text(encoding="utf-8"))
    overrides = package.get("overrides", {})
    reasons = package.get("overridesReasons", {})

    assert overrides, (
        f"{manifest.name} declares no overrides. If they were removed, remove "
        "overridesReasons with them — an explanation for something that is no "
        "longer there reads as current."
    )
    assert set(reasons) == set(overrides), (
        "Every override needs an entry in overridesReasons and vice versa. "
        f"Unexplained: {sorted(set(overrides) - set(reasons))}. "
        f"Explaining nothing: {sorted(set(reasons) - set(overrides))}."
    )


@pytest.mark.parametrize("manifest", MANIFESTS, ids=lambda p: p.parent.name)
def test_every_reason_says_something(manifest: Path) -> None:
    package = json.loads(manifest.read_text(encoding="utf-8"))
    for name, entry in package.get("overridesReasons", {}).items():
        reason = entry.get("reason", "")
        assert len(reason) >= MINIMUM_REASON, (
            f"The reason for the {name} override is too short to be one: {reason!r}. "
            "Name how the dependency arrives, or the advisory it answers."
        )
        assert CITATION.search(reason), (
            f"The reason for the {name} override cites nothing checkable: {reason!r}. "
            "Give the advisory ID it answers, or the pull request that introduced "
            "it — a reader has to be able to go and verify the claim, and prose "
            "alone gives them nowhere to start."
        )


@pytest.mark.parametrize("manifest", MANIFESTS, ids=lambda p: p.parent.name)
def test_no_re_check_date_has_passed(manifest: Path) -> None:
    """A date nobody honours is decoration.

    This is deliberately enforcing rather than advisory, matching the npm audit
    allowlist and `osv-scanner.toml`. It means a re-check date arriving turns
    the required `pytest` job red with no commit behind it — which is the point:
    the alternative is an override that outlives its reason in silence.

    Re-checking does not mean deleting. Confirm the override is still needed,
    say so, and move the date.
    """
    package = json.loads(manifest.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    overdue = [
        f"{name} (due {entry['reviewBy']})"
        for name, entry in package.get("overridesReasons", {}).items()
        if entry.get("reviewBy", "") < today
    ]
    assert not overdue, (
        f"Override re-check dates have passed in {manifest.name}: {', '.join(overdue)}. "
        "Verify each is still required — the upstream range may have moved — then "
        "either drop the override or re-date it with what you found. Do not extend "
        "it silently."
    )
