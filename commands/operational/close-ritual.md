---
description: Close a programme session — write this session's changes back to shared memory, sweep README and agent instruction files for staleness, open a doc PR if needed, and log the handover.
argument-hint: "[programme or repo path] — optional; inferred from the working directory"
---

Run the **close** phase of the session ritual.

Load the `session-rituals` skill with the Skill tool, read its `CLOSE.md`
reference, and follow it step by step.

**Target:** $ARGUMENTS

If that is empty, resolve the programme from the current working directory using
the register in the skill's `CALIBRATION.local.md`.

Hold to these for this run:

- **Start from evidence, not recollection.** `git log`, the pull request list and
  the tracker decide what this session actually changed. If nothing changed, say
  so and conclude cheaply.
- **Rewrite hooks, not just bodies.** A fragment whose hook advertises last
  week's state is stale however accurate its body is.
- **Delegate the staleness sweep to the `cleanup` skill.** Do not improvise a
  second method. Scope it to this session's changes, and use the recorded sweep
  floor as `<since>` if one exists.
- **Doc corrections go on their own branch and through a pull request** — never
  the default branch, never merged by you, never carrying tracker record
  identifiers in the branch name, message, title or body. Let the repository's
  gates run.
- **Append the handover, never overwrite it.** Include what is in flight and who
  owns it, the floor for the next sweep, and any lesson that cost something. Put
  cross-machine items in the namespace the other machine boots from.
- **Report in the six-line shape, then stop.**

Anything unresolved goes on the `Open:` line with an owner. A red gate or an
unaddressed blocker is not something to close over silently.
