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
