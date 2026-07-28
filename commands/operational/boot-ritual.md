---
description: Boot a programme session — read shared memory, verify it against repo and tracker ground truth, correct what drifted, check inbound PRs, then report briefly and prepare planning or execution.
argument-hint: "[programme or repo path] — optional; inferred from the working directory"
---

Run the **boot** phase of the session ritual.

Load the `session-rituals` skill with the Skill tool, read its `BOOT.md`
reference, and follow it step by step. Do not summarise it from memory — the
whole point of the ritual is that it is executed rather than recalled.

**Target:** $ARGUMENTS

If that is empty, resolve the programme from the current working directory using
the calibration register, found via the lookup order in the skill's `SKILL.md`.
If the directory matches no row, or more than one, ask rather than assume.

Hold to these for this run:

- **Read the memory layer before looking at the repo.** Reading ground truth
  first turns the reconciliation step into confirmation of whatever you happened
  to look at.
- **Correct the store where it contradicts an authoritative surface** — but
  verify first, rewrite the hook as well as the body, and append rather than
  overwrite on anything that is a record.
- **Classify inbound work; do not act on it.** No merging, no starting approved
  work, no patching a defect from inside the boot.
- **Report in the six-line shape, then stop.** One short line per correction
  below the block, and nothing else. Detail belongs in the store.

Finish by stating whether this session is planning or execution, and the single
thing it should start with.
