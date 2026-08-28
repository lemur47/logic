"""The secret gate's configuration, asserted instead of commented.

`.pre-commit-config.yaml` carries a long comment saying DO NOT ADD `args` to
the gitleaks hook. That comment is there because the key was added once and the
gate became a no-op: pre-commit *appends* args to the hook's own entry rather
than replacing it, so a trailing positional became the scan path, gitleaks
failed to chdir, scanned ~0 bytes and exited 0. The hook reported "Passed" on
every commit for months, `--config` never applied either, and a planted canary
went through green.

A comment cannot fail. These assertions can.

This is a canary rather than a repair — nothing has drifted at the time of
writing, so a passing run proves only that today is fine. Each assertion below
was proved by making the config wrong on purpose and watching it go red, which
is the standing rule for controls that fail by silence.

Matched textually rather than through a YAML parser, for the reason given in
`test_pinned_version_parity.py`: PyYAML reaches this environment only as a
transitive dependency of pre-commit, so a test built on it passes or errors
depending on somebody else's dependency tree.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PRE_COMMIT = REPO / ".pre-commit-config.yaml"

# The gitleaks hook block: from its `- id: gitleaks` line to the next line that
# starts a sibling key at the same or lower indentation.
GITLEAKS_HOOK = re.compile(r"^(\s*)-\s*id:\s*gitleaks\s*$\n((?:\1\s+.*\n|\s*\n)*)", re.MULTILINE)


def gitleaks_hook_block() -> str:
    """The gitleaks hook's own keys, or fail loudly if it is not there.

    A lookup that silently stopped matching would let every assertion below
    pass against nothing — the same shape as the defect under test.
    """
    match = GITLEAKS_HOOK.search(PRE_COMMIT.read_text(encoding="utf-8"))
    assert match is not None, (
        "The gitleaks hook was not found in .pre-commit-config.yaml at all. "
        "Either the secret gate has been removed, or this pattern stopped "
        "matching and every assertion in this file is now vacuous."
    )
    return match.group(2)


def test_gitleaks_hook_declares_no_args() -> None:
    """The exact regression that made the gate a no-op for months.

    pre-commit APPENDS `args` to the upstream entry
    (`gitleaks git --pre-commit --redact --staged --verbose`), so anything
    positional becomes the path gitleaks scans. There is no safe value here;
    the key itself is the defect.
    """
    assert "args:" not in gitleaks_hook_block(), (
        "The gitleaks pre-commit hook declares `args`. pre-commit appends them "
        "to the hook's own entry, so a positional becomes the scan PATH and the "
        "hook passes having scanned ~0 bytes. Delete the key; .gitleaks.toml is "
        "auto-discovered at the repo root and needs no flag."
    )


def test_the_zero_byte_guard_is_wired_into_the_same_stage() -> None:
    """A gate whose companion check is not installed is one gate, not two.

    `staged-bytes-guard` is what makes an empty scan red instead of a green
    tick indistinguishable from a real pass. It has to run at the pre-commit
    stage, and unconditionally — a `files:` filter would let it be skipped by
    the very commits it is meant to question.
    """
    config = PRE_COMMIT.read_text(encoding="utf-8")
    assert "id: staged-bytes-guard" in config
    block = re.search(
        r"^(\s*)-\s*id:\s*staged-bytes-guard\s*$\n((?:\1\s+.*\n|\s*\n)*)", config, re.MULTILINE
    )
    assert block is not None, "The zero-byte guard's hook block stopped matching."
    body = block.group(2)
    assert "always_run: true" in body, "The zero-byte guard must not be skippable."
    assert "stages: [pre-commit]" in body


def test_the_commit_message_guard_is_still_wired_at_commit_msg_stage() -> None:
    """The identifier guard is only a gate while pre-commit installs that stage.

    `default_install_hook_types` is what makes a plain `pre-commit install`
    wire up commit-msg as well. Without it the guard installs silently as a
    no-op, which is configured-but-not-active — the failure class this
    repository keeps paying for.
    """
    config = PRE_COMMIT.read_text(encoding="utf-8")
    # Read the KEY, not the file. The first draft of this assertion searched the
    # header for the string "commit-msg" and passed against a config with the
    # stage removed, because the explanatory comment above the key contains the
    # same words. Found by perturbing it; it would never have failed on its own.
    declared = re.search(r"^default_install_hook_types:\s*\[(.*)\]\s*$", config, re.MULTILINE)
    assert declared is not None, "default_install_hook_types is not declared at all."
    assert "commit-msg" in declared.group(1), (
        "default_install_hook_types no longer wires the commit-msg stage, so "
        "`pre-commit install` leaves the Airtable ID guard uninstalled — "
        "configured, reported as installed, and never running."
    )
    assert "id: airtable-id-guard" in config
