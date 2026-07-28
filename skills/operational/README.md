# Operational Skills

Skills that govern *how the work is done*, not decision-logic modules.

The skills in [`../`](../README.md) (PERT, EVM, TCO, Monte Carlo) encode executable maths that mirrors the Python modules — same logic, conversational runtime. The skills here are a different class: operational and editorial guardrails applied to the work itself, with no `app/` counterpart and no maths to verify.

| Skill | Purpose |
|-------|---------|
| [anonymisation](anonymisation/SKILL.md) | Extract lessons from real engagement experience without exposing the parties, before anything reaches a public surface. |
| [content-cadence](content-cadence/SKILL.md) | Turn one R&D artefact into one post (briefing or deep dive) plus a LinkedIn derivative, with the anonymisation gate and editorial conventions enforced. |
| [cleanup](cleanup/SKILL.md) | Sweep the surfaces that carry durable claims — README, agent instruction files, docs, shared memory — for statements reality has moved past, and correct them or mark them unverified. |
| [session-rituals](session-rituals/SKILL.md) | Open and close a working session: reconcile shared memory against repo and tracker ground truth, absorb what arrived, and leave a handover the next session can boot from. Invoked via [`/boot-ritual` and `/close-ritual`](../../commands/operational/README.md). |
| [ship](ship/SKILL.md) | Drive a change from working tree to merge-ready: reproduce the gates exactly as CI runs them, triage whose red it is, sequence the merge — and never make a check pass by weakening it. Invoked via [`/ship`](../../commands/operational/README.md). |

## Org calibration via local overlay

Each operational skill keeps **universal logic** in the tracked `SKILL.md` and **organisation-specific values** in a gitignored calibration overlay. No organisation's audience, escalation paths, or confidentiality constraints land in the public repo — the same public-logic / private-calibration split used for `core.py` and proprietary `plugins/` across this codebase.

### Where the overlay lives

Skills resolve their overlay in this order and take the first hit:

```
1. <repo>/.claude/calibration/<skill>.local.md    # this repository's own values
2. ~/.claude/calibration/operational.local.md     # machine-wide, all skills
3. skills/operational/<skill>/CALIBRATION.local.md  # beside the skill
```

Rung 3 is the simplest and is all a single-repository setup needs. Rung 2 matters once one machine works across several repositories: skills reach the machine via a symlink or a clone, so an overlay that only ever sits beside the skill describes whichever repository happened to author it, and the others get either nothing or another repository's values. A machine-wide register keyed by working directory serves them all from one place — and, being outside every tree, it does not travel with a repository that is handed over.

Rung 1 wins where a repository's values are genuinely its own and should move with it.

Whichever rung you use, the overlay is **never committed** — not to a public repository and not to a private one. It typically carries tracker identifiers and namespaces, and the value of the split disappears the moment a copy is versioned.

A minimal overlay names your core audience, your confidentiality sign-off owner, the agreements that bind you, and your default fallback when an example fails the rule.
