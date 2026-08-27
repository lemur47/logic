"""The reviewer prompt exists twice; this stops the copies drifting apart.

`automation/pr-auditor/reviewer-prompt.md` is the authoritative copy — the one a
human reviews. `automation/pr-auditor/scenario.blueprint.json` carries a
transcription of it, because that is what the hosted automation actually sends.

Two documents describing one truth, with nothing forcing them to agree, is how a
control quietly stops matching the thing it controls. The prompt is a security
control: it is what tells the reviewer the diff is untrusted data. A drift here
does not fail loudly, it just means the deployed reviewer is running
instructions nobody reviewed.

Comparing them by eye does not work. That is the lesson `site/src/lib/round.ts`
earned — a rounding-mode divergence survived a line-by-line review because the
two implementations *looked* alike. So compare the bytes.
"""

import json
import re
from pathlib import Path

AUTOMATION = Path(__file__).resolve().parent.parent / "automation" / "pr-auditor"
PROMPT_DOC = AUTOMATION / "reviewer-prompt.md"
BLUEPRINT = AUTOMATION / "scenario.blueprint.json"

# The prompt lives in the single ```text fence under the "## The prompt" heading.
PROMPT_FENCE = re.compile(r"## The prompt\n\n```text\n(.*?)\n```", re.DOTALL)


def authoritative_prompt() -> str:
    """The reviewer prompt as a human reviews it, from the markdown document."""
    match = PROMPT_FENCE.search(PROMPT_DOC.read_text(encoding="utf-8"))
    assert match is not None, (
        f"No ```text fence found under '## The prompt' in {PROMPT_DOC.name}. "
        "The prompt is the control; if this heading moved, this test stopped "
        "checking anything."
    )
    return match.group(1)


def deployed_prompts() -> list[str]:
    """Every system prompt the exported scenario would actually send."""
    blueprint = json.loads(BLUEPRINT.read_text(encoding="utf-8"))
    return [
        module["mapper"]["system"]
        for module in blueprint["flow"]
        if isinstance(module.get("mapper"), dict) and "system" in module["mapper"]
    ]


def test_blueprint_carries_exactly_one_system_prompt() -> None:
    """Guard the guard: a comparison against nothing passes for the wrong reason.

    If the scenario is rebuilt so the prompt lands somewhere this test does not
    look, `deployed_prompts()` returns an empty list and the equality check below
    would iterate zero times and pass — a green result meaning "not checked".
    """
    assert len(deployed_prompts()) == 1


def test_deployed_prompt_matches_the_authoritative_copy() -> None:
    """The transcription in the blueprint is byte-identical to the document."""
    expected = authoritative_prompt()
    for deployed in deployed_prompts():
        assert deployed == expected, (
            "The system prompt in scenario.blueprint.json has drifted from "
            "reviewer-prompt.md. The markdown document is authoritative: re-export "
            "the scenario after correcting it there, rather than editing the "
            "blueprint to match."
        )


def test_untrusted_diff_markers_survive_in_the_deployed_prompt() -> None:
    """The delimiters are defence in depth, but their absence should still fail.

    An edit that drops them leaves a prompt that still reads sensibly and no
    longer tells the reviewer where the untrusted region ends.
    """
    for deployed in deployed_prompts():
        assert "<<<UNTRUSTED_DIFF>>>" in deployed
        assert "<<<END_UNTRUSTED_DIFF>>>" in deployed


# ═══════════════════════════════════════════════════════════════════════════════
# The user turn — the half nothing guarded
#
# The system prompt is pinned byte for byte above. The user turn was not, and it
# is where the untrusted-diff markers live: delete them and the system prompt
# still promises the reviewer a delimited region that no longer exists. That
# pairing drifted twice inside one pull request, and `reviewer-prompt.md`
# documented a turn that had not shipped for weeks.
#
# Shape, not bytes. The document describes the turn with placeholders where the
# deployed turn carries Make expressions, so a byte comparison could only be made
# to pass by making the document useless to a human. These assert the properties
# that make the reviewer non-silent and the trusted half trustworthy.
# ═══════════════════════════════════════════════════════════════════════════════

DIFF_CAP = 200000

OPENING_MARKER = "<<<UNTRUSTED_DIFF>>>"
CLOSING_MARKER = "<<<END_UNTRUSTED_DIFF>>>"

# The split argument is anchored to a newline so a "diff --git " appearing inside
# a hunk body cannot be counted as a file header.
ANCHORED_SPLIT = 'split(toString(2.data); newline + "diff --git ")'


def deployed_user_turns() -> list[str]:
    """Every user message the exported scenario would actually send."""
    blueprint = json.loads(BLUEPRINT.read_text(encoding="utf-8"))
    return [
        message["content"]
        for module in blueprint["flow"]
        if isinstance(module.get("mapper"), dict)
        for message in module["mapper"].get("messages", [])
        if message.get("role") == "user"
    ]


def module_body(module_id: int) -> str:
    """The `body` mapper of one module, by id."""
    blueprint = json.loads(BLUEPRINT.read_text(encoding="utf-8"))
    for module in blueprint["flow"]:
        if module.get("id") == module_id:
            return module["mapper"]["body"]
    raise AssertionError(f"No module {module_id} in the blueprint.")


def test_blueprint_carries_exactly_one_user_turn() -> None:
    """Guard the guard, as for the system prompt: assert on something."""
    assert len(deployed_user_turns()) == 1


def test_the_untrusted_region_is_delimited_at_both_ends() -> None:
    """A single leading marker can be escaped by diff content closing its own.

    Matched markers mean the model can see where the untrusted region ends, so
    text claiming to be outside it while sitting inside it is visibly
    inconsistent. The system prompt names both markers; if the turn stops
    emitting them, the prompt is promising a structure that is not there.
    """
    turn = deployed_user_turns()[0]
    for marker in (OPENING_MARKER, CLOSING_MARKER):
        assert turn.count(marker) == 1, (
            f"The user turn does not carry exactly one {marker}. The system "
            "prompt tells the reviewer the diff sits between both markers; "
            "without them it is describing a region that does not exist."
        )
    assert turn.index(OPENING_MARKER) < turn.index(CLOSING_MARKER)


def test_the_trusted_half_is_not_built_from_the_webhook_payload() -> None:
    """Everything above the opening marker reads as operator-authored.

    The head SHA and changed-file count are re-fetched from the GitHub API
    (module 8) rather than taken from the webhook body, so a caller cannot place
    chosen text in the region the system prompt vouches for. This asserts the
    invariant rather than the fix, so a later edit cannot quietly reinstate the
    payload fields.
    """
    trusted_half = deployed_user_turns()[0].split(OPENING_MARKER)[0]
    leaked = [ref for ref in ("1.pull_request", "1.title", "1.body") if ref in trusted_half]
    assert not leaked, (
        f"The operator-authored half interpolates webhook-supplied fields: {leaked}. "
        "Those are attacker-controllable in principle and sit in the region the "
        "system prompt tells the reviewer to trust. Re-fetch them from the API "
        "(module 8) instead."
    )


def test_the_pull_request_title_and_body_stay_out_of_the_prompt() -> None:
    """Author-controlled prose has no place in either half.

    In the trusted half it is an injection route. In the untrusted half it would
    be reviewed as though it were code. It is neither, so it is not sent.
    """
    turn = deployed_user_turns()[0]
    for field in ("pull_request.title", "pull_request.body"):
        assert field not in turn, (
            f"The user turn now interpolates {field}. That is author-controlled "
            "prose, not diff content, and nothing above the marker may be."
        )


def test_the_diff_cap_is_stated_and_self_consistent() -> None:
    """The cap appears twice: once to measure, once to send.

    They must be the same number. If the sent slice were larger than the measured
    one, the "diff characters included below" line would understate what the model
    was shown, and the reviewer would be told the truncation was worse than it was.
    """
    turn = deployed_user_turns()[0]
    assert turn.count(f"0; {DIFF_CAP}") == 2, (
        f"Expected the {DIFF_CAP}-character cap exactly twice in the user turn — "
        "once measuring what is included and once taking the slice. A mismatch "
        "makes the reported figure describe a different string from the sent one."
    )


def test_the_file_header_count_is_anchored_to_a_newline() -> None:
    """This is the check that shipped broken twice — pin its exact form.

    Counting the PARTS of the split, not the separators, is what makes the
    number comparable with GitHub's `changed_files`. Verified against five real
    diffs: parts equals changed_files, separators equals changed_files minus one.
    The split is anchored to a preceding newline so that a "diff --git " written
    inside a hunk body is not counted as a file header.
    """
    turn = deployed_user_turns()[0]
    assert ANCHORED_SPLIT in turn, (
        "The file-header count is no longer the anchored split. This expression "
        "has shipped broken twice, both times from reasoning about it instead of "
        "running it — if you change it, run it against a real diff first and "
        "check parts against the API's changed_files."
    )
    # The WHOLE interpolation, closing braces included. A substring test for
    # `length(split(...))` alone still matches `length(split(...)) - 1` — which
    # is the separators form, the exact regression this pins against. That gap
    # was found by canary rather than by reading, and it is why the closing
    # `}}` is part of the expected string.
    assert "{{" + f"length({ANCHORED_SPLIT})" + "}}" in turn, (
        "The header count must be exactly length(split(...)) — the number of "
        "PARTS, with no arithmetic applied. Counting separators, or subtracting "
        "one, gives a number one below the file count and makes every complete "
        "diff look truncated to the reviewer."
    )


def test_the_incompleteness_notice_still_compares_the_stop_reason() -> None:
    """Module 7's body, not the user turn — the brief named the wrong module.

    Without this comparison a cut-off review is posted looking exactly like a
    finished one, which is the silent-failure class the reviewer is itself told
    to report.
    """
    body = module_body(7)
    assert "3.data.stop_reason" in body and "end_turn" in body, (
        "Module 7 no longer compares the model's stop_reason against end_turn. "
        "A truncated review would then be posted with no warning that the "
        "findings are not exhaustive."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# The README's numbers, tied to the blueprint that produces them
#
# The design document restates figures the blueprint owns: the model, the output
# ceiling, the diff cap, and the module count that sets the operations bill. A
# restated number drifts the moment the scenario changes, silently, because
# nothing reads both. The module count read "seven" for a day after the metadata
# fetch landed — which is this row's own worked example.
# ═══════════════════════════════════════════════════════════════════════════════

README = AUTOMATION / "README.md"


def blueprint_flow() -> list[dict]:
    return json.loads(BLUEPRINT.read_text(encoding="utf-8"))["flow"]


def review_request_mapper() -> dict:
    """Module 6's mapper — the Anthropic request the scenario builds."""
    return next(m for m in blueprint_flow() if m["id"] == 6)["mapper"]


_WORDS = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
]


def spelled(count: int) -> str:
    """The README writes counts as words; fall back to digits past the list.

    A plain dict lookup raised KeyError the moment a canary removed a module,
    turning a legible assertion into a traceback. Same shape as the failure the
    auditor found in the rounding guard: the diagnostic must survive the case it
    is diagnosing.
    """
    return _WORDS[count] if 0 <= count < len(_WORDS) else str(count)


def test_the_readme_module_count_matches_the_blueprint() -> None:
    """The count that sets the operations bill, spelled as the README spells it."""
    modules = len(blueprint_flow())
    readme = README.read_text(encoding="utf-8")
    assert f"The chain is {spelled(modules)} modules" in readme, (
        f"The blueprint has {modules} modules but the README does not say "
        f"'{spelled(modules)} modules'. Every module is one operation, so "
        "this number is the monthly bill; a stale one under-counts it."
    )
    assert f"costs **{spelled(modules)} operations**" in readme


def test_the_readme_failure_path_count_matches_the_error_handler() -> None:
    """Trigger, the failed fetch itself, and every handler module after it."""
    diff_fetch = next(m for m in blueprint_flow() if m["id"] == 2)
    on_failure = 2 + len(diff_fetch.get("onerror", []))
    readme = README.read_text(encoding="utf-8")
    assert f"failed diff fetch costs **{spelled(on_failure)}**" in readme, (
        f"A failed diff fetch now costs {on_failure} operations "
        f"({spelled(on_failure)}), which the README does not state. The "
        "error path bills too, and it bills on exactly the large pull requests "
        "most likely to trigger it."
    )


def test_the_readme_model_and_ceiling_match_the_request() -> None:
    """Two figures a reader will quote back when reasoning about cost."""
    mapper = review_request_mapper()
    readme = README.read_text(encoding="utf-8")
    assert f"`{mapper['model']}`" in readme, (
        f"The blueprint sends {mapper['model']}, which the README does not name."
    )
    assert f"| `max_tokens` | {mapper['max_tokens']} |" in readme, (
        f"The blueprint sets max_tokens={mapper['max_tokens']}; the README's "
        "configuration table says otherwise. That table is what someone reads "
        "before deciding whether a cut-off review was expected."
    )


def test_the_readme_diff_cap_matches_the_user_turn() -> None:
    """Stated with a thousands separator, as prose does."""
    readme = README.read_text(encoding="utf-8")
    assert f"{DIFF_CAP:,}-character cap" in readme, (
        f"The user turn caps the diff at {DIFF_CAP:,} characters and the README "
        "does not say so. This is the number that decides whether a large pull "
        "request is reviewed whole."
    )
