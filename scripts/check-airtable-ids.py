#!/usr/bin/env python3
"""Airtable ID leak guard — commit messages and ``gh`` payloads.

Airtable record, base, table and field IDs are the internal CTO ↔ agent
channel. Git history is the project's external record, and this repository is
public — so the two must not meet. Referring to work in plain English costs
nothing; an ID in a public commit message cannot be taken back without
rewriting history that other clones already have.

The gitleaks ``airtable-id`` rule already gates *committed file content*. It
cannot see two surfaces:

* the commit **message**, which is never a file in the working tree;
* the body of a ``gh pr`` / ``gh issue`` command, which never touches the
  repository at all.

This script covers exactly those, in two modes.

commit-msg mode (pre-commit ``commit-msg`` stage)::

    python scripts/check-airtable-ids.py <commit-msg-file>

  Scans the message, minus git's comment lines. Exit 1 blocks the commit.
  Tracked in ``.pre-commit-config.yaml``, so it protects commits made outside
  the agent environment too — including a fresh clone's.

PreToolUse hook mode (Claude Code, ``--hook``)::

    python3 scripts/check-airtable-ids.py --hook   # JSON payload on stdin

  Scans the command string plus any file named by ``-F``/``--file``/
  ``--body-file``, and denies before the artefact exists. Registered in
  ``.claude/settings.local.json``, which is gitignored — so this half is
  local belt-and-braces, not a guarantee a clone inherits.

Exit codes (commit-msg mode):
    0 — clear, commit proceeds
    1 — Airtable ID detected, commit blocked
"""

from __future__ import annotations

import json
import math
import re
import shlex
import sys
from collections import Counter
from pathlib import Path

# Prefixes and shape are kept identical to the gitleaks `airtable-id` rule in
# `.gitleaks.toml`. Two gates covering adjacent surfaces must agree on what an
# ID *is*, or a token blocked on one path sails through the other.
AIRTABLE_ID_PATTERN = re.compile(r"\b(?:app|tbl|fld|rec|viw|sel)[A-Za-z0-9]{14}\b")

# Shannon-entropy floor, also mirroring the gitleaks rule.
#
# Without it this guard blocks ordinary English. A real ID is 17 characters of
# mixed-case base62; so is "recrystallisation" (~3.38 bits), "selectAllElements"
# (~2.91) and a long tail of words nobody should have to avoid in a commit
# message. Generated IDs sit near 3.8-4.0, so the floor separates them cleanly.
# A false positive here blocks a commit, which is exactly the friction that
# teaches people to reach for --no-verify.
ENTROPY_FLOOR = 3.5

# Command families whose payloads become public artefacts.
_GUARDED_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("git", "commit"),
    ("gh", "pr"),
    ("gh", "issue"),
)

# Flags whose value is a path whose contents also warrant scanning
# (``gh pr create --body-file body.md``, ``git commit -F msg.txt``).
_FILE_VALUE_FLAGS: tuple[str, ...] = ("-F", "--file", "--body-file")


def shannon_entropy(text: str) -> float:
    """Shannon entropy of *text* in bits per character."""
    if not text:
        return 0.0
    length = len(text)
    return -sum((count / length) * math.log2(count / length) for count in Counter(text).values())


def find_airtable_id(text: str) -> str | None:
    """Return the first token that looks like a real Airtable ID, or None.

    Shape alone is not enough — see ENTROPY_FLOOR.
    """
    for match in AIRTABLE_ID_PATTERN.finditer(text):
        token = match.group(0)
        if shannon_entropy(token) >= ENTROPY_FLOOR:
            return token
    return None


def _strip_comment_lines(message: str) -> str:
    """Drop git comment lines.

    Git's default 'strip' cleanup removes these before the message is
    committed, so scanning them only invents false positives — notably on the
    commented diff that ``commit --verbose`` prepends.
    """
    return "\n".join(line for line in message.splitlines() if not line.startswith("#"))


def _contains_guarded_command(tokens: list[str]) -> bool:
    """True if a guarded invocation appears anywhere in the token stream.

    Scans the whole stream rather than the head, so a compound command such as
    ``cd site && git commit -m ...`` is still caught.
    """
    for prefix in _GUARDED_COMMANDS:
        width = len(prefix)
        for i in range(len(tokens) - width + 1):
            if tuple(tokens[i : i + width]) == prefix:
                return True
    return False


def _referenced_files(tokens: list[str]) -> list[str]:
    """Paths named by the file-value flags, in both ``flag value`` and
    ``flag=value`` forms."""
    files: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in _FILE_VALUE_FLAGS:
            if index + 1 < len(tokens):
                files.append(tokens[index + 1])
            index += 2
            continue
        for flag in _FILE_VALUE_FLAGS:
            if token.startswith(f"{flag}="):
                files.append(token[len(flag) + 1 :])
                break
        index += 1
    return files


def _emit_deny(found: str) -> None:
    """Print the PreToolUse 'deny' decision.

    Always paired with exit 0 — under the hook spec the decision carries the
    block, and a non-zero exit would be read as the hook itself failing.
    """
    reason = (
        f"Airtable ID '{found}' found in a git/gh command. Record, base, table and "
        "field IDs must stay out of commit messages, PR titles and bodies, and issue "
        "bodies — git history is the project's public record. Refer to the work in "
        "plain English; the ID belongs in the Airtable record or CLAUDE.local.md."
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def _print_commit_block(found: str) -> None:
    """Human-facing block message for the commit-msg stage."""
    lines = (
        "",
        "=" * 64,
        "  AIRTABLE ID GUARD — COMMIT BLOCKED",
        "=" * 64,
        "",
        f"  An Airtable ID reached the commit message: {found}",
        "",
        "  Git history is this project's public, permanent record, and this",
        "  repository is public. Record/base/table/field IDs are the internal",
        "  CTO <-> agent channel and belong in the Airtable record itself, or",
        "  in CLAUDE.local.md (gitignored).",
        "",
        "  Action: describe the work in plain English and commit again.",
        "  Do not reach for --no-verify: once pushed, the only remedy is a",
        "  history rewrite that breaks every clone and fork.",
        "",
        "=" * 64,
        "",
    )
    print("\n".join(lines), file=sys.stderr)


def _run_hook() -> int:
    """PreToolUse mode: read the JSON payload, deny guarded commands carrying IDs."""
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return 0  # Malformed payload — fall through to the normal permission flow.

    if payload.get("tool_name") != "Bash":
        return 0

    command = (payload.get("tool_input") or {}).get("command", "")
    if not command:
        return 0

    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()

    if not _contains_guarded_command(tokens):
        return 0

    haystack = command
    for path in _referenced_files(tokens):
        try:
            haystack += "\n" + Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # Unreadable referenced file — scan what we do have.

    found = find_airtable_id(haystack)
    if found is not None:
        _emit_deny(found)
    return 0


def _scan_commit_msg(path: str) -> int:
    """commit-msg mode: scan the message file, exit 1 on match."""
    try:
        message = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        # Fail open — git would have failed first on a message it cannot read —
        # but say so rather than reporting a clean pass we did not perform.
        print(f"airtable-id-guard: could not read {path!r}: {exc}", file=sys.stderr)
        return 0

    found = find_airtable_id(_strip_comment_lines(message))
    if found is None:
        return 0
    _print_commit_block(found)
    return 1


def main(argv: list[str]) -> int:
    if "--hook" in argv:
        return _run_hook()

    positional = [arg for arg in argv if not arg.startswith("-")]
    if not positional:
        print("usage: check-airtable-ids.py <commit-msg-file> | --hook", file=sys.stderr)
        return 0
    return _scan_commit_msg(positional[0])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
