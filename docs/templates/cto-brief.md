# CTO Brief and Agent Report Template

Work Items are the contract between three parties: the **CTO** writes the brief,
the **DevSecOps agent** executes and reports, and the **CEO** reviews and merges.
This file is the shared, durable source of truth for that contract's structure —
so the interface lives in the repo rather than in any one party's private notes.

The Work Item's notes field carries these blocks in lifecycle order. A `[CTO BRIEF]`
is frozen once work starts; later blocks are **appended**, never rewritten over it.

All placeholders are generic. Use `recXXXXXXXXXXXXXX` or `<record-id>` for any
record reference — never a real base, record, or Work Item identifier.

## Work Item Lifecycle

1. **Backlog** — brief written, queued, not yet approved. Do not start.
2. **In Progress** — CEO or CTO approved and triggered. Safe to execute.
3. **Review** — agent finished, `[AGENT REPORT]` written, PR open. CTO reviews against the branch; CEO merges.
4. **Done** — PR merged.

## CTO Brief

Written by the CTO. Frozen once the agent starts work — annotate alongside it
with `[CTO NOTE]`, never edit in place.

```
[CTO BRIEF]
Type: implementation | exploration
Objective: one-line plain-English goal.
Context: what's true now that makes this WI necessary. Link prior WIs/Decisions (recXXXXXXXXXXXXXX).
Scope:
1. Concrete deliverable.
Out of scope:
- What this WI deliberately does not touch.
Constraints:
- Least-privilege, style rules, branch strategy (feature/* + PR, never main).
Depends-on: recXXXXXXXXXXXXXX or "None. Can start day 1."
Acceptance criteria:
- Measurable outcomes.
- [Content/docs] every inline image ref resolves to a committed file.
- [Content/docs] every cross-reference slug verified to exist.
- [Content/docs] British English; APA 7th title case for H1/H2.
```

`Type: implementation` — execute autonomously from the brief; ship it, report back.
`Type: exploration` — conversational work; engage interactively and iterate.

## Agent Report

Written by the agent on completion, appended below the brief. Two report blocks
on one Work Item is fine (e.g. a pre-execution resolution plus an execution-complete
report) — append, don't rewrite history.

```
[AGENT REPORT]
- PR + Branch (or "local-only").
- Tests - new + existing count.
- Files changed - short list.
- Cross-references checked - links/slugs/images verified (content WIs).
- Drift found - anything stale fixed that wasn't in the brief.
- Decisions - judgement calls made during execution.
- Issues / follow-ups - flag for CTO; candidate follow-up WIs are flagged, not created. Exception: env-friction / security reds blocking the commit may be spun into a scoped WI proactively, on the CTO's behalf.
- Deviations / bypasses - anything that departed from standard process (e.g. a pre-commit bypass), with the reason. None by default.
```

## CTO Review

Written by the CTO at the Review gate, before the CEO merges. Verifies the work
against the branch itself — not against the agent's own report.

```
[CTO REVIEW]
- Verified against the branch, not the report - claims checked in the repo.
- Acceptance criteria - each confirmed met / not met.
- [Content/docs] image refs resolve; cross-reference slugs exist; target pages render.
- Judgement calls - CC's execution decisions reviewed; any landing in CTO/CEO lanes (e.g. content authorship) flagged.
- Verdict - ready to merge / changes requested.
```

## CTO Note

An ad-hoc CTO annotation usable at any point — approval rationale, a buffer or
freeze exception, a scope or edit-site clarification. The header states its purpose.
It sits alongside a frozen `[CTO BRIEF]`; it never edits the brief.

```
[CTO NOTE - <purpose>]
- CTO annotation tied to the stated purpose.
```
