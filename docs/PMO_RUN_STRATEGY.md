# pmo.run — Strategy

**Domain:** pmo.run
**Repo:** github.com/lemur47/logic
**Phase:** Awareness & Prototype → Agent PoC
**Last updated:** 2026-03-26

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
3. **Privacy by design.** Explicit data zones with transparent boundaries (see Privacy Architecture).
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
| Revenue model | Consulting fees | API subscriptions (future) |

### Content Split

- **Japanese pages:** Business outcomes, real-world case studies, consulting CTA, plain language
- **English pages:** Technical tools, API docs, open source repo, PMO methodology

---

## Product Architecture

### Six-Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│  CLIENT LAYER (View / Boundary)                         │
│  Astro + Svelte (pmo.run)  |  Baserow (operational UI)  │
│  EN/JA  |  Web Crypto API (client-side encryption)      │
├─────────────────────────────────────────────────────────┤
│  AGENT LAYER                                            │
│  Cloudflare Agents SDK  |  Durable Objects  |           │
│  AI Gateway  |  Workflows (human-in-the-loop)           │
├─────────────────────────────────────────────────────────┤
│  LOGIC LAYER                                            │
│  Finance: TCO | NPV | IRR | ROI                         │
│  Performance: PERT | EVM | Baseline | Bayesian           │
│  Value Delivery: Flow Metrics | Benefits Realisation     │
│  Python (community) + TypeScript (product)              │
├─────────────────────────────────────────────────────────┤
│  DATA LAYER (Model / Entity)                            │
│  D1 (structured metadata, queryable — Zone 3)           │
│  R2 (encrypted blobs, zero-knowledge — Zone 1)          │
├─────────────────────────────────────────────────────────┤
│  INTEGRATION LAYER                                      │
│  Baserow API  |  GitHub/GitLab webhooks  |  MCP Servers │
│  Browser Rendering                                      │
├─────────────────────────────────────────────────────────┤
│  PRIVACY LAYER                                          │
│  Three-zone model  |  Asymmetric key management         │
│  Envelope encryption  |  Digital signatures              │
│  Team key distribution                                  │
└─────────────────────────────────────────────────────────┘
```

### Two-Layer Data Architecture

Baserow is the View. D1 + R2 is the Model. The agent is the bridge.

**D1 (Model/Entity)** stores everything — all work items including archived, all process events, all financial history, all estimation history, all audit logs. It grows indefinitely and is queryable via SQL for analytics and AI. It feeds Bayesian updating with full historical data.

**R2 (Encrypted Blob Storage)** stores zero-knowledge encrypted documents, generated reports, audit archives, and proprietary calibration data. Client data in R2 is encrypted with the client's public key — we cannot read it.

**Baserow (View/Boundary)** shows only what's currently relevant — active projects, open work items (WBS work packages), unresolved risks, recent decisions. It's a materialised view of D1, curated by the agent. When a project completes, the agent archives from Baserow but retains everything in D1.

```
┌──────────────────────────────────────────────────────┐
│  VIEW / BOUNDARY (Baserow)                           │
│  Filtered, aggregated, current-state only.           │
│  Rows: hundreds, not thousands.                      │
│  Tables: Active Work Items (WBS), Current Risks,     │
│          Live EVM Dashboard, Open Decisions           │
└──────────────────────┬───────────────────────────────┘
                       │  agent reads/writes
┌──────────────────────┴───────────────────────────────┐
│  AGENT LAYER (Cloudflare Workers / Agents SDK)       │
│  Queries D1, computes with logic modules,            │
│  writes summaries to Baserow, syncs with GitHub.     │
│  Translates between abstraction levels:              │
│  work packages (managers) ↔ issues (developers)      │
└──────────────────────┬───────────────────────────────┘
                       │  agent reads/writes
┌──────────────────────┴───────────────────────────────┐
│  MODEL / ENTITY (D1 + R2)                            │
│  All raw data. Full history. Every event.            │
│  D1: structured (SQL, relational, indexed)           │
│  R2: blobs (encrypted docs, reports, archives)       │
└──────────────────────────────────────────────────────┘
```

### Baserow Relational Schema

Baserow is a relational visual database. We use it *as* a relational database — not one flat table, but a proper entity graph that solves the core SIer/PMO problem: "nothing is related systematically."

**Design principle:** Work Items represent WBS work packages only — never activities or tasks. Activities are observed by the agent from GitHub events and stored in D1 analytics. Managers plan at work package level. Developers work at issue level. The agent bridges the gap.

**Who manages activities? Nobody.** That's the point. Work packages are managed by humans. GitHub issues are created by developers at natural granularity. Activity-level analytics are computed by the agent from observed events. No human maintains the activity layer — it emerges from developer behaviour.

```
BASEROW — Core Tables (managed by humans, viewed by managers)

┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│  Projects   │────<│  Work Items      │>────│   People     │
│             │     │  (WBS work pkgs) │     │  (RACI)      │
│ name        │     │                  │     │              │
│ sponsor     │     │ wbs_code         │     │ name, role   │
│ baseline_   │     │ parent_id        │ ← hierarchy       │
│   start/end │     │ pert_o/m/p       │   (phase → pkg)   │
│ status      │     │ pert_expected    │     │ capacity     │
│ roi_target  │     │ baseline_cost    │     └──────────────┘
└──────┬──────┘     │ baseline_date    │
       │            │ actual_cost      │
       │            │ actual_date      │
       │            │ sv, spi, cv, cpi │ ← EVM calculated
       │            │ status           │ ← Kanban column
       │            │ assignee         │ ← PM/lead, not devs
       │            │ github_issue_    │
       │            │   count          │ ← aggregated by agent
       │            │ github_          │
       │            │   completion_%   │ ← computed by agent
       │            └──────┬───────────┘
       │                   │
  ┌────┴─────┐  ┌─────────┴──┐  ┌──────────────┐
  │ Finance  │  │   Risks    │  │  Decisions   │
  │          │  │            │  │              │
  │ tco_ref  │  │ probability│  │ what         │
  │ npv      │  │ impact     │  │ why (trace)  │
  │ irr      │  │ owner      │  │ confidence   │
  │ roi      │  │ status     │  │ evidence     │
  │ period   │  │ mitigation │  │ approved_by  │
  └──────────┘  │ work_item_ │  │ work_item_   │
                │   refs     │  │   refs       │
                └────────────┘  └──────────────┘
```

Managers see aggregated GitHub signals on work packages (`github_issue_count: 5`, `github_completion_%: 60%`), never individual issue details. If SPI drops, they investigate — but the default view is work package level.

**Domain extension tables** (added as features ship, never modify core):

```
┌─────────────┐  ┌────────────┐  ┌──────────────┐
│ Procurement │  │  Audit Log │  │  Benefits    │
│             │  │            │  │  Realisation │
│ vendor      │  │ who        │  │              │
│ cost        │  │ what       │  │ outcome      │
│ status      │  │ when       │  │ measured     │
│ work_item_  │  │ decision_  │  │ target       │
│   ref       │  │   ref      │  │ project_ref  │
└─────────────┘  └────────────┘  └──────────────┘
```

**Scalability principle:** Core tables are stable, domain tables are additive. Every domain table links back to core tables via foreign keys, but core tables never reference domain tables.

### D1 Schema

D1 mirrors the Baserow core schema plus analytics and integration tables that Baserow never sees:

```
D1 Core (mirrors Baserow, plus archived/historical records)
├── projects
├── work_items            ← includes archived, full PERT history
├── people
├── risks
├── finance
├── decisions
├── clients               ← public_key, key_signature, key_fingerprint, key_created_at
├── project_members        ← team access control for encrypted reports

D1 Integration (GitHub bridge — never in Baserow)
├── github_issue_links     ← junction: work_item_id ↔ github_issue_id + repo + link_type
├── sync_log               ← every Baserow/GitHub sync event

D1 Analytics (computed by agent — never in Baserow, never manually maintained)
├── activity_analytics     ← computed from GitHub events per issue per work item
│     work_item_id, github_issue_id, started_at, completed_at,
│     duration_days, review_cycles, contributor_count, rework_flag
├── process_events         ← append-only event log, millions of rows over time
│     event_type, timestamp, actor, work_item_ref, source,
│     before_state, after_state, metadata
├── estimation_log         ← every PERT calc: input, output, actual result
├── agent_actions          ← what the agent did and why (audit trail)
└── calibration_data       ← proprietary: field-adjusted coefficients
```

**`activity_analytics`** is the key table. It's populated entirely by the agent from GitHub webhook events. No human creates or maintains rows. Over time, it feeds Bayesian calibration ("work packages involving authentication historically take 1.4x PERT estimate"), process mining ("issues with 3+ contributors take 40% longer"), and anomaly detection ("WBS 1.3 has 2 open issues but no commits in 5 days").

### GitHub Integration: Input → Agent → Output

Developers live in GitHub. Managers live in Baserow. Neither group changes their workflow. The agent bridges them — translating between abstraction levels.

**GitHub is the input.** Commits, PRs, issue transitions, and label changes generate webhook events. The agent processes these events, updates D1, and pushes aggregated signals to Baserow.

**Baserow is the output.** Managers see real-time project status at work package level — EVM metrics, risk dashboards, aggregated completion signals. When a manager changes a priority in Baserow, the agent syncs back to GitHub as label/assignee changes.

**One canonical record at each level.** Work packages live in Baserow (manager's truth). GitHub issues live in GitHub (developer's truth). The `github_issue_links` junction table in D1 maps between them. The agent computes activity analytics from observed developer behaviour and rolls results up to work package level.

```
DEVELOPER WORLD                    MANAGER WORLD
(lives in GitHub)                  (lives in Baserow)

 ┌──────────┐                      ┌──────────────┐
 │  Issues   │                     │  Work Items  │
 │  at any   │──── webhook ───────>│  (WBS pkgs)  │
 │  granu-   │         │          │              │
 │  larity   │    ┌────┴────┐     │  Aggregated: │
 │           │    │  Agent  │     │  issue_count │
 │  Commits  │    │ Bridge  │     │  completion% │
 │  PRs      │    │         │     │  EVM metrics │
 │  Reviews  │    │ • links │     │              │
 └──────────┘    │   issues│     │  Kanban View │
                  │   to WBS│     │  Timeline    │
                  │ • computes    │  Dashboard   │
                  │   activity    └──────────────┘
                  │   analytics
                  │ • rolls up
                  │   to pkg level
                  │ • pushes
                  │   aggregates
                  │   to Baserow
                  └──────────┘
```

**Conflict resolution:** The more specific context wins. Developer changes status via PR merge → GitHub wins (ground truth about code). Manager changes priority in Baserow → Baserow wins (ground truth about business value). Every sync is logged in `process_events` for audit.

### Dual Codebase Strategy

| Codebase | Language | Purpose | Audience |
|----------|----------|---------|----------|
| `logic` repo | Python | Open source PoCs, standalone modules, FastAPI prototypes | Community, developers, self-hosters |
| Cloudflare Agent | TypeScript | Production product, Agents SDK, Workers runtime | Paying customers, platform |

Same math, two runtimes. The Python-to-TypeScript port is itself a blog post series.

### Logic Modules

Every module follows: **Standalone PoC → FastAPI endpoint → Agent tool → Interactive UI**

**Family 1: Finance** — "What will it cost and is it worth it?"

| Module | Status | Description |
|--------|--------|-------------|
| TCO | ✅ Live | Total Cost of Ownership with NPV adjustment |
| NPV | 📋 Planned | Net Present Value analysis |
| IRR | 📋 Planned | Internal Rate of Return |
| ROI | 📋 Planned | Return on Investment (capstone — synthesises TCO, NPV, IRR) |

**Family 2: Performance** — "How long will it take and are we on track?"

| Module | Status | Description |
|--------|--------|-------------|
| PERT | ✅ Live | Three-point estimation (optimistic/likely/pessimistic) |
| EVM Baseline | ✅ Live | Approved plan reference point for EVM tracking |
| EVM Metrics | ✅ Live | SV, SPI, CV, CPI — schedule and cost performance |
| Bayesian | ✅ Live | Bayesian estimation calibration from actuals |
| Monte Carlo | 📋 Planned | Probabilistic schedule and cost simulation |
| Base-rate | 📋 Planned | Reference class forecasting, reduce subjective bias |

**Family 3: Value Delivery** — "Are we delivering value?" (VDO/VMO)

| Module | Status | Description |
|--------|--------|-------------|
| Flow Metrics | 📋 Planned | Cycle time, throughput, WIP analysis |
| Benefits Realisation | 📋 Future | Outcome tracking against business case |

Module families relate to each other:

```
FINANCE                PERFORMANCE              VALUE DELIVERY
(is it worth it?)      (are we on track?)       (are we delivering?)

TCO ─────────────────► Baseline ◄──── PERT      Flow Metrics
NPV                    EVM:                      Benefits
IRR                      SV, SPI                 Realisation
ROI ◄──────────────────  CV, CPI
 ▲                         │                           │
 └─────────────────────────┴───────────────────────────┘
                    all feed into
              DECISION TRACEABILITY
                  (the agent layer)
```

### Logic API

Every logic module is available as:

- **Python import:** `from logic.tco.core import calculate_tco` — for developers integrating into their own systems
- **FastAPI endpoint:** `POST /tco/calculate` — stateless HTTP API for any client
- **Agent tool:** Callable by the Cloudflare Agent for orchestrated decision workflows

The API is not a separate product — it's an inherent property of composable logic.

### Live Endpoints

```
TCO  (9 endpoints): calculate, compare, breakeven, scenario CRUD + stats
PERT (7 endpoints): task, project, scenario CRUD
EVM  (8 endpoints): calculate, health, baseline CRUD, evaluate, snapshots
Bayesian (10 endpoints): calculate, adjust, context CRUD, observations, belief
```

---

## Agent Architecture

### Why an Agent, Not Just an API

A raw LLM gives essays. Our PMO Agent gives auditable decisions backed by deterministic math, governance workflows, and integration with the client's actual operational tools.

**Differentiation from generic AI:**

- **Domain-encoded logic.** PERT, TCO, Bayesian — precise calculations, not probabilistic text.
- **Human-in-the-loop as a feature.** Cloudflare Workflows `waitForApproval()` maps to real PMO governance: calculate → review → approve → execute.
- **External tool orchestration.** Agent writes to Baserow (WBS/timeline), observes GitHub (developer activity), reads from D1 (metadata), triggers reports — automation that LLMs alone can't do.

### Where AI Enters: The Decomposition Boundary

AI enters at the point where a vague human intention becomes structured, estimable work packages. This is the seam between natural language and deterministic math — the earliest point where AI adds irreplaceable value.

The foundation (PERT, EVM, Baserow schema) is built first (March–April). AI is designed in parallel but ships when the math it depends on is solid (May). The wave isn't gone — PMOs are still figuring out how to use AI. We have time to be precise.

```
Human input: "implement user authentication" (natural language)
       │
       ▼
  ┌─────────────┐
  │  LLM Layer  │  Decomposes into work packages with
  │  (Claude)   │  suggested O/M/P estimates per package
  └──────┬──────┘
         │  structured JSON
         ▼
  ┌─────────────┐
  │  PERT Math  │  Calculates expected duration, variance,
  │  (our logic)│  critical path, confidence intervals
  └──────┬──────┘
         │  deterministic results
         ▼
  ┌─────────────┐
  │  Baserow /  │  Visual timeline, Kanban,
  │  D1 storage │  dependency graph, EVM baseline
  └─────────────┘
```

The calibration layer between LLM and math is the proprietary IP insertion point. The open-source PERT math is MIT. The LLM decomposition prompt is generic. But the field-calibrated adjustments ("in SIer projects, authentication tasks typically take 1.3x the initial estimate due to stakeholder review cycles") — that's consulting IP encoded as a plugin.

### AI Surface Growth

AI is present from Sprint 3 and grows with each phase:

- **Sprint 3:** AI decomposes work packages → PERT estimates them
- **Sprint 4:** AI detects EVM anomalies, narrates GitHub activity into work package status
- **Sprint 5:** AI orchestrates full decision briefings with traceability across all modules

### Decision Flow Example

```
Client question
  → Agent reasons about intent (LLM via AI Gateway)
    → Calls TCO/PERT tools (our logic layer)
      → Stores results in D1 (structured metadata)
        → Pushes WBS to Baserow (work package level)
          → Developers create GitHub issues (natural granularity)
            → Agent observes, links, computes activity analytics
              → Pauses for human review (Workflow)
                → On approval: generates report (encrypted with team keys), updates status
                  → Logs everything via AI Gateway (billing/analytics)
```

### AI Gateway: Billing, Analytics, and Process Mining

AI Gateway provides cost visibility and model-switching flexibility. Beyond billing:

- Every agent interaction is logged — which tools get called, how often, in what sequence.
- Over time, this becomes a **process mining dataset**: how SMEs actually make decisions.
- Anonymised, aggregated insights become blog content and consulting IP.
- 30-day Cloudflare analytics for operational view; archive to R2/D1 for long-term analysis.

---

## Privacy Architecture: Three-Zone Model

The real question isn't "is everything encrypted?" The real question is **"where does plaintext exist, for how long, and who can access it?"** We answer this publicly and precisely.

### Three Zones

```
┌────────────────────────────────────────────────────────┐
│  ZONE 1 — Zero-Knowledge (R2 encrypted storage)       │
│                                                        │
│  Client-uploaded documents, agent-generated reports,   │
│  audit archives, proprietary calibration data.         │
│  Encrypted with client's public key.                   │
│  We cannot read this data. Period.                     │
├────────────────────────────────────────────────────────┤
│  ZONE 2 — Transient Computation (Cloudflare Workers)   │
│                                                        │
│  When the agent generates a report, plaintext exists   │
│  in Workers memory for milliseconds to seconds.        │
│  Result is encrypted before storage. Nothing persists  │
│  in plaintext. Client-side generation available for    │
│  stricter requirements.                                │
├────────────────────────────────────────────────────────┤
│  ZONE 3 — Operational Metadata (D1)                    │
│                                                        │
│  Project structure, task status, EVM metrics,          │
│  estimation parameters. Must be queryable by the       │
│  agent in real-time. Protected by Cloudflare's         │
│  infrastructure security and application-level         │
│  access controls. Not end-to-end encrypted.            │
└────────────────────────────────────────────────────────┘
```

### What Lives in Each Zone

**Zone 1 — Zero-Knowledge (R2):**
- Client-uploaded documents (contracts, org charts, board decks, vendor quotes)
- Agent-generated reports (project health PDFs, portfolio summaries, ROI exports)
- Sensitive records (decision memos with political context, named risk assessments, salary-linked cost breakdowns)
- Audit archives (raw GitHub payloads, aged-out process event batches)
- Proprietary IP (calibration coefficient models, risk pattern recognition data)

**Zone 2 — Transient Computation (Workers memory):**
- Report assembly from D1 data (plaintext in memory only, discarded after encryption)
- Webhook payload processing (parsed, structured results written to D1, raw payload archived to R2 encrypted)

**Zone 3 — Operational Metadata (D1):**
- Project structure (IDs, names, status, WBS codes)
- PERT inputs/outputs, EVM calculations
- Process events (active retention window)
- GitHub issue links, sync state, activity analytics
- Agent action logs
- Non-sensitive Baserow sync data

### Encryption Stack

**Asymmetric key management (client key pairs):**

```
Account Setup (one-time):
1. Browser generates RSA key pair (Web Crypto API)
2. Constructs key registration payload: {public_key, created_at, account_id}
3. Signs payload with private key (self-signature proves possession)
4. Sends {payload, signature} to server → stored in D1
5. Private key stays on client device only (never transmitted)
6. Client receives key fingerprint for out-of-band verification
```

**Agent-generated report encryption (envelope encryption):**

```
1. Agent assembles report from D1 data (in Workers memory)
2. Agent generates random AES-256-GCM symmetric key
3. Agent encrypts report with symmetric key
4. Agent retrieves public key + verifies signature (tamper detection)
5. Agent encrypts symmetric key with client's public key
6. Stores {encrypted_report, encrypted_symmetric_key} → R2
7. Agent discards all plaintext from memory
8. Client downloads, decrypts symmetric key with private key, decrypts report
```

**Team sharing (multi-recipient envelope encryption):**

```
Report encrypted once with random symmetric key.
Symmetric key encrypted separately for each authorised team member:

{
  encrypted_report: <single ciphertext>,
  encrypted_keys: {
    alice_id: <symmetric_key encrypted with Alice's public key>,
    bob_id:   <symmetric_key encrypted with Bob's public key>,
    carol_id: <symmetric_key encrypted with Carol's public key>
  }
}

Team access controlled via D1 project_members table:
  project_id → Projects
  member_id  → People (with client account)
  role       (sponsor, pm, lead, viewer)
  public_key_id → clients (registered public key)

Adding a member: encrypt symmetric key with their public key (no re-encryption of report).
Revoking a member: remove from project_members. Future reports exclude their key.
```

**Client-side generation (optional, strict zero-knowledge):**

```
1. Browser fetches aggregated data via API
2. Browser assembles report locally
3. Browser encrypts with own key
4. Browser uploads encrypted blob → R2
5. Server never sees assembled report, even in memory
```

### Key Rotation and Verification

- New keys signed with old private key (chain of trust)
- Key fingerprint displayed for out-of-band verification
- Public key signature verified by agent before every encryption operation
- Key registration payload includes `account_id` and `created_at` to prevent replay
- Key recovery uses a client-generated recovery secret (mnemonic phrase or downloadable file) created at account setup. The encrypted private key backup is stored in R2; the recovery secret never leaves the client's control. If both the private key and recovery secret are lost, Zone 1 data is permanently inaccessible — this is an inherent property of zero-knowledge architecture, not a flaw. Zone 3 operational data remains unaffected.

### Security Positioning (Public Commitment)

We tell you exactly where your data is readable — and where it isn't.

PMO data exists on a spectrum from public (estimation formulas) to highly sensitive (financial details, personnel decisions). We define three explicit zones with clear boundaries. We publish our encryption architecture openly. We never claim more protection than we provide. If your threat model requires Zone 1 guarantees for data currently in Zone 3, our architecture is designed to move boundaries as your requirements evolve.

### Privacy Phasing (Market-Driven)

- **Phase 1 (Consulting):** Server-side report generation with envelope encryption. Honest about Zone 2 transient exposure. Consulting clients accept this within the trust relationship.
- **Phase 2 (Freemium SaaS):** Add client-side report generation option. Self-service users choose between convenience and stricter guarantees.
- **Phase 3 (Enterprise):** Full client-side computation for sensitive operations. Plaintext never exists on our infrastructure, even transiently.

---

## IP Strategy: Open Core + Proprietary Plugins

### Principle

Logic and code are public. Data and calibration models are protected. The math stays open — what stays proprietary is the *reasoning that tells the math which variables matter*.

### Three-Layer IP Architecture

```
┌─────────────────────────────────────────────────────────┐
│  OSS LAYER (trust + adoption)                           │
│  MIT licensed. Pure math: PERT, TCO, NPV, Bayesian.     │
│  FastAPI endpoints, CLI tools, Python imports.           │
│  Anyone can use, audit, fork, self-host.                │
├─────────────────────────────────────────────────────────┤
│  PRODUCT LAYER (platform + workflows)                   │
│  Agent orchestration, Baserow integration,              │
│  Three-zone privacy model, GitHub sync.                 │
│  Cloudflare Workers, Workflows, AI Gateway.             │
│  Freemium → paid SaaS.                                  │
├─────────────────────────────────────────────────────────┤
│  PROPRIETARY PLUGIN LAYER (IP + exit value)             │
│  Field-calibrated adjustment coefficients.              │
│  Risk pattern recognition models.                       │
│  Observation frameworks ("what to measure").             │
│  Industry-specific delay/risk profiles.                 │
│  Client data (Zone 1 encrypted, never accessible).      │
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
| FastAPI endpoints, CLI tools, schemas | MIT | Adoption surface, composability proof |
| Plugin interface definitions | MIT | Enables ecosystem, lowers integration barrier |
| Agent orchestration (Cloudflare Workers) | Source-available or MIT | Platform showcase, transparency |
| Calibration coefficients and field models | Proprietary (B2B) | Core consulting IP, exit value |
| Risk pattern recognition models | Proprietary (B2B) | Systems thinking encoded, highest-value asset |
| Client data | Zone 1 encrypted | Never accessible, even by us |

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

### Sprint 6 (Current) — Docs Refresh + CI

- [ ] API docs: add Bayesian endpoints to api-overview (WI#166)
- [ ] Housekeeping: refresh README, strategy doc, CLAUDE.md (WI#167)
- [ ] GitHub Actions: migrate to Node.js 22+ (WI#136)
- [ ] Blog: layered mandate series (EN/JA) (WI#134, WI#135)
- [ ] Monte Carlo module development (WI#169)

---

## Monetisation Strategy

### Phase 1: Consulting + Free Tools + PoC Spike (Now → Q2 2026)

Revenue comes from consulting. Tools and content are free. The website and repo are the storefront.

**Service model:** AI + human working together to analyse, calculate, advise, prototype, and deliver.

**Key deliverables this phase:**
- PERT + EVM modules (standalone → FastAPI → interactive page)
- Baserow relational schema with logic module integration
- Cloudflare Agent PoC spike (TCO/PERT as tools + Workflow approval gate)
- 5+ blog posts (bilingual, from R&D and consulting experience)
- First direct consulting clients (JA market)

**Pricing:** Project-based or retainer. Japanese SME market first.

### Phase 2: PMO Agent MVP + Freemium SaaS (Q3-Q4 2026)

Free tools remain free. Agent goes live. Paid tier adds:
- Saved scenarios and PDF report export (Zone 1 encrypted, team sharing)
- Team sharing with role-based access
- Zone 1 encrypted storage for sensitive documents
- Baserow integration for WBS/timeline management
- GitHub bidirectional sync with activity analytics
- AI Gateway billing and analytics dashboard
- API rate increases

### Phase 3: Platform + Full Privacy + Ecosystem (2027)

- Full three-zone privacy with client-side generation option
- Vectorize for RAG over PMO knowledge base
- MCP servers for third-party integrations
- AI PMO Assistant (natural language queries over project data)
- Enterprise custom plans (dedicated infrastructure option)
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
| Manual WBS management | Baserow integration (WBS work packages) | Integration |
| Disconnected tooling | GitHub ←→ Baserow sync via agent | Integration |
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
- **Relational data model:** Baserow + D1 solves "nothing is connected" by design
- **Simplicity:** Activities computed, not managed. Developers and managers stay in their tools.

---

## Technical Decisions

| Decision | Resolution | Notes |
|----------|-----------|-------|
| API hosting | Cloudflare Workers (Agent) | Agent architecture supersedes VPS option |
| Interactive components | Svelte | Lighter, aligns with Astro islands |
| i18n approach | Astro content collections | Scales better for bilingual content |
| Auth (Phase 2) | Cloudflare Access | Integrates with Agent/Workers stack |
| Operational data | D1 (structured metadata) | Zone 3: infrastructure-secured, agent-queryable |
| Encrypted storage | R2 (blobs) | Zone 1: zero-knowledge, envelope encryption |
| Encryption | RSA-OAEP + AES-256-GCM via Web Crypto API | Asymmetric key pairs, envelope pattern |
| Operational UI | Baserow (View layer) | Relational visual database, WBS work packages only |
| Dev tool sync | GitHub webhooks | Agent bridge: activity analytics computed, not managed |
| Python vs TypeScript | Both | Python for community, TypeScript for product |

---

## Content Flywheel

Every R&D experiment and consulting engagement produces content:

```
R&D / Consulting / Real PMO Problems
      ↓
PoC Script (committed to logic repo, MIT)
      ↓
Blog Post (EN + JA) explaining the problem, math, and solution
      ↓
Tool Page on pmo.run (interactive Svelte component)
      ↓
Social sharing (LinkedIn JP, dev.to EN, Hacker News)
      ↓
Traffic → Consulting inquiries + API/tool users
      ↓
More real problems → More content → More trust
```

### Blog Post Pipeline

| # | Title (EN) | Title (JA) | Ties to |
|---|-----------|-----------|---------|
| 1 | "Cheap vs Inexpensive: TCO for office equipment" | 「安い」と「お得」は違う：オフィス機器のTCO分析 | TCO tool |
| 2 | "Build vs Buy: A framework with real numbers" | 内製 vs 外注：数字で考えるフレームワーク | TCO breakeven |
| 3 | "Why your project estimates are always wrong" | なぜプロジェクトの見積もりはいつも外れるのか | PERT tool |
| 4 | "Why your project docs rot — and a system-level fix" | なぜプロジェクトのドキュメントは腐るのか | DevSecOps insight |
| 5 | "Reference class forecasting for SMEs" | 中小企業のための参照クラス予測 | Base-rate tool |
| 6 | "The time value of money, explained with Python" | Pythonで理解するお金の時間的価値 | NPV module |
| 7 | "Transparent privacy for PMO data: a three-zone model" | PMOデータの透明なプライバシーモデル | Privacy architecture |
| 8 | "PMO tools on Cloudflare Agents: a PoC" | Cloudflare Agentsで動くPMOツール | Agent architecture |
| 9 | "Connecting Baserow to automated cost analysis" | Baserowで自動コスト分析を構築する | Integration PoC |
| 10 | "How AI + human PMO services actually work" | AI×人間のPMOサービスとは何か | Service marketing |
| 11 | "Open source tools for PMO: why we build in public" | なぜ私たちはオープンソースでPMOツールを作るのか | Brand story |
| 12 | "Cloud migration TCO: numbers your vendor won't show" | クラウド移行のTCO：ベンダーが見せない数字 | TCO tool |

---

## Website: pmo.run

### Tech Stack

- **Framework:** Astro (static + islands)
- **Interactive components:** Svelte (lighter, aligns with Astro)
- **Styling:** Tailwind CSS
- **Hosting:** Cloudflare Pages
- **i18n:** Astro built-in (EN/JA)
- **API backend:** Cloudflare Workers (Agent) + FastAPI (Python community)

### Site Structure

```
pmo.run/
├── /[lang]/                → Landing page
│   ├── /en/                → "PMO tools + services powered by AI"
│   └── /ja/                → "AIとプロフェッショナルによるPMOサービス"
├── /[lang]/tools/
│   ├── /tools/tco          → Interactive TCO calculator
│   ├── /tools/pert         → PERT estimator
│   └── /tools/breakeven    → Break-even analyzer
├── /[lang]/blog/           → R&D notes, case studies (bilingual)
├── /[lang]/docs/           → API documentation
└── /[lang]/contact/        → Consulting inquiry form
```

### Design Principles

- Nerdy but simple — no corporate fluff
- Tools work without signup
- Privacy by design — no tracking, no analytics cookies
- Fast — static pages, edge-deployed
- Real examples — every tool page has a business case story

---

## Development Environment

- **OS:** Pop!_OS
- **Package management:** uv
- **Editor:** Zed
- **Python:** 3.14+ (FastAPI, SQLAlchemy, pytest)
- **TypeScript:** Cloudflare Workers, Agents SDK (future)
- **Frontend:** Astro + Svelte + Tailwind CSS
- **AI:** Claude (development partner, CLAUDE.md-driven)
- **Security:** gitleaks, bandit, ruff, pyright, pre-commit hooks, GitHub Actions CI

---

*This document is our public commitment and the context for Claude Code. Every decision here is traceable to a real problem, a mathematical model, or a consulting insight. We update it as we learn.*
