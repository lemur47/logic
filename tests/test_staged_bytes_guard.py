"""Tests for the zero-byte scan guard.

Driven through ``subprocess`` against **real** temporary git repositories. The
thing under test is a claim about what git reports, so mocking git would leave
exactly the risky boundary unexercised — the guard would then be verified
against my model of `git diff --cached` rather than against git.

Its own docstring says the hook does not prove gitleaks read the staged
content. These tests hold it to the narrower claim it does make.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check-staged-bytes.py"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def new_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Test")
    return repo


def run_guard(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=cwd, capture_output=True, text=True, check=False
    )


def test_staged_content_passes(tmp_path: Path) -> None:
    repo = new_repo(tmp_path)
    (repo / "a.txt").write_text("hello\n", encoding="utf-8")
    git(repo, "add", "a.txt")
    git(repo, "commit", "-qm", "first")
    (repo / "a.txt").write_text("hello again\n", encoding="utf-8")
    git(repo, "add", "a.txt")
    assert run_guard(repo).returncode == 0


def test_nothing_staged_is_red(tmp_path: Path) -> None:
    """The whole point: a scan over nothing must not read as a pass."""
    repo = new_repo(tmp_path)
    (repo / "a.txt").write_text("hello\n", encoding="utf-8")
    git(repo, "add", "a.txt")
    git(repo, "commit", "-qm", "first")
    result = run_guard(repo)
    assert result.returncode == 1
    assert "ZERO-BYTE SCAN" in result.stderr


def test_first_commit_of_a_repository_passes(tmp_path: Path) -> None:
    """Before any commit exists there is no HEAD to diff against.

    The guard falls back to the empty tree. Without that branch every initial
    commit would be blocked by a hook meant to catch the opposite case.
    """
    repo = new_repo(tmp_path)
    (repo / "a.txt").write_text("hello\n", encoding="utf-8")
    git(repo, "add", "a.txt")
    assert run_guard(repo).returncode == 0


def test_a_staged_binary_file_counts_as_content(tmp_path: Path) -> None:
    """`--binary`, so a binary blob is content rather than an empty summary."""
    repo = new_repo(tmp_path)
    (repo / "a.txt").write_text("hello\n", encoding="utf-8")
    git(repo, "add", "a.txt")
    git(repo, "commit", "-qm", "first")
    (repo / "image.bin").write_bytes(bytes(range(256)))
    git(repo, "add", "image.bin")
    assert run_guard(repo).returncode == 0


def test_outside_a_repository_fails_closed(tmp_path: Path) -> None:
    """git could not be questioned, so the guard refuses rather than assumes.

    Exit 2, not 1 — a different state from "nothing staged", and both are
    non-zero because a gate that cannot see must never report a pass.
    """
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    result = run_guard(plain)
    assert result.returncode == 2
    assert "could not read the staged diff" in result.stderr


def test_amending_only_a_message_is_blocked_and_that_is_the_known_cost(tmp_path: Path) -> None:
    """The tradeoff this guard carries, asserted so it cannot change silently.

    `git commit --amend` to fix a typo in a message stages nothing, so the
    index equals HEAD and the guard fires — the same state as `--allow-empty`.
    The two are indistinguishable from inside a pre-commit hook: git exposes no
    signal that an amend is in progress, and both present as "index equals
    HEAD".

    Raised by the automated reviewer and confirmed rather than dismissed. It is
    a real cost: friction on a legitimate operation is what teaches people to
    reach for --no-verify. It is recorded here, and named in the hook's own
    output, rather than papered over — whether the guard is worth this cost is
    the approver's call, not something to settle by loosening the test.
    """
    repo = new_repo(tmp_path)
    (repo / "a.txt").write_text("hello\n", encoding="utf-8")
    git(repo, "add", "a.txt")
    git(repo, "commit", "-qm", "typoed messge")
    assert run_guard(repo).returncode == 1
