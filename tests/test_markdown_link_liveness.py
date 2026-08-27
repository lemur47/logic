"""Relative links in `skills/` and `docs/` must resolve to a committed file.

The content pipeline's first gate is marked BINDING and linked as
`../anonymisation/SKILL.md`. That path stopped existing when the operational
skills moved to `agent-ops`, so a clone of this repository could not follow its
own mandatory control. Nothing noticed for weeks, because in an agent session
the link *appears* to work: `.claude/skills/anonymisation` is a symlink to the
`agent-ops` copy, which is a different path entirely. The control resolved for
the one reader holding the symlink and was dead for every human and every clone.

Two consequences shape this check.

**Tracked, not merely present.** Resolution is tested against `git ls-files`,
not the filesystem. A gitignored or untracked file exists locally and is absent
from a clone — which is the exact asymmetry that hid the original breakage, so a
check built on `Path.exists()` would reproduce it rather than catch it.

**Code spans are illustrations, not links.** `content-cadence/SKILL.md` teaches
the image convention by writing `![...](path)` inline. A checker that flags
documentation for demonstrating markdown gets switched off, and a switched-off
checker is worth less than none.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# The trees this check owns. Both carry durable claims that point at each other.
SEARCHED = ("skills", "docs")

MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`]*`")

# Anything with a scheme is somebody else's to keep alive; this check is about
# links whose target is a file in this repository.
EXTERNAL = ("http://", "https://", "mailto:", "#")


def tracked_paths() -> set[Path]:
    """Every file git actually carries, as absolute paths.

    `git ls-files` rather than a filesystem walk: a clone gets exactly this set,
    and a link is only live if it points inside it.
    """
    listing = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {(REPO / name).resolve() for name in listing.split("\0") if name}


def prose_of(text: str) -> str:
    """The document with its code removed — fenced blocks first, then spans."""
    kept, in_fence = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            kept.append(line)
    return INLINE_CODE.sub("", "\n".join(kept))


def relative_links() -> list[tuple[Path, str]]:
    """Every (document, target) pair this check is responsible for."""
    found = []
    for tree in SEARCHED:
        for document in sorted((REPO / tree).glob("**/*.md")):
            for target in MARKDOWN_LINK.findall(prose_of(document.read_text(encoding="utf-8"))):
                cleaned = target.split("#")[0].strip()
                if cleaned and not cleaned.startswith(EXTERNAL):
                    found.append((document, cleaned))
    return found


def test_there_are_relative_links_to_check() -> None:
    """Guard the guard: a check over an empty set passes for the wrong reason.

    If the glob, the tree names, or the link pattern ever stop matching, the
    assertion below iterates nothing and reports green — indistinguishable from
    every link being live.
    """
    assert len(relative_links()) >= 10, (
        "Fewer relative markdown links found than this repository is known to "
        "carry. The parser or the searched trees have drifted, and this check is "
        "now looking at almost nothing while still reporting green."
    )


def test_code_spans_are_not_read_as_links() -> None:
    """The `![...](path)` in the image convention is prose about markdown."""
    assert "path" not in [target for _, target in relative_links()], (
        "A code span is being parsed as a link. `content-cadence/SKILL.md` "
        "documents the image convention by writing `![...](path)` inline; "
        "flagging it would make this check wrong about the one document it was "
        "written for."
    )


def test_every_relative_link_resolves_to_a_tracked_file() -> None:
    """A link a clone cannot follow is a broken link, however it looks here."""
    tracked = tracked_paths()
    broken = [
        f"{document.relative_to(REPO)} -> {target}"
        for document, target in relative_links()
        if (document.parent / target).resolve() not in tracked
    ]
    assert not broken, (
        "Relative links that do not resolve to a file git carries:\n  "
        + "\n  ".join(broken)
        + "\n\nA link that resolves only through `.claude/skills` symlinks is "
        "broken: it works for an agent session and fails for every clone. Point "
        "at the file in this repository, or at the full URL of the repository "
        "that now owns it."
    )
