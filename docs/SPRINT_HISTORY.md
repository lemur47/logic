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

Monte Carlo module shipped end-to-end through the standard pipeline: standalone PoC (PR #35), FastAPI integration with 72 new tests for 391 total (PR #36), Skill (PR #38), Monte Carlo blog EN + JA (PR #42), API docs v2 (PR #44). API docs also extended for Bayesian (PR #33). CI migrated to Node.js 22+ (PR #32). Five reactive security patches landed without scope collapse: Astro security fix (PR #34), vite path traversal (PR #40), defu prototype pollution, `.npmrc` supply-chain hardening, and a late-landing Astro 5 → 6 upgrade for the `define:vars` XSS (PR #45). Dirichlet-Monte Carlo productisation architecture decided and captured in the internal Decisions record. Sprint ran 28 days against an 18-day plan; layered-mandate blog posts (EN + JA) carried to Sprint 7 to protect flywheel cadence.

### Sprint 7 (April 2026) — Information Staleness + Compact Cadence ✅

First sprint under the new compact format — capped at 8 Work Items over 3–4 days, deliberately built to flush information staleness and reduce unnecessary context burn at session boot. Carried layered-mandate blog posts shipped (EN + JA, PR #48). Standalone test suites added for Bayesian (354 tests) and EVM (351 tests), closing a long-standing gap in `examples/standalone/` (PR #46). Workflow infrastructure overhaul: CLAUDE.md refreshed and split — operational notes moved into a gitignored `CLAUDE-internal.md` (Work Item Protocol, sprint conventions, Airtable reference) so the in-repo file stays code-focused (PR #47); claude.ai project instructions revised for boot reliability; bwrap sandbox restrictions removed for `git` and `gh` to remove per-command friction. Dirichlet-Monte Carlo productisation architecture review delivered as a scope doc, queuing implementation for Sprint 8. Closing housekeeping WI refreshed README and this strategy doc, and migrated `astro:content`'s `z` re-export to a direct `zod` import to clear the Astro 6 deprecation hint left by PR #45.

### Sprint 8 (May 2026) — Dirichlet Drift + MCP Prototype ✅

Compact 6-WI / 3-day sprint validating the R&D flywheel end to end on the Dirichlet-Monte Carlo drift work: standalone PoC (PR #50), core + FastAPI integration (PR #51), and an MCP prototype exposing five decision-logic tools (PR #52) — the first appearance of the exploration-then-implementation pattern, where design decisions are locked in an exploration Work Item and executed in one clean commit. The Dirichlet drift explainer shipped EN + JA (PR #53), and the monolithic strategy document was decomposed into the focused STRATEGY.md / DESIGN.md / CONTENT_FLYWHEEL.md set (PR #54). 87 new tests across the three surfaces. First sprint to run the entire GitHub Flow with zero sandbox bypasses — Sprint 7's environment investments paid out completely, and "one core, three surfaces" (standalone, FastAPI, MCP) became code reality rather than strategy prose.

### Sprint 9 (May 2026) — Site Renewal + MCP Server v0.1 ✅

Wide 8-WI sprint, stretched to a week by client-side scheduling rather than team throughput. The website's visual renewal landed (design tokens, new chrome, /about page — PR #56) alongside the LLM-first content architecture decision, frontend CVE bumps (PR #55), and the anonymisation skill that now gates every piece of client-derived content (PR #57). MCP server v0.1 shipped with four classic PMO tools and shared schemas (PR #59), flanked by the hidden-tax and MCP release blog posts EN + JA (PRs #58, #61). Two reactive hotfixes closed the loop: a source-first install correction when PyPI publishing was deferred (PR #60), and removal of the external-PR invitation from the release post's CTA (PR #62) — extending the supply-chain posture into content review itself. Key process lesson recorded: an artefact published is a separate deliverable from code merged, and earns its own dependency line.

### Sprint 10 (June 2026) — pmorun-mcp on PyPI ✅

Laser-focused product-delivery sprint: pmorun-mcp published to PyPI as a lean stdio package with OIDC trusted publishing (PR #63), the canonical install flipped to `uvx pmorun-mcp` (PR #65), the MCP server documented on-site EN + JA (PR #67), and the legacy-ERP integration worked example shipped EN + JA (PR #68). Environment and process hardening rode along: uv.lock tracked and enforced in CI via `uv sync --frozen` (PR #66), and the CTO brief / agent report template promoted from private notes to a committed public doc (PR #70). The ~15% buffer absorbed two mid-sprint additions — a `depends_on` behaviour verification (PR #64) and a high-severity esbuild override (PR #69) — closing at 7/7 over six days, judged an acceptable security-red-week overrun. The dual-product packaging squeeze surfaced by PR #63 (lean MCP runtime vs full web stack in one pyproject) seeded the agreed uv-workspace direction.

### Sprint 11 (June 2026) — Post-Ship Consolidation + Dogfooding ✅

Interval-style consolidation sprint, 8/8 in three days: 0.1.1 published (PR #73) and every surface pointed at `uvx pmorun-mcp@0.1.1` (PRs #74, #75); security hardening made the SAST gate real (it had been a silent no-op), SHA-pinned every GitHub Action including the OIDC publish job, cleared live osv/npm-audit reds, and established the Dependabot cadence for the uv lockfile and Actions (PRs #71, #72, #76–#78). The proof half of the goal ran our own PMO operations through the shipped product: all four tools against real sprint data, with Monte Carlo correctly identifying the publish-chain as the dominant risk driver and TCO correctly ranking the stack — genuine validation, not a token exercise. The measurement gap it exposed (no estimate/actual fields on our own Work Items — ironic for a PMO product) became Sprint 12's new tracking fields.

### Sprint 12 (July 2026) — Strategy Pivot + Security Compounding ✅

Two-day sprint closing 9/9 (8 planned + 1 reactive). The no-freemium pivot — the OSS itself is the free tier of value; paid is the intelligence layer — was decided anchor-first so the vocabulary was frozen before the docs ran, then propagated through STRATEGY.md (PR #85), README/DESIGN/CONTENT_FLYWHEEL (PR #87), and the site's open-core copy (PR #75 groundwork), with mobile-friendly navigation and responsive content blocks verified on-device (PR #86). Security compounded on Sprint 11: HTTP security headers on the static site (PR #83), Monte Carlo DoS bounds + CORS hardening on the API prototype (PR #82), a gitleaks rule keeping internal record IDs out of committed content (PR #84), opengrep aligned and version-pinned (PRs #80, #89), and GitHub code scanning enabled with least-privilege workflow tokens (PR #88) — the code-scanning page went clean. First sprint with estimate/actual/friction fields live on Work Items, and the first external market signal: LinkedIn demographics on the pmorun-mcp post matched the two-audience thesis almost exactly.

### Sprint 13 (July 2026) — Phase 2 Foundations + Cloudflare Account ✅

Seven-item sprint that laid the ground for the Phase 2 product rather than shipping to it. The frontend MCP product was defined and its boundary decided — a paid remote MCP app, built in a separate private repository, with personal calibration memory as the non-negotiable core — and the remote MCP server PoC landed on Cloudflare Workers as an explicit proof, never a product (PR #91). A dedicated Cloudflare account was stood up for Phase 2, and the pmo.run domain and site migration off the old account was planned end to end before any record was touched. Housekeeping: the Dependabot ruff relock merged (PR #90), Sprints 8–12 were backfilled into this document (PR #92), and a wrangler pin plus a sandbox allowlist cleared recurring environment friction. **No actuals were recorded this sprint** — the estimate/actual protocol in sessions arrived with Sprint 14, so S13's PERT figures have nothing to calibrate against. That gap is the reason the protocol exists.

### Sprint 14 (July 2026) — Calibration Memory + Content Cadence ✅

Eight items, 6.48 PERT sessions against 3.9 actual. The product gained its differentiating capability: opt-in SQLite calibration memory, which unparked `estimate_from_history` and took the MCP server from four tools to eight when `PMORUN_DB` is set, staying stateless and writing nothing when it is not (PR #94). The R&D-to-content pipeline was made executable as the content-cadence skill (PR #98) and immediately exercised on its own first briefing, EN and JA (PR #99). An exploration established that MCP and REST can serve from one core at the cost of a single seam file, provided the transports never touch the core, and the PoC was merged (PR #100). The pmo.run migration ran phases A through C across the sprint. Security housekeeping cleared a pillow advisory (PR #95) and greened the scheduled scan by separating historical findings from live ones and adding a manual trigger (PR #93). **The one item to exceed its estimate was the briefing post, at 1.5 against 1.0** — the first appearance of a pattern that has held since: content items carrying real review rounds overrun, and implementation executed from a settled brief does not.

### Sprint 15 (July 2026) — Security, Refactoring and Parity Nets ✅

Eight items, and **the only sprint on record where every single item exceeded its estimate** — 3.47 PERT sessions against 4.45 actual, a ratio above 1.0 on all eight. Worth stating plainly rather than averaging away, because it is the clearest counter-example to the over-estimation pattern the other sprints show, and the items were small: the largest was 1.02 PERT. The work was security and internal quality, which is where "small" is least reliable. Four advisories blocking the commit gate were cleared, then four more npm advisories via scoped relock and a `sharp` override (PRs #103, #104). Monte Carlo's drift path was bounded and the scalar-cap sweep finished (PR #107), then the duplicated simulation logic was collapsed into one forward pass and one summariser (PR #108) and the dual-transport seam into one tag resolver and one result converter (PR #109). Two nets went in that have earned their keep since: pytest became a merge gate with the npm supply-chain posture pinned for the remote-MCP example (PR #105), and the site's calculators were netted against the Python core with generated fixtures, freezing the standalone examples (PR #110) — the control that catches rounding-mode divergence a line-by-line review does not. The `CLAUDE.local.md` convention for local operational notes was adopted (PR #106), and the `/cleanup` staleness sweep shipped along with its own first run (PR #111). Between this sprint and the next, on 26 July, the operational layer was extended out of sprint: the boot and close session rituals as cross-programme commands (PR #112), commit-message and `gh`-payload ID guards (PR #114), and the ship loop (PR #115).

### Sprint 16 (July–August 2026) — 0.2.0 Release + Operational Layer Consolidation ✅

Seven items over five days against a 3–4 day cadence, 6.42 PERT sessions against 4.4 actual. Both halves of the goal delivered. **`pmorun-mcp` 0.2.0 reached PyPI (PR #121), fixing a release that could not start on any machine**: `mcp` 2.0.0 had removed `FastMCP` while the requirement was unbounded, and `uv.lock` pinned a working version internally, so every gate stayed green while the published artefact was unusable — a lockfile proves the repository works, never that the release works. The fix was a capped constraint plus a new smoke job that installs the built wheel with dependencies resolved fresh and drives a real MCP handshake, which is the control whose absence let the broken version ship. The operational layer was then consolidated out of this repository entirely: the calibration overlays moved to a machine-wide register resolved by a three-rung lookup (PRs #119, #120, #124), and the session rituals, staleness sweep, ship loop and anonymisation gate moved to the neutral public `agent-ops` repository and were cut over across all three symlink surfaces before the originals were removed here (PR #128). `content-cadence` stayed, having forked between two working trees. A security-and-analysis panel audit settled the Dependabot question — the alert feed needed a default-branch push to analyse, not a backfill, so a just-enabled feed reads a meaningless zero. Astro 6 → 7 landed out of sprint (PR #122), discharging three suppressed XSS advisories and retiring a gate deadline; the blocker was an npm `overrides` pin below Astro 7's declared Vite floor, which no error message named. The sprint's briefing post shipped after a full restructure (PR #125), and CLAUDE.md and the content-cadence skill were corrected where the sprint's own changes had invalidated them (PRs #123, #126, #127). **Calibration held its shape: the two items that overran were the two that went through rounds of genuine human review**, at 1.13 and 1.11, while everything executed from a settled brief came in well under. Review rounds are not in the estimate, which is a property of the estimate rather than a defect in the work.
