# Operational Skills

Skills that govern *how the work is done*, not decision-logic modules.

The skills in [`../`](../README.md) (PERT, EVM, TCO, Monte Carlo) encode executable maths that mirrors the Python modules — same logic, conversational runtime. The skills here are a different class: operational and editorial guardrails applied to the work itself, with no `app/` counterpart and no maths to verify.

| Skill | Purpose |
|-------|---------|
| [anonymisation](anonymisation/SKILL.md) | Extract lessons from real engagement experience without exposing the parties, before anything reaches a public surface. |
| [content-cadence](content-cadence/SKILL.md) | Turn one R&D artefact into one post (briefing or deep dive) plus a LinkedIn derivative, with the anonymisation gate and editorial conventions enforced. |

## Org calibration via local overlay

Each operational skill keeps **universal logic** in the tracked `SKILL.md` and **organisation-specific values** in a co-located `CALIBRATION.local.md`. The overlay is gitignored (`*.local.md`), so no organisation's audience, escalation paths, or confidentiality constraints land in the public repo — the same public-logic / private-calibration split used for `core.py` and proprietary `plugins/` across this codebase.

To adopt a skill, create your own overlay alongside it:

```
skills/operational/<skill>/
├── SKILL.md              # tracked, organisation-neutral
└── CALIBRATION.local.md  # gitignored, your organisation's values
```

A minimal overlay names your core audience, your confidentiality sign-off owner, the agreements that bind you, and your default fallback when an example fails the rule.
