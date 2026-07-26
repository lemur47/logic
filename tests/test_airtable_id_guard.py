"""Tests for the Airtable ID leak guard.

Driven through ``subprocess`` rather than by importing the module: both modes
are defined by their process contract — an exit code for the ``commit-msg``
stage, a JSON decision on stdout for the hook — and importing would test the
functions while leaving the contract that git and Claude Code actually rely on
unverified.

**No ID-shaped literal appears in this file.** Identifiers are assembled from
fragments at runtime, because the guard under test also gates commits to its
own test suite — a realistic fixture written out in full would block the very
commit that adds it.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check-airtable-ids.py"


def fake_id(prefix: str) -> str:
    """Build a high-entropy identifier of the real shape, at runtime.

    Assembled from fragments so no single literal in this file matches the
    guard's own pattern. See the module docstring.
    """
    return prefix + "aB3" + "xK9" + "mQ2" + "pL7" + "wZ"


def run_commit_msg(tmp_path: Path, message: str) -> subprocess.CompletedProcess[str]:
    msg_file = tmp_path / "COMMIT_EDITMSG"
    msg_file.write_text(message, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(msg_file)],
        capture_output=True,
        text=True,
        check=False,
    )


def run_hook(payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--hook"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )


def bash_payload(command: str) -> dict[str, object]:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def denied(result: subprocess.CompletedProcess[str]) -> bool:
    """True if the hook emitted a deny decision.

    The hook always exits 0 — the decision is carried by the JSON, so asserting
    on the exit code would pass whether or not the guard did anything.
    """
    if not result.stdout.strip():
        return False
    decision = json.loads(result.stdout)
    return decision["hookSpecificOutput"]["permissionDecision"] == "deny"


# --- commit-msg mode ----------------------------------------------------------


def test_clean_message_passes(tmp_path: Path) -> None:
    result = run_commit_msg(tmp_path, "fix(pert): correct the beta weighting\n")
    assert result.returncode == 0


@pytest.mark.parametrize("prefix", ["app", "tbl", "fld", "rec", "viw", "sel"])
def test_every_guarded_prefix_blocks(tmp_path: Path, prefix: str) -> None:
    message = f"docs: fold in the review notes from {fake_id(prefix)}\n"
    result = run_commit_msg(tmp_path, message)
    assert result.returncode == 1
    assert "COMMIT BLOCKED" in result.stderr


def test_git_comment_lines_are_ignored(tmp_path: Path) -> None:
    """Git strips '#' lines before committing, so scanning them invents failures."""
    message = f"docs: tidy the README\n\n# on branch main\n# {fake_id('rec')}\n"
    result = run_commit_msg(tmp_path, message)
    assert result.returncode == 0


@pytest.mark.parametrize("word", ["recrystallisation", "selectAllElements"])
def test_low_entropy_lookalikes_pass(tmp_path: Path, word: str) -> None:
    """Ordinary English of the right shape must not block a commit.

    Both words are exactly 17 characters with a guarded prefix, so shape alone
    would reject them. A guard that blocks real prose is one people learn to
    bypass, which costs more than it saves.
    """
    result = run_commit_msg(tmp_path, f"refactor: extract {word} into a helper\n")
    assert result.returncode == 0, result.stderr


def test_unreadable_message_file_fails_open(tmp_path: Path) -> None:
    """Git would have failed first; the guard says so rather than dying silently."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path / "missing")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "could not read" in result.stderr


def test_no_arguments_prints_usage() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0
    assert "usage:" in result.stderr


# --- PreToolUse hook mode -----------------------------------------------------


def test_hook_denies_git_commit_carrying_an_id() -> None:
    result = run_hook(bash_payload(f"git commit -m 'ship the fix for {fake_id('rec')}'"))
    assert denied(result)


def test_hook_denies_gh_pr_and_gh_issue() -> None:
    assert denied(run_hook(bash_payload(f"gh pr create --title 'x' --body '{fake_id('tbl')}'")))
    assert denied(run_hook(bash_payload(f"gh issue create --body '{fake_id('fld')}'")))


def test_hook_scans_body_file_payloads(tmp_path: Path) -> None:
    """The ID is in a referenced file, not the command string."""
    body = tmp_path / "body.md"
    body.write_text(f"Closes the work tracked at {fake_id('rec')}.\n", encoding="utf-8")
    assert denied(run_hook(bash_payload(f"gh pr create --title 'x' --body-file {body}")))
    assert denied(run_hook(bash_payload(f"gh pr create --title 'x' --body-file={body}")))


def test_hook_catches_compound_commands() -> None:
    """A guarded command is caught wherever it sits in the stream, not just at the head."""
    result = run_hook(bash_payload(f"cd site && git commit -m 'refs {fake_id('rec')}'"))
    assert denied(result)


def test_hook_ignores_unguarded_commands() -> None:
    """Only artefact-creating commands are guarded — an ID in `echo` reaches nothing public."""
    assert not denied(run_hook(bash_payload(f"echo {fake_id('rec')}")))
    assert not denied(run_hook(bash_payload(f"grep -r {fake_id('rec')} .")))


def test_hook_ignores_non_bash_tools() -> None:
    payload = {"tool_name": "Read", "tool_input": {"file_path": f"/tmp/{fake_id('rec')}.md"}}
    assert not denied(run_hook(payload))


def test_hook_survives_a_malformed_payload() -> None:
    """A broken payload must not wedge the session — fall through to normal permissions."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--hook"],
        input="{not json",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert not result.stdout.strip()


def test_hook_survives_unbalanced_quotes() -> None:
    """shlex raises on unbalanced quotes; the guard falls back rather than crashing."""
    result = run_hook(bash_payload(f'git commit -m "unclosed {fake_id("rec")}'))
    assert result.returncode == 0
    assert denied(result)
