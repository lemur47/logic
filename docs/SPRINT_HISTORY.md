# pmo.run — Sprint History

Sprint actuals from go-to-market execution. Forward-looking phasing lives in the Monetisation Strategy section of [`STRATEGY.md`](STRATEGY.md).

---

## Go-to-Market: Sprint Plan

Philosophy and principles are stable. Strategy and design can be pivoted and tweaked during PoC phases.

### Sprint 1 (March 2026) — PERT + EVM Foundations ✅

Shipped PERT module (standalone PoC + FastAPI, 7 endpoints), EVM calculations and baseline module (8 endpoints), full test suite with mutation testing, CI/CD pipeline with gitleaks/opengrep/osv-scanner/ruff/pyright. Published TCO case study blog post (EN/JA).

### Sprint 2 (March 2026) — Site + Content ✅

Launched pmo.run Astro site with EN/JA i18n. Published SIer-focused blog posts (JA). Interactive PERT tool page. Claude Skills for PERT and EVM.

### Sprint 3 (March 2026) — EVM Baselines + Docs ✅

EVM baseline evaluate/snapshot endpoints. API documentation site. Pre-commit security hooks hardened. PERT scenario persistence (CRUD).

### Sprint 4 (March 2026) — Bayesian + Research ✅

Bayesian estimation calibration module (standalone PoC + 10 FastAPI endpoints). Five research decisions anchored. "Cognition as Code" blog post (EN/JA). BlogCta component.

### Sprint 5 (March 2026) — Hardening + Content ✅

319 tests passing. Bayesian CRUD with context/observation persistence. Plugin architecture defined (core → calibration → plugins). Strategy doc and architecture finalised. Test count: 319.

### Sprint 6 (March–April 2026) — Monte Carlo + Hardening ✅

Monte Carlo module shipped end-to-end through the standard pipeline: standalone PoC (PR #35), FastAPI integration with 72 new tests for 391 total (PR #36), Skill (PR #38), Monte Carlo blog EN + JA (PR #42), API docs v2 (PR #44). API docs also extended for Bayesian (PR #33). CI migrated to Node.js 22+ (PR #32). Five reactive security patches landed without scope collapse: Astro security fix (PR #34), vite path traversal (PR #40), defu prototype pollution, `.npmrc` supply-chain hardening, and a late-landing Astro 5 → 6 upgrade for the `define:vars` XSS (PR #45). Dirichlet-Monte Carlo productisation architecture decided (Decision recYXe6htpG3NYcwf). Sprint ran 28 days against an 18-day plan; layered-mandate blog posts (EN + JA) carried to Sprint 7 to protect flywheel cadence.

### Sprint 7 (April 2026) — Information Staleness + Compact Cadence ✅

First sprint under the new compact format — capped at 8 Work Items over 3–4 days, deliberately built to flush information staleness and reduce unnecessary context burn at session boot. Carried layered-mandate blog posts shipped (EN + JA, PR #48). Standalone test suites added for Bayesian (354 tests) and EVM (351 tests), closing a long-standing gap in `examples/standalone/` (PR #46). Workflow infrastructure overhaul: CLAUDE.md refreshed and split — operational notes moved into a gitignored `CLAUDE-internal.md` (Work Item Protocol, sprint conventions, Airtable reference) so the in-repo file stays code-focused (PR #47); claude.ai project instructions revised for boot reliability; bwrap sandbox restrictions removed for `git` and `gh` to remove per-command friction. Dirichlet-Monte Carlo productisation architecture review delivered as a scope doc, queuing implementation for Sprint 8. Closing housekeeping WI refreshed README and this strategy doc, and migrated `astro:content`'s `z` re-export to a direct `zod` import to clear the Astro 6 deprecation hint left by PR #45.
