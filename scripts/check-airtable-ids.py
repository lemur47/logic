#!/usr/bin/env python3
"""Airtable ID leak guard — commit messages and ``gh`` payloads.

Airtable record, base, table and field IDs are the internal CTO ↔ agent
channel. Git history is the project's external record, and this repository is
public — so the two must not meet. Referring to work in plain English costs
nothing; an ID in a public commit message cannot be taken back without
rewriting history that other clones already have.

The gitleaks ``airtable-id`` rule already gates *committed file content*. It
cannot see three surfaces:

* the commit **message**, which is never a file in the working tree;
* the body of a ``gh pr`` / ``gh issue`` command, which never touches the
  repository at all;
* the **squash-merge message**, composed in the GitHub web interface at merge
  time — so it passes through no local hook, on any machine, and it is the one
  message that actually lands on ``main``.

This script covers the first two outright. For the third it scans the pull
request's title and body, which is what the squash dialog is seeded from: that
covers merging them unedited, and does **not** reach a message rewritten in the
dialog itself, because that edit re-triggers no check at all.

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

merge-gate mode (CI, ``--pr-text``)::

    python scripts/check-airtable-ids.py --pr-text title.txt body.md messages.txt

  Scans each file verbatim — no comment stripping, because '#' opens a markdown
  heading in a pull request body — and fails closed on a file it cannot read.
  Run from the required ``gitleaks`` job, so it blocks a merge rather than
  advising one.

Exit codes (commit-msg mode):
    0 — clear, commit proceeds
    2 — called with no message path: a misconfigured hook, not a clean pass
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

# The floor is necessary and it is also porous. The 2026-08-21 review generated
# 200,000 synthetic identifiers of the real shape: mean 3.847, first percentile
# 3.455, with 2.63 per cent scoring below 3.5. One genuine identifier in
# thirty-eight therefore passes, and because the gitleaks rule shares the
# constant by design the blind spot is IDENTICAL on both gates rather than one
# covering for the other.
#
# The structural signals below close that tail. They sit ON TOP of the floor,
# never in place of it — a union. Replacing the floor was the original scope and
# was reversed before execution, for two reasons worth keeping:
#
#   * a LONE identifier in a commit message satisfies no structural signal, and
#     that is the canonical leak this guard exists to stop;
#   * gitleaks rules are regex plus entropy only, so adjacency and "a service
#     URL in context" cannot be expressed in `.gitleaks.toml`. Replacing the
#     floor would diverge the two gates; adding to it leaves the shared constant
#     intact, so nothing gitleaks blocks passes here.

# The service whose identifiers these are. A token below the floor sitting next
# to its own service name is not a coincidence — but "next to" has to mean it,
# so the domain is looked for on the SAME LINE as the token, not anywhere in
# the text. A pull request that links to airtable.com documentation in one
# paragraph and uses a lookalike word in another is not a leak.
SERVICE_URL_PATTERN = re.compile(r"airtable\.com", re.IGNORECASE)

# What may sit between two identifiers for them to count as adjacent: URL path
# and query punctuation only. This is the copy-pasted-URL shape
# (`.../appXXX/tblYYY/viwZZZ`).
#
# Whitespace and commas were in this class in the first version, and that made
# the claim below false: `", "` between two words in a sentence, and `"\n- "`
# between two markdown bullets, both qualified as "adjacent". Ordinary
# formatting is not a paste, and a guard that blocks a bullet list is one people
# learn to bypass. Two shape-matching words separated by punctuation a URL would
# not contain are now left alone — the paste-count signal still covers three.
_ADJACENCY_GAP = re.compile(r"^[/?&=#]{1,3}$")

# How many shape-matching tokens make a message a paste rather than a sentence.
# One lookalike is a word; two can be a sentence ("recrystallisation and
# selectAllElements"); three is not prose anyone writes by accident.
_PASTE_TOKEN_COUNT = 3

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


def _has_adjacent_pair(matches: list[re.Match[str]], text: str) -> bool:
    """True if two shape-matching tokens are separated by URL punctuation alone."""
    for first, second in zip(matches, matches[1:], strict=False):
        if _ADJACENCY_GAP.fullmatch(text[first.end() : second.start()]):
            return True
    return False


def _service_url_on_the_same_line(text: str, match: re.Match[str]) -> bool:
    """True if the service's own domain sits on the token's line.

    Proximity rather than co-occurrence. Searching the whole text would condemn
    any low-entropy lookalike in a document that happens to link to the service
    somewhere else, which is a false positive with no leak behind it.
    """
    start = text.rfind("\n", 0, match.start()) + 1
    end = text.find("\n", match.end())
    line = text[start:] if end == -1 else text[start:end]
    return SERVICE_URL_PATTERN.search(line) is not None


def find_airtable_id(text: str) -> str | None:
    """Return the first token that must block, or None.

    Two ways to block, and the order matters. The entropy floor is a HARD
    block: any token at or above it fails on its own, so a lone identifier is
    caught exactly as before. Only when every token sits BELOW the floor do the
    structural signals get a say, and they can block the whole low tail without
    the floor being lowered by a thousandth.

    Returning `str | None` is unchanged deliberately: both callers and both
    renderers want one token to name in their message, so the union is evaluated
    here rather than pushed out into the call sites.
    """
    matches = list(AIRTABLE_ID_PATTERN.finditer(text))
    if not matches:
        return None

    for match in matches:
        if shannon_entropy(match.group(0)) >= ENTROPY_FLOOR:
            return match.group(0)

    if len(matches) >= _PASTE_TOKEN_COUNT or _has_adjacent_pair(matches, text):
        return matches[0].group(0)

    for match in matches:
        if _service_url_on_the_same_line(text, match):
            return match.group(0)
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


def _scan_pr_text(paths: list[str]) -> int:
    """--pr-text mode: scan pull-request text verbatim, exit 1 on match.

    Two things differ from commit-msg mode, both deliberate:

    * **No comment-line stripping.** Git removes '#' lines before committing;
      in a pull request body '#' opens a markdown heading and is published as
      written. Stripping here would hand every author a one-character bypass.
    * **Unreadable input fails CLOSED.** In commit-msg mode git would already
      have failed on a message it cannot read. Here an unreadable file means
      the CI step is broken, and reporting a clean pass we never performed is
      the failure this mode exists to remove.
    """
    blocked = False
    for path in paths:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"airtable-id-guard: could not read {path!r}: {exc}", file=sys.stderr)
            return 2
        found = find_airtable_id(text)
        if found is not None:
            print(
                f"airtable-id-guard: BLOCKED — Airtable ID {found!r} in {path}. "
                "Pull request titles, bodies and commit messages become the public "
                "record; this repository squash-merges, so the merge message is "
                "composed in the web interface and no local hook ever sees it. "
                "Describe the work in plain English.",
                file=sys.stderr,
            )
            blocked = True
    return 1 if blocked else 0


def main(argv: list[str]) -> int:
    if "--hook" in argv:
        return _run_hook()

    if "--pr-text" in argv:
        paths = [arg for arg in argv if not arg.startswith("-")]
        if not paths:
            print("usage: check-airtable-ids.py --pr-text <file> [<file>...]", file=sys.stderr)
            return 2
        return _scan_pr_text(paths)

    positional = [arg for arg in argv if not arg.startswith("-")]
    if not positional:
        # Fail CLOSED. Being called with no message path means the hook is
        # wired up wrongly, and a leak gate that reports success when it was
        # given nothing to scan is the failure this repository has already paid
        # for once: the gitleaks hook scanned ~0 bytes and exited 0 for months.
        print("usage: check-airtable-ids.py <commit-msg-file> | --hook", file=sys.stderr)
        return 2
    return _scan_commit_msg(positional[0])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
