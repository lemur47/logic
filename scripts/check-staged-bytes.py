#!/usr/bin/env python3
"""Refuse a zero-byte secret scan.

The gitleaks pre-commit hook reports success identically whether it scanned the
staged diff or scanned nothing at all. That is not hypothetical: for as long as
the hook carried an ``args`` key, pre-commit appended it to the upstream entry,
gitleaks read the first positional as a path, failed to chdir, scanned ~0 bytes
and **exited 0**. Every commit in that period passed a gate that was not
running, and a planted canary went through green.

In ``--staged`` mode gitleaks always prints ``0 commits scanned``, red or green,
so the commit count says nothing. The honest signal is the **byte count** — and
the hook's own output is not available to another hook.

What this hook can assert independently is the other half of the same fact:
that the gate had something to scan at all. If the staged diff is empty, a
green secret gate is meaningless, and this makes that state red instead.

**Say plainly what this does not prove.** It does not prove gitleaks read the
staged content — only that content was there to read. The historical defect,
where real content was staged and the scanner looked elsewhere, is caught by
the configuration assertion in ``tests/test_secret_gate_config.py`` and by the
positive control in ``CLAUDE.md``, not by this hook.

Exit codes:
    0 — the staged diff is non-empty, the gate had real input
    1 — nothing staged: a green secret gate here would mean nothing
    2 — git could not be questioned; fail closed rather than assume
"""

from __future__ import annotations

import subprocess
import sys

# The empty tree's well-known hash — what to diff against before the first
# commit exists, when `HEAD` cannot be resolved.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def _git(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], capture_output=True, check=False)


def staged_bytes() -> int:
    """Size of the staged diff in bytes, as git itself reports it.

    ``--binary`` so a staged binary file counts as content rather than as an
    empty summary line.
    """
    has_head = _git("rev-parse", "--verify", "--quiet", "HEAD").returncode == 0
    args = (
        ["diff", "--cached", "--binary"]
        if has_head
        else ["diff", "--cached", "--binary", EMPTY_TREE]
    )
    result = _git(*args)
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(message or "git diff --cached failed")
    return len(result.stdout)


def main() -> int:
    try:
        size = staged_bytes()
    except (OSError, RuntimeError) as exc:
        print(f"staged-bytes-guard: could not read the staged diff: {exc}", file=sys.stderr)
        return 2

    if size > 0:
        return 0

    print(
        "\n"
        "  SECRET GATE — REFUSING A ZERO-BYTE SCAN\n"
        "\n"
        "  Nothing is staged, so the secret scanner has no content to read and\n"
        "  its green tick would mean only that it found nothing in nothing.\n"
        "\n"
        "  This repository has already shipped months of commits through a\n"
        "  secret gate that scanned ~0 bytes and exited 0. Reading a pass as\n"
        "  evidence is the failure; an empty scan is now red instead.\n"
        "\n"
        "  Two ordinary operations land here, and neither is a mistake:\n"
        "  an empty commit, and `git commit --amend` that changes only the\n"
        "  message. Both leave the index equal to HEAD, and git gives a\n"
        "  pre-commit hook no way to tell them apart. If that is what you are\n"
        "  doing, run it with the hooks off and say so in the message.\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
