# Claude Skills

**Cognition as code, for conversational execution.**

Same math as the Python modules, different runtime. Skills encode decision-making logic as markdown instructions that Claude can execute in-context — no deployment, no infrastructure, no code.

## How to Use

1. Open a [Claude Project](https://claude.ai)
2. Add a `SKILL.md` file as project knowledge
3. Start estimating

That's it. Claude reads the skill, follows the formulas, and shows its work.

## Available Skills

| Skill | Module | Parity | Description |
|-------|--------|--------|-------------|
| [PERT](pert/SKILL.md) | `app/pert` | Full | Three-point estimation with reality adjustments |

## Planned Skills

| Skill | Module | Notes |
|-------|--------|-------|
| TCO | `app/tco` | Total Cost of Ownership with NPV adjustment |

## What Stays API-Only

Some modules involve iterative computation or stateful tracking that doesn't fit "soft" execution. These are available only via the FastAPI app.

| Module | Why API-Only |
|--------|-------------|
| EVM | Cumulative calculations across baselines and snapshots — too many interdependent variables for reliable in-context math |

If a skill can't do it reliably, it says so and points you to the repo.

## Design Principles

- **One skill, one decision function.** Each skill maps to one module.
- **Self-contained.** Formulas, domain context, and output format — all in one file.
- **Worked examples as guardrails.** Every skill includes pre-computed examples so Claude can self-check its math before presenting results.
- **Honest about limits.** Skills that can't reliably handle a calculation say so explicitly.
- **Dual input support.** Skills accept both severity (0.0–1.0) used by the Python API and direct multipliers used by the [pmo.run](https://pmo.run) web tools.

## Repo Structure

```
logic/
├── app/          # FastAPI service (deterministic execution)
├── examples/     # Standalone PoCs (prove the math)
├── skills/       # Claude Skills (conversational execution)
│   ├── pert/
│   │   └── SKILL.md
│   └── README.md
├── site/         # pmo.run website (interactive UI)
└── docs/         # Strategy and documentation
```

Same logic, four interfaces: code, API, conversation, browser.

## Contributing

Want to add a skill for a new decision function? Follow the pattern:

1. Build the standalone PoC in `examples/` first — prove the math
2. Write the skill with formulas, execution steps, and worked examples
3. Verify the skill output matches the Python module output
4. Add it to the table above

Keep it simple. If the math is too complex for reliable in-context execution, it belongs in `app/`, not `skills/`.
