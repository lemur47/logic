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


def test_no_arguments_fails_closed() -> None:
    """No argument is a misconfiguration, and a leak gate must not pass on one.

    This assertion was inverted on purpose. It previously required exit 0:
    latent, because pre-commit always supplies the message path — but an
    explicit fail-OPEN inside a gate whose whole job is to refuse. A hook wired
    up wrongly would have reported success on every commit, which is the exact
    shape of the `args` defect that made the secret gate a no-op for months.
    """
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, check=False
    )
    assert result.returncode != 0
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


# --- structural signals -------------------------------------------------------
#
# The entropy floor of 3.5 passes about one identifier in thirty-eight: 200,000
# synthetic identifiers of the real shape scored a mean of 3.847 with a first
# percentile of 3.455, so 2.63 per cent sit below it. Because the gitleaks rule
# shares the constant by design, that blind spot is identical on both gates
# rather than compensating.
#
# The signals below block the low tail WITHOUT touching the floor. That
# direction is deliberate and was reversed during review: demoting the floor to
# a warning and hard-blocking on structure instead would pass a LONE identifier
# in a commit message — the canonical leak this guard exists to stop — and would
# diverge the two gates, since adjacency and "a service URL in context" are
# inexpressible in a gitleaks TOML rule. Union, never replacement.
#
# The words below are ordinary English of the exact guarded shape, chosen from
# the measured low tail: `applicationlayers` scores 3.455, the first percentile
# itself. No high-entropy literal appears here either — see the module docstring.

LOW_TAIL = "applicationlayers"  # 3.455 — the measured first percentile
LOW_TAIL_2 = "recordsallocation"  # 3.337
LOW_TAIL_3 = "recommendationset"  # 3.337


def test_low_tail_id_blocks_when_a_service_url_is_in_context(tmp_path: Path) -> None:
    """Below the floor, but named next to the service it belongs to."""
    message = f"docs: the base at airtable.com is {LOW_TAIL}\n"
    result = run_commit_msg(tmp_path, message)
    assert result.returncode == 1, result.stdout
    assert "COMMIT BLOCKED" in result.stderr


def test_adjacent_low_tail_ids_block(tmp_path: Path) -> None:
    """Two guarded prefixes separated by nothing but a path separator.

    This is the copy-pasted-URL shape. Prose does not produce it: it needs two
    17-character guarded-prefix tokens with only punctuation between them.
    """
    result = run_commit_msg(tmp_path, f"chore: sync {LOW_TAIL}/{LOW_TAIL_2}\n")
    assert result.returncode == 1, result.stdout


def test_three_shape_tokens_block_even_when_spread_through_prose(tmp_path: Path) -> None:
    """One lookalike is a word; three in a message is a paste."""
    message = f"chore: reconcile {LOW_TAIL} with {LOW_TAIL_2} and then {LOW_TAIL_3}\n"
    result = run_commit_msg(tmp_path, message)
    assert result.returncode == 1, result.stdout


def test_two_lookalikes_in_ordinary_prose_still_pass(tmp_path: Path) -> None:
    """The false-positive boundary, asserted rather than assumed.

    Two low-entropy lookalikes separated by prose are not a leak, and a guard
    that blocked this sentence would teach people to reach for --no-verify.
    """
    message = "refactor: extract recrystallisation and selectAllElements into helpers\n"
    result = run_commit_msg(tmp_path, message)
    assert result.returncode == 0, result.stderr


def test_hook_denies_adjacent_low_tail_ids() -> None:
    """The union applies to the gh/git surface too, not only to commit messages."""
    assert denied(run_hook(bash_payload(f"gh pr create --body '{LOW_TAIL}/{LOW_TAIL_2}'")))


# --- --pr-text mode (the CI surface) ------------------------------------------
#
# This repository squash-merges, so the message that lands on `main` is composed
# in the GitHub web interface at merge time and passes through no local hook at
# all. The commit-msg hook is therefore blind to the one message that becomes
# the public record. This mode is what the merge gate runs over the pull
# request's title, body and commit messages.


def run_pr_text(*paths: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--pr-text", *[str(p) for p in paths]],
        capture_output=True,
        text=True,
        check=False,
    )


def test_pr_text_blocks_an_id_in_a_body(tmp_path: Path) -> None:
    body = tmp_path / "body.md"
    body.write_text(f"Closes the work tracked at {fake_id('rec')}.\n", encoding="utf-8")
    result = run_pr_text(body)
    assert result.returncode == 1
    assert "BLOCKED" in result.stderr


def test_pr_text_does_not_strip_markdown_headings(tmp_path: Path) -> None:
    """The one behaviour that must differ from commit-msg mode.

    Git strips lines beginning with '#' before committing, so scanning them
    there invents false positives. In a pull request body '#' opens a markdown
    heading and the line is published verbatim — stripping it would hand every
    author a one-character bypass of the gate.
    """
    body = tmp_path / "body.md"
    body.write_text(f"## Context\n# {fake_id('tbl')}\n", encoding="utf-8")
    assert run_pr_text(body).returncode == 1


def test_pr_text_passes_clean_files(tmp_path: Path) -> None:
    title = tmp_path / "title.txt"
    title.write_text("fix(pert): correct the beta weighting\n", encoding="utf-8")
    body = tmp_path / "body.md"
    body.write_text("## Summary\n\nRefer to the sprint housekeeping item.\n", encoding="utf-8")
    result = run_pr_text(title, body)
    assert result.returncode == 0, result.stderr


def test_pr_text_fails_closed_on_an_unreadable_file(tmp_path: Path) -> None:
    """Opposite of commit-msg mode, and deliberately so.

    There, git would have failed first on a message it cannot read. Here an
    unreadable file means the CI step is broken, and a gate that reports a clean
    pass it never performed is the whole failure class this work closes.
    """
    result = run_pr_text(tmp_path / "missing.md")
    assert result.returncode != 0
    assert "could not read" in result.stderr


def test_pr_text_scans_every_file_not_just_the_first(tmp_path: Path) -> None:
    """Guards against the mode being absent and the flag silently ignored.

    Without a real --pr-text mode the flag is filtered out as an option and the
    FIRST path is scanned as a commit message, which passes the single-file
    cases by accident. Putting the identifier in the second file is what makes
    the mode itself observable.
    """
    title = tmp_path / "title.txt"
    title.write_text("docs: tidy the README\n", encoding="utf-8")
    body = tmp_path / "body.md"
    body.write_text(f"Refs {fake_id('fld')}\n", encoding="utf-8")
    assert run_pr_text(title, body).returncode == 1


# --- the false-positive boundary, tightened after review ----------------------
#
# The first version of the adjacency signal allowed any whitespace in the gap,
# which made "a comma and a space" and "a newline and a bullet" count as
# adjacency. Both are ordinary formatting, and the module comment claimed
# prose could not produce the shape while these two cases plainly did. The gap
# is now URL punctuation only.


def test_a_markdown_bullet_list_of_lookalikes_is_not_adjacency(tmp_path: Path) -> None:
    message = f"docs: rename the helpers\n\n- {LOW_TAIL}\n- {LOW_TAIL_2}\n"
    result = run_commit_msg(tmp_path, message)
    assert result.returncode == 0, result.stderr


def test_a_comma_between_two_lookalikes_is_not_adjacency(tmp_path: Path) -> None:
    message = f"refactor: compare {LOW_TAIL}, {LOW_TAIL_2} for consistency\n"
    result = run_commit_msg(tmp_path, message)
    assert result.returncode == 0, result.stderr


def test_a_service_link_elsewhere_does_not_condemn_a_distant_lookalike(tmp_path: Path) -> None:
    """Proximity, not co-occurrence.

    A body that links to airtable.com documentation in one paragraph and uses a
    low-entropy lookalike in another is not a leak. The signal is a token
    sitting NEXT TO its own service name, which is what the comment always
    claimed and what the first implementation did not check.
    """
    message = (
        "docs: explain the plugin layer\n\n"
        "Background reading lives at https://airtable.com/developers/web/api.\n\n"
        "The helper is still called " + LOW_TAIL + " and is unrelated.\n"
    )
    result = run_commit_msg(tmp_path, message)
    assert result.returncode == 0, result.stderr


def test_a_service_url_still_blocks_the_id_it_carries(tmp_path: Path) -> None:
    """The signal that must survive the tightening."""
    message = f"docs: see https://airtable.com/{LOW_TAIL} for the schema\n"
    result = run_commit_msg(tmp_path, message)
    assert result.returncode == 1, result.stdout
