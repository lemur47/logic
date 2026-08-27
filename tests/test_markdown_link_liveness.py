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
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$", re.MULTILINE)

# Anything with a scheme is somebody else's to keep alive; this check is about
# links whose target is a file in this repository.
#
# That boundary has a cost worth stating plainly, because this repository just
# paid it: the BINDING anonymisation gate now points at `agent-ops` over https,
# so it sits OUTSIDE this check. If that file is renamed or the branch moves,
# the gate goes dead again — silently, exactly as before, just one repository
# further away. Nothing here can close that; only a cross-repository check can.
EXTERNAL = ("http://", "https://", "mailto:")


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


def slug_of(heading: str) -> str:
    """A heading as its anchor, the way the renderers derive one.

    Lowercase, formatting characters dropped, everything that is not a word
    character or a space removed, spaces joined with hyphens.
    """
    plain = re.sub(r"[`*_]", "", heading)
    return re.sub(r"[^\w\s-]", "", plain).strip().lower().replace(" ", "-")


def anchors_in(document: Path) -> set[str]:
    """Every anchor a reader can actually land on in this document."""
    return {slug_of(text) for text in HEADING.findall(prose_of(document.read_text("utf-8")))}


def resolve(document: Path, target: str) -> Path:
    """Where a link target points, treating a leading `/` as the repository root.

    `Path.__truediv__` discards the left side when the right is absolute, so a
    root-relative link would otherwise resolve against the filesystem root and
    report as broken however correct it was.
    """
    if target.startswith("/"):
        return (REPO / target.lstrip("/")).resolve()
    return (document.parent / target).resolve()


def relative_links() -> list[tuple[Path, str, str]]:
    """Every (document, path, anchor) triple this check is responsible for.

    The path is empty for a same-document `#anchor` link; the anchor is empty
    for a plain file link.
    """
    found = []
    for tree in SEARCHED:
        for document in sorted((REPO / tree).glob("**/*.md")):
            for target in MARKDOWN_LINK.findall(prose_of(document.read_text(encoding="utf-8"))):
                if target.startswith(EXTERNAL):
                    continue
                path, _, anchor = target.strip().partition("#")
                if path or anchor:
                    found.append((document, path, anchor))
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
    assert "path" not in [path for _, path, _ in relative_links()], (
        "A code span is being parsed as a link. `content-cadence/SKILL.md` "
        "documents the image convention by writing `![...](path)` inline; "
        "flagging it would make this check wrong about the one document it was "
        "written for."
    )


def test_every_relative_link_resolves_to_a_tracked_file() -> None:
    """A link a clone cannot follow is a broken link, however it looks here."""
    tracked = tracked_paths()
    broken = [
        f"{document.relative_to(REPO)} -> {path}"
        for document, path, _ in relative_links()
        if path and resolve(document, path) not in tracked
    ]
    assert not broken, (
        "Relative links that do not resolve to a file git carries:\n  "
        + "\n  ".join(broken)
        + "\n\nA link that resolves only through `.claude/skills` symlinks is "
        "broken: it works for an agent session and fails for every clone. Point "
        "at the file in this repository, or at the full URL of the repository "
        "that now owns it."
    )


def test_every_anchor_lands_on_a_real_heading() -> None:
    """A link to a section that no longer exists is broken, not merely untidy.

    Checking only the file was the gap the PR auditor found in this very check:
    `../README.md#where-the-overlay-lives` would have passed on the strength of
    `README.md` existing, whatever became of the section. That is the same
    "resolves for nobody who checks" failure the file check exists to end, so
    leaving it to the file half would have been this test making the mistake it
    was written about.
    """
    tracked = tracked_paths()
    dangling = []
    for document, path, anchor in relative_links():
        if not anchor:
            continue
        target = resolve(document, path) if path else document
        # A missing or untracked file is the other test's finding, not this one.
        if target not in tracked or target.suffix != ".md":
            continue
        if anchor.lower() not in anchors_in(target):
            dangling.append(f"{document.relative_to(REPO)} -> {path}#{anchor}")

    assert not dangling, (
        "Links whose anchor matches no heading in the target document:\n  "
        + "\n  ".join(dangling)
        + "\n\nThe file resolves, so the other check here stays green — which is "
        "precisely why this one exists. Repoint the anchor, or restore the "
        "heading it was written against."
    )


def test_there_are_anchors_to_check() -> None:
    """Guard the guard: the anchor check over an empty set proves nothing."""
    with_anchors = [triple for triple in relative_links() if triple[2]]
    assert len(with_anchors) >= 4, (
        f"Only {len(with_anchors)} anchored links found. This repository is known "
        "to carry several, so the link parser has drifted and the anchor check "
        "above is now iterating almost nothing while reporting green."
    )
