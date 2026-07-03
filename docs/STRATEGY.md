# pmo.run — Strategy

Forward-looking strategy: mission, audiences, monetisation phases, IP positioning, and competitive moat. Architecture and technical decisions live in [`DESIGN.md`](DESIGN.md). Sprint actuals live in [`SPRINT_HISTORY.md`](SPRINT_HISTORY.md). The R&D → community loop lives in [`CONTENT_FLYWHEEL.md`](CONTENT_FLYWHEEL.md).

**Domain:** pmo.run
**Repo:** github.com/lemur47/logic
**Phase:** Awareness & Prototype → Agent PoC
**Last updated:** 2026-07-03

---

## Mission

Ship decisions, not spreadsheets.

Provide AI + human PMO services to SMEs, backed by open source decision-making tools that serve the global PM/PMO community. Every R&D deliverable creates value for the world — contribution first, revenue follows naturally.

## Philosophy: R&D for Everyone

Our flywheel runs on a simple principle: every experiment, every formula, every line of code we write becomes a public deliverable. We don't build in private and sell — we build in public and earn trust.

![R&D for Everyone](assets/flywheel.svg)

```
Real Problems (consulting & PMO work)
  → Logic & Math (formulas & analysis)
    → Open Source (Python PoC & modules)
      → Content (blog posts EN/JA)
        → Community (trust & adoption)
          → Value (to the world, always)
            → back to Real Problems
```

This is not a growth hack. It's the ethical foundation of the business.

## Principles

1. **Ship, don't perfect.** A live page beats a perfect plan.
2. **R&D = Content.** Every experiment becomes a blog post.
3. **Privacy by design.** Explicit data zones with transparent boundaries (see [Privacy Architecture in `DESIGN.md`](DESIGN.md#privacy-architecture-three-zone-model)).
4. **Two audiences, one brand.** SME clients (JA) and PMO community (EN).
5. **AI + Human.** The service is the product. Tools are the proof.
6. **Open source trust.** The logic repo is the credibility engine.
7. **Composable over monolithic.** Small modules anyone can import, not a walled garden.
8. **Authenticity over marketing.** When math contradicts the pitch, fix the pitch.
9. **Simplicity.** Fewer managed entities, more computed insights. If nobody maintains it, don't make it a table.

---

## Two Audiences, Two Languages

| Attribute | Primary: SME Managers (JA) | Secondary: PM/PMO Community (EN) |
|-----------|---------------------------|----------------------------------|
| Who | CEOs, COOs, dept heads at 5-200 person companies | Dedicated PMO staff, project managers, developers |
| Relationship | Direct consulting clients | Tool users, community, word-of-mouth |
| Language | Japanese-first | English-first |
| What they need | Decisions answered ("Is this investment worth it?") | Tools to use ("TCO calculator with NPV") |
| How they find us | Blog (JA), referrals, LinkedIn JP | GitHub, blog (EN), dev.to, Hacker News |
| Revenue model | Consulting fees | Intelligence layer engagements (future) |

### Content Split

- **Japanese pages:** Business outcomes, real-world case studies, consulting CTA, plain language
- **English pages:** Technical tools, API docs, open source repo, PMO methodology


---

## IP Strategy: Open Core + Intelligence Layer

### Principle

Logic and code are public. Data and calibration models are protected. The math stays open — what stays proprietary is the *reasoning that tells the math which variables matter*.

There is no freemium tier. **The OSS itself is the free tier of value** — full-strength tools (pmorun-mcp, Skills, MCP servers, plugin interfaces), not a crippled trial. Distribution happens through OSS + Skills + MCP + Plugins, not a SaaS funnel. What we charge for is the **intelligence layer**: analysis and insights (consulting), proprietary calibration plugins, and a managed data layer we run.

### Three-Layer IP Architecture

```
┌─────────────────────────────────────────────────────────┐
│  OSS LAYER (trust + adoption — the free tier of value)  │
│  MIT licensed. Pure math: PERT, TCO, NPV, Bayesian.     │
│  pmorun-mcp (PyPI), Skills, MCP servers,                │
│  FastAPI endpoints, plugin interfaces, Python imports.  │
│  Team Cognition MCP (standalone OSS repo).              │
│  Anyone can use, audit, fork, self-host.                │
├─────────────────────────────────────────────────────────┤
│  DISTRIBUTION LAYER (platform + workflows)              │
│  Agent orchestration, three-zone privacy model,         │
│  GitHub sync. Cloudflare Workers, Workflows,            │
│  AI Gateway. Visual/operational UI arrives via the      │
│  plugin layer — bring your own app; Airtable is the     │
│  reference plugin we dogfood.                           │
├─────────────────────────────────────────────────────────┤
│  INTELLIGENCE LAYER (proprietary IP + exit value)       │
│  Analysis and insights + consulting.                    │
│  Field-calibrated adjustment coefficients.              │
│  Risk pattern recognition models.                       │
│  Observation frameworks ("what to measure").             │
│  Industry-specific delay/risk profiles.                 │
│  Managed data layer (D1 + R2) holding client data       │
│  (Zone 1 encrypted, never accessible).                  │
└─────────────────────────────────────────────────────────┘
```

### What We Sell Is Not Calculations

We deliver **cognition as code** — mental models and mindset encoded as executable logic:

1. **Evaluation frameworks** — "what to observe to find the problem's root cause." The structure of attention, not the data itself.
2. **Risk detection models** — systems-thinking-based inference that converts observation patterns into probability. Turns ignored gut feeling into "system says 82% chance of resource failure in 3 weeks."
3. **Calibration plugins** — field-tested adjustments that make standard mathematical models match reality. PERT says duration X; the plugin knows this approval process adds 3 days, this review phase has a 20% rejection rate.

### Plugin Architecture

Each logic module exposes a `PluginInterface` that accepts calibration data:

```
core.py          → Pure math (OSS, MIT)
calibration.py   → Plugin interface for field adjustments (OSS, MIT)
plugins/         → Proprietary calibration data and models (closed, B2B licensed)
```

### What Stays Open vs. Closed

| Layer | License | Rationale |
|-------|---------|-----------|
| Mathematical formulas (PERT, TCO, NPV, etc.) | MIT | Trust engine, community adoption, auditability |
| pmorun-mcp, Skills, FastAPI endpoints, CLI tools, schemas | MIT | Adoption surface, composability proof |
| Plugin interface definitions | MIT | Enables ecosystem, lowers integration barrier |
| Team Cognition MCP (standalone repo) | MIT | Shared team-cognition tooling, dogfooded internally |
| Agent orchestration (Cloudflare Workers) | Source-available or MIT | Platform showcase, transparency |
| Calibration coefficients and field models | Proprietary (B2B) | Core consulting IP, exit value |
| Risk pattern recognition models | Proprietary (B2B) | Systems thinking encoded, highest-value asset |
| Managed data layer (D1 + R2) | Proprietary service | Client-data stewardship — the plugins thesis extended to storage |
| Client data | Zone 1 encrypted | Never accessible, even by us |


---

## Monetisation Strategy

### Phase 1: Consulting + Free Tools + PoC Spike (Now → Q2 2026)

Revenue comes from consulting. Tools and content are free. The website and repo are the storefront.

**Service model:** AI + human working together to analyse, calculate, advise, prototype, and deliver.

**Key deliverables this phase:**
- PERT + EVM modules (standalone → FastAPI → interactive page)
- Relational work-records schema with logic module integration (first built on Baserow, since retired in favour of the plugin layer — see Phase 2)
- Cloudflare Agent PoC spike (TCO/PERT as tools + Workflow approval gate)
- 5+ blog posts (bilingual, from R&D and consulting experience)
- First direct consulting clients (JA market)

**Pricing:** Project-based or retainer. Japanese SME market first.

### Phase 2: PMO Agent MVP + OSS Distribution Surfaces (Q3-Q4 2026)

There is no paid tier to graduate into — the OSS is the free tier of value, and it stays full-strength. This phase widens the distribution surfaces and stands up the intelligence layer behind them.

**OSS distribution surfaces:**
- pmorun-mcp on PyPI (shipped) — decision logic over MCP, `uvx pmorun-mcp` away
- Skills and plugin interfaces for agent workflows
- Team Cognition MCP: the internal lemurkit tooling split into two repos — the private ops repo exports via R2 to a standalone public OSS repo
- Visual/operational UI via the plugin layer: enterprises bring the app they already use (Airtable is the reference plugin we dogfood)

**Intelligence layer (paid):**
- Analysis and insights + consulting engagements
- Proprietary calibration plugins (field-tested coefficients, risk profiles)
- Managed data layer: D1 + R2 we run, holding clients' project data (Zone 1 encrypted) — stewardship, not a datastore we mandate
- GitHub bidirectional sync with agent-computed activity analytics

### Phase 3: Platform + Full Privacy + Ecosystem (2027)

- Full three-zone privacy with client-side generation option
- Vectorize for RAG over PMO knowledge base
- MCP servers for third-party integrations
- AI PMO Assistant (natural language queries over project data)
- Enterprise intelligence-layer engagements (dedicated infrastructure option)
- Process mining dashboard (anonymised decision analytics from D1)


---

## Real-World Problem: DevSecOps in PMO

From direct consulting experience — the pattern every enterprise PMO team suffers:

**Symptoms:**
- Notion/Confluence/Wiki manually edited and slowly rotting
- ClickUp/Jira tickets non-maintained, disconnected from reality
- GitLab/GitHub Issues used as a poor backlog with no estimation discipline
- WBS in spreadsheets: estimation-result gaps never tracked or learned from
- 3-4 disaster recoveries per month from stale documentation
- 70% of work is manual coordination between stakeholders
- 属人化 (person-dependency) from inconsistent task granularity across tools

**Our solution stack maps directly:**

| Pain | Our Module | Layer |
|------|-----------|-------|
| Estimation gaps | PERT (three-point estimation) | Logic |
| No learning from past estimates | Bayesian updating (from D1 estimation_log) | Logic |
| Manual WBS management | Plugin-layer work records (WBS work packages in the visual app you already use) | Integration |
| Disconnected tooling | GitHub ←→ plugin sync via agent | Integration |
| No decision analytics | AI Gateway + process mining (D1 activity_analytics) | Analytics |
| Data security concerns | Three-zone privacy model | Privacy |
| Documentation decay | Our own repo as the example | Meta |
| 属人化 | Agent-computed activity analytics (nobody maintains activities) | Agent |


---

## Strategic Positioning

### Appeal to Cloudflare

First PMO-domain Agent on their platform. Showcases: Agents SDK, Workflows, AI Gateway, D1, R2, Browser Rendering. Target: Developer Blog co-authorship and "Powered by Cloudflare" showcase.

### Appeal to Anthropic

CLAUDE.md-driven development workflow. PMO prompt library on GitHub. Domain-specific Claude integration for business decision-making. Target: best-practice showcase for "how Claude powers enterprise decisions."

### Competitive Moat

- **Domain logic:** PMO-specific math no generic AI provides
- **Human-in-the-loop:** Governance workflows, not just chat
- **Transparent privacy:** Three-zone model with honest boundaries
- **Dual language:** JA consulting + EN community
- **Open source trust:** Credibility via radical transparency
- **Composable modules:** Partial adoption lowers barrier, builds embedded presence
- **Relational data model:** the D1 + R2 managed data layer solves "nothing is connected" by design; visual apps plug into it
- **Simplicity:** Activities computed, not managed. Developers and managers stay in their tools.


---

*This document is our public commitment and the context for Claude Code. Every decision here is traceable to a real problem, a mathematical model, or a consulting insight. We update it as we learn.*
