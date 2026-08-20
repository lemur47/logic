# Operational Skills

Skills that govern *how the work is done*, not decision-logic modules.

The skills in [`../`](../README.md) (PERT, EVM, TCO, Monte Carlo) encode executable maths that mirrors the Python modules — same logic, conversational runtime. The skills here are a different class: operational and editorial guardrails applied to the work itself, with no `app/` counterpart and no maths to verify.

| Skill | Purpose |
|-------|---------|
| [content-cadence](content-cadence/SKILL.md) | Turn one R&D artefact into one post (briefing or deep dive), plus a social derivative where the calibration overlay scopes one in, with the anonymisation gate and editorial conventions enforced. |

## Most of This Set Now Lives in `agent-ops`

Four skills that used to live here — **`anonymisation`, `cleanup`, `session-rituals` and `ship`** — moved to
**[github.com/lemur47/agent-ops](https://github.com/lemur47/agent-ops)** (public, MIT), together with the
`/boot-ritual`, `/close-ritual` and `/ship` commands.

They moved because they were never about this repository. They govern how an agent works — opening and closing a
session, sweeping stale claims, driving a change to merge-ready, keeping engagement material out of public
writing — and none of that depends on decision maths. Kept here, they were reachable only by whoever had this
repository checked out, and they carried the awkwardness of a general method living inside one product's tree.

`content-cadence` stays. It has forked between two working trees with improvements on both sides, so reconciling
it is a rewrite rather than a move, and it waits on its own piece of work.

If you arrived from a blog post or a link expecting one of the moved skills, `agent-ops` is where it is now.

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

**An overlay travels with its skill.** A rung-3 overlay sits *inside* the skill directory, so moving the skill
moves the overlay with it — and deleting the skill deletes the overlay. That is easy to miss when a skill is
relocated, and the failure is silent: the skill resolves no overlay at all and stops, or falls back, without
anything announcing that its calibration went missing. Check the resolved rung after any move.
