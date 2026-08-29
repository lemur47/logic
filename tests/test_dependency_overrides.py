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


# --- Dependabot's own deferrals ----------------------------------------------
#
# An `ignore` entry is the same promise as an override or a suppression: we are
# declining an update for a reason, and the reason has a shelf life. Held
# without an expiry it becomes a dependency frozen by accident — which is the
# state the two npm trees were already in for six months, arrived at by having
# no update channel rather than by choosing one.

DEPENDABOT = REPO / ".github" / "dependabot.yml"
REVIEW_BY = re.compile(r"review-by\s+(\d{4}-\d{2}-\d{2})")


def ignore_blocks() -> list[tuple[int, str]]:
    """Each `ignore:` key, with the comment block directly above it.

    Read textually: dependabot.yml carries the reason in comments, and a YAML
    parser discards exactly the part under test.
    """
    lines = DEPENDABOT.read_text(encoding="utf-8").splitlines()
    found = []
    for index, line in enumerate(lines):
        if line.strip() != "ignore:":
            continue
        preamble = []
        cursor = index - 1
        while cursor >= 0 and lines[cursor].strip().startswith("#"):
            preamble.append(lines[cursor])
            cursor -= 1
        found.append((index + 1, "\n".join(reversed(preamble))))
    return found


def test_every_dependabot_ignore_is_dated_and_current() -> None:
    """A held-back dependency needs a reason and a date, like everything else.

    Deliberately enforcing: the date arriving reds the required job, which is
    the only thing that makes anyone look again. Re-checking does not mean
    lifting the hold — confirm whether the constraint still stands, say so, and
    move the date.
    """
    today = date.today().isoformat()
    for line_number, preamble in ignore_blocks():
        match = REVIEW_BY.search(preamble)
        assert match, (
            f"The `ignore:` block at .github/dependabot.yml:{line_number} carries no "
            "`review-by YYYY-MM-DD` in the comment above it. An update declined "
            "with no expiry is a dependency frozen by accident."
        )
        assert match.group(1) >= today, (
            f"The `ignore:` block at .github/dependabot.yml:{line_number} passed its "
            f"review-by date ({match.group(1)}). Check whether the constraint that "
            "justified it still holds — upstream may have moved — then either lift "
            "the hold or re-date it with what you found."
        )
