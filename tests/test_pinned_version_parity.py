"""Tool versions pinned in more than one place, asserted instead of asked for.

Four keep-these-in-step rules in this repository are enforced only by comments.
When one drifts the symptom is green-locally, red-in-CI — or worse, green in
both while two different tools ran. `.pre-commit-config.yaml` records that ruff
once sat at three different versions across its three pins, so local commits and
CI ran different formatters and neither said so.

Nothing has drifted at the time of writing. This file is therefore a canary, not
a repair: a passing run proves only that today is fine, so each assertion was
proved by deliberately bumping one side and watching it go red. That is the
standing rule for controls that fail by silence.

**`.python-version` is excluded from the Python set, deliberately.** It reads
3.14 — the interpreter we develop on — against a 3.12 support floor declared in
`requires-python`, `[tool.pyright] pythonVersion` and ruff's `target-version`.
Those three are one fact and must agree. The fourth is a different fact, and a
test that folded it in would "fix" a deliberate split by dragging the floor up
to the interpreter, silently narrowing what the package supports.

**`osv-scanner` IS asserted here now.** It was not: the hook pinned `v2.3.3`
while CI's action was `v2.5.1`, and this file said so rather than checking it,
because asserting a known skew would have redded the gate for a drift nothing
was scoped to close. The hook is now at `v2.5.1` and the assertion is live.

Its CI half is read from the **comment** on the `uses:` line, not from a value —
the action is SHA-pinned, and the trailing `# vX.Y.Z` that Dependabot maintains
is the only human-readable version there.

**So be exact about what this proves: comment-versus-rev parity, not
SHA-versus-rev parity.** If a SHA is changed and the comment left behind, the
lookup still returns a present-but-stale version and the comparison passes while
the action that actually runs has drifted from what the comment claims. The
found-check below catches the comment vanishing; it cannot catch the comment
lying. Closing that would mean resolving the SHA to a tag over the network,
which is not something a required unit test should depend on.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

PRE_COMMIT = REPO / ".pre-commit-config.yaml"
PYPROJECT = REPO / "pyproject.toml"
UV_LOCK = REPO / "uv.lock"
CI_WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"

# Whole URLs, not fragments — see `pre_commit_rev`.
RUFF_HOOK_REPO = "https://github.com/astral-sh/ruff-pre-commit"
GITLEAKS_HOOK_REPO = "https://github.com/gitleaks/gitleaks"
OSV_HOOK_REPO = "https://github.com/google/osv-scanner"
OSV_ACTION = "google/osv-scanner-action/osv-scanner-action"


def as_tuple(version: str | None) -> tuple[int, ...]:
    """`v0.16.2` and `0.16.2` alike, as comparable integers.

    A missing pin raises here rather than comparing as absent, so a lookup that
    silently stopped matching cannot reach a comparison and pass.
    """
    assert version is not None, "A pin this comparison needs was not found at all."
    return tuple(int(part) for part in version.lstrip("v").split("."))


def pre_commit_rev(repo_url: str) -> str | None:
    """The `rev` pinned against an exact hook-repository URL.

    Matched textually rather than through a YAML parser. PyYAML reaches this
    environment only as a transitive dependency of `pre-commit`, so a test built
    on it passes or errors depending on somebody else's dependency tree — the
    same class of accident this file exists to make visible. The shape here is
    fixed (`- repo: <url>` then `rev: <pin>`), and the guard test below catches
    a pattern that stops matching.

    The URL is matched WHOLE, deliberately. A substring match on `gitleaks`
    still finds `github.com/gitleaks/anything-else`, which would let a renamed
    hook keep satisfying the lookup while pinning a different tool.
    """
    pattern = re.compile(
        rf"^\s*-\s*repo:\s*{re.escape(repo_url)}\s*$\s*^\s*rev:\s*(\S+)\s*$",
        re.MULTILINE,
    )
    match = pattern.search(PRE_COMMIT.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def uv_lock_version(package: str) -> str | None:
    """What `uv.lock` actually resolves — the version a developer really runs."""
    lock = tomllib.loads(UV_LOCK.read_text(encoding="utf-8"))
    for entry in lock["package"]:
        if entry["name"] == package:
            return entry["version"]
    return None


def pyproject_floor(package: str) -> str | None:
    """The `>=` floor declared for a dev dependency.

    Only the floor, even where the specifier grows an upper bound later:
    `ruff>=0.16.2,<1` yields `0.16.2`. Returning the whole tail would reach
    `as_tuple` as `0.16.2,<1` and crash on `int("2,<1")` — a bare traceback in
    a file that otherwise takes care to say what went wrong and why.
    """
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    for extra in config["project"]["optional-dependencies"].values():
        for requirement in extra:
            if requirement.startswith(f"{package}>="):
                return requirement.split(">=", 1)[1].split(",")[0].strip()
    return None


def ci_env_value(name: str) -> str | None:
    """A bare `NAME: "value"` env pin in the workflow.

    Read textually on purpose. These pins are the ones Dependabot cannot see —
    a bare env var and a pre-commit rev both move by hand or not at all — so the
    check has to look at the same characters a human would edit.
    """
    match = re.search(rf'^\s*{name}:\s*"?([^"\s]+)"?\s*$', CI_WORKFLOW.read_text(), re.MULTILINE)
    return match.group(1) if match else None


def ci_action_version(action: str) -> str | None:
    """The `# vX.Y.Z` comment Dependabot keeps beside a SHA-pinned action.

    The SHA is the control; the comment is the only place the version is legible
    to a person, which makes it the only thing comparable to a pre-commit rev.
    A comparison against a comment is worth less than one against a value — so
    a lookup that stops matching must fail loudly, which is what the found-check
    is for.
    """
    match = re.search(
        rf"^\s*uses:\s*{re.escape(action)}@[0-9a-f]{{40}}\s*#\s*(v?\d+\.\d+\.\d+)\s*$",
        CI_WORKFLOW.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    return match.group(1) if match else None


def python_floor_declarations() -> dict[str, str | None]:
    """The three places that state the *support floor*, normalised to `3.12`."""
    config = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    requires = config["project"]["requires-python"]
    target = config["tool"]["ruff"]["target-version"]

    return {
        "project.requires-python": requires.lstrip(">=").strip(),
        "tool.pyright.pythonVersion": config["tool"]["pyright"]["pythonVersion"],
        # `py312` states the same fact in ruff's own spelling.
        "tool.ruff.target-version": f"{target[2]}.{target[3:]}",
    }


def test_every_pin_this_file_compares_was_actually_found() -> None:
    """Guard the guard: two `None`s are equal, and that is not agreement.

    Every lookup here is a search that can silently miss — a renamed hook
    repository, a moved env var, a dependency group that changed shape. If one
    starts returning `None` the comparisons below keep passing while checking
    nothing, which is the failure mode this whole file exists to catch.
    """
    found = {
        "ruff pre-commit rev": pre_commit_rev(RUFF_HOOK_REPO),
        "ruff uv.lock version": uv_lock_version("ruff"),
        "ruff pyproject floor": pyproject_floor("ruff"),
        "gitleaks pre-commit rev": pre_commit_rev(GITLEAKS_HOOK_REPO),
        "gitleaks CI env": ci_env_value("GITLEAKS_VERSION"),
        "osv-scanner pre-commit rev": pre_commit_rev(OSV_HOOK_REPO),
        "osv-scanner CI action version": ci_action_version(OSV_ACTION),
        **python_floor_declarations(),
    }
    missing = [name for name, value in found.items() if not value]
    assert not missing, (
        f"These pins could not be located at all: {missing}. Until each is found "
        "again the parity assertions below are comparing nothing and reporting "
        "green, which is exactly the silence they were written to break."
    )


def test_ruff_agrees_across_its_three_pins() -> None:
    """The hook, the lockfile and the declared floor must describe one tool."""
    rev = pre_commit_rev(RUFF_HOOK_REPO)
    resolved = uv_lock_version("ruff")
    floor = pyproject_floor("ruff")

    assert as_tuple(rev) == as_tuple(resolved), (
        f"ruff pre-commit rev {rev} does not match the {resolved} that uv.lock "
        "resolves. These are the two copies that actually run — one in the hook, "
        "one under `uv run` and in CI — so a mismatch means local commits and CI "
        "are formatted by different versions, with nothing announcing it."
    )
    assert as_tuple(floor) <= as_tuple(resolved), (
        f"The ruff floor in pyproject.toml ({floor}) is above the resolved "
        f"{resolved}. The floor is a floor deliberately: it marks the release "
        "whose Markdown-formatting behaviour `extend-exclude` defends against. "
        "Raise the lock, do not lower the floor."
    )


def test_gitleaks_agrees_across_the_hook_and_the_workflow() -> None:
    """Unset, `gitleaks-action` resolves the latest release at run time."""
    rev = pre_commit_rev(GITLEAKS_HOOK_REPO)
    ci_pin = ci_env_value("GITLEAKS_VERSION")

    assert as_tuple(rev) == as_tuple(ci_pin), (
        f"gitleaks pre-commit rev {rev} does not match GITLEAKS_VERSION {ci_pin} "
        "in the CI workflow. Neither surface is covered by Dependabot — a bare "
        "env var and a pre-commit rev both move by hand or not at all — and an "
        "unset CI pin makes a SHA-pinned action download an unpinned binary."
    )


def test_osv_scanner_agrees_across_the_hook_and_the_action() -> None:
    """Two scanners enforcing one policy, with nothing forcing them to agree.

    No Dependabot ecosystem covers a pre-commit `rev`, so the hook moves by hand
    while the action moves on its own. Skewed, a local green says nothing about
    CI: the two run different rule sets and different detectors over the same
    lockfiles, and the difference surfaces as a merge-gate failure nobody could
    reproduce locally.
    """
    rev = pre_commit_rev(OSV_HOOK_REPO)
    action = ci_action_version(OSV_ACTION)

    assert as_tuple(rev) == as_tuple(action), (
        f"osv-scanner pre-commit rev {rev} does not match the {action} CI pins. "
        "The hook is the copy that gates a commit and the action is the copy "
        "that gates a merge; when they differ, passing locally is not evidence "
        "about the required job."
    )


def test_the_python_support_floor_is_one_number_in_three_places() -> None:
    """Excluding `.python-version`, which states a different fact on purpose."""
    declared = python_floor_declarations()
    assert len(set(declared.values())) == 1, (
        f"The Python support floor disagrees across its declarations: {declared}. "
        "These three are one fact — what the package promises to run on. Do not "
        "reconcile them against `.python-version`, which is the interpreter we "
        "develop on and is higher by design."
    )
