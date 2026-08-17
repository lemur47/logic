# pmo.run — Design

Architecture and technical decisions: six-layer stack, two-layer data architecture, agent design, three-zone privacy model, plus the website and dev environment. Forward-looking strategy lives in [`STRATEGY.md`](STRATEGY.md). Sprint actuals live in [`SPRINT_HISTORY.md`](SPRINT_HISTORY.md). The content pipeline is in [`CONTENT_FLYWHEEL.md`](CONTENT_FLYWHEEL.md).

---

## Product Architecture

### Six-Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│  CLIENT LAYER (View / Boundary)                         │
│  Astro + Svelte (pmo.run)  |  plugin UI (bring your own)│
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
│  Plugin connectors  |  GitHub/GitLab webhooks  |  MCP   │
│  Browser Rendering                                      │
├─────────────────────────────────────────────────────────┤
│  PRIVACY LAYER                                          │
│  Three-zone model  |  Asymmetric key management         │
│  Envelope encryption  |  Digital signatures              │
│  Team key distribution                                  │
└─────────────────────────────────────────────────────────┘
```

### Two-Layer Data Architecture

The plugin layer is the View. D1 + R2 is the Model — the proprietary data layer we run. The agent is the bridge.

We do not build a visual UI. Enterprises plug in the visual app they already use — Airtable is the reference plugin (the one we dogfood), one option among many. (Earlier iterations fixed Baserow as the View; it was retired in July 2026 in favour of this plugin layer.)

**D1 (Model/Entity)** stores everything — all work items including archived, all process events, all financial history, all estimation history, all audit logs. It grows indefinitely and is queryable via SQL for analytics and AI. It feeds Bayesian updating with full historical data.

**R2 (Encrypted Blob Storage)** stores zero-knowledge encrypted documents, generated reports, audit archives, and proprietary calibration data. Client data in R2 is encrypted with the client's public key — we cannot read it.

**Plugin layer (View/Boundary)** shows only what's currently relevant — active projects, open work items (WBS work packages), unresolved risks, recent decisions. Whatever visual app the client brings, it's a materialised view of D1, curated by the agent. When a project completes, the agent archives from the plugin UI but retains everything in D1.

```
┌──────────────────────────────────────────────────────┐
│  VIEW / BOUNDARY (plugin layer — BYO visual app)     │
│  Filtered, aggregated, current-state only.           │
│  Rows: hundreds, not thousands.                      │
│  Tables: Active Work Items (WBS), Current Risks,     │
│          Live EVM Dashboard, Open Decisions           │
└──────────────────────┬───────────────────────────────┘
                       │  agent reads/writes
┌──────────────────────┴───────────────────────────────┐
│  AGENT LAYER (Cloudflare Workers / Agents SDK)       │
│  Queries D1, computes with logic modules,            │
│  writes summaries to the plugin, syncs with GitHub.  │
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

### Canonical Work-Records Schema

The work-records schema is canonical in D1; plugin UIs map onto it. It is a proper entity graph — not one flat table — and it solves the core SIer/PMO problem: "nothing is related systematically." A relational visual app (Airtable as the reference plugin) surfaces these tables for managers.

**Design principle:** Work Items represent WBS work packages only — never activities or tasks. Activities are observed by the agent from GitHub events and stored in D1 analytics. Managers plan at work package level. Developers work at issue level. The agent bridges the gap.

**Who manages activities? Nobody.** That's the point. Work packages are managed by humans. GitHub issues are created by developers at natural granularity. Activity-level analytics are computed by the agent from observed events. No human maintains the activity layer — it emerges from developer behaviour.

```
CORE TABLES (canonical in D1 · surfaced in the plugin UI · managed by humans)

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

D1 is the canonical store: the core work-records tables above, plus analytics and integration tables that plugin UIs never see:

```
D1 Core (canonical — includes archived/historical records)
├── projects
├── work_items            ← includes archived, full PERT history
├── people
├── risks
├── finance
├── decisions
├── clients               ← public_key, key_signature, key_fingerprint, key_created_at
├── project_members        ← team access control for encrypted reports

D1 Integration (GitHub bridge — never surfaced in plugins)
├── github_issue_links     ← junction: work_item_id ↔ github_issue_id + repo + link_type
├── sync_log               ← every plugin/GitHub sync event

D1 Analytics (computed by agent — never surfaced in plugins, never manually maintained)
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

**`activity_analytics`** is the key table. It's populated entirely by the agent from GitHub webhook events. No human creates or maintains rows. Over time, it feeds Bayesian calibration, process mining ("issues with 3+ contributors take 40% longer"), and anomaly detection ("WBS 1.3 has 2 open issues but no commits in 5 days").

What calibration output looks like in practice, from our own `estimation_log` rather than a hypothetical: across 29 estimate/actual pairs, the posterior delay factor is **0.891** — we *over*-estimate by roughly 1.12x per item — and it varies by category, from content work at 0.994 down to operational housekeeping at 0.756. Earlier versions of this document illustrated the same idea with a 1.4x *under*-estimate. That figure was an extrapolation from a handful of observations and the measured data reversed both its size and its direction, which is the argument for the table rather than a footnote about it.

### Data Plane and Narrative Plane

A governance boundary, not a preference, and deliberately written to resist being softened later.

**The data plane takes measurable, falsifiable inputs only.** Into the engine go the influence graph and behavioural measures — estimate-accuracy ratio, throughput, review turnaround, domain familiarity. Every one is derived from events the system already records, and every one can be contradicted by the next observation.

**Personality typologies stay out of the maths, permanently.** MBTI, Wealth Dynamics and anything comparable are excluded as model inputs, weights, priors or features — including as tie-breakers, defaults or "soft" adjustments, and including any attempt to infer a type from observed behaviour, which would reintroduce them through the back door. Four reasons:

1. Poor test-retest reliability and no validated predictive power for delivery outcomes. An input that does not reproduce cannot carry a coefficient.
2. An unfalsifiable prior is not a prior. Bayesian machinery applied to one manufactures false confidence and launders it as arithmetic.
3. GDPR Article 22 and works-council exposure. Software that profiles identified individuals inside decision support carries obligations that a throughput measure does not.
4. One weak component taints the whole instrument. Everything else here is defensible under scrutiny; this would be the sentence a sceptical reviewer quotes.

**The narrative plane may carry labelled qualitative colour** — opt-in, explicitly marked as heuristic, and never feeding a calculation.

The test to apply when this is next questioned: *can the input be measured from recorded events, and could an observation falsify it?* If not, it belongs to the narrative plane. The named typologies are only today's instances; the test is the durable part.

### Ontology: A Fixed Upper Layer With Generated Extensions

The semantic layer over D1, KV and R2 uses a **fixed upper ontology** — actor, team, coordination mechanism, artefact, claim, dependency — with **generated per-programme domain extensions** beneath it.

The deciding argument is comparability rather than elegance. A freshly generated ontology per programme destroys cross-project comparison: posteriors cannot transfer between programmes, and the reference-class layer — the thing that lets one programme's history inform another's estimate — dies with it. The fixed upper layer is what makes calibration extensible past a single programme.

**The grounding rule is mandatory.** Every generated class and relation must bind to at least one observable data source, or be pruned. An unbound class is deleted, not flagged for later; "later" is how ungrounded taxonomies survive. A taxonomy with no data beneath it is a container artefact about the organisation that wrote it — it records how people talked, not what happened.

This mirrors the schema principle above: core tables are stable, domain tables are additive, and the same holds one level up in the semantics.

### GitHub Integration: Input → Agent → Output

Developers live in GitHub. Managers live in their plugin UI. Neither group changes their workflow. The agent bridges them — translating between abstraction levels.

**GitHub is the input.** Commits, PRs, issue transitions, and label changes generate webhook events. The agent processes these events, updates D1, and pushes aggregated signals to the plugin UI.

**The plugin UI is the output.** Managers see real-time project status at work package level — EVM metrics, risk dashboards, aggregated completion signals. When a manager changes a priority in their plugin, the agent syncs back to GitHub as label/assignee changes.

**One canonical record at each level.** Work packages live in D1 and surface in the plugin UI (manager's truth). GitHub issues live in GitHub (developer's truth). The `github_issue_links` junction table in D1 maps between them. The agent computes activity analytics from observed developer behaviour and rolls results up to work package level.

```
DEVELOPER WORLD                    MANAGER WORLD
(lives in GitHub)                  (lives in the plugin UI)

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
                  │   to plugin
                  └──────────┘
```

**Conflict resolution:** The more specific context wins. Developer changes status via PR merge → GitHub wins (ground truth about code). Manager changes priority in the plugin UI → the plugin wins (ground truth about business value). Every sync is logged in `process_events` for audit.

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
| Monte Carlo | ✅ Live | Probabilistic schedule simulation (P50/P80/P95) |
| EVM Baseline | ✅ Live | Approved plan reference point for EVM tracking |
| EVM Metrics | ✅ Live | SV, SPI, CV, CPI — schedule and cost performance |
| Bayesian | ✅ Live | Bayesian estimation calibration from actuals |
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
- **External tool orchestration.** Agent writes to the plugin UI (WBS/timeline), observes GitHub (developer activity), reads from D1 (metadata), triggers reports — automation that LLMs alone can't do.

### Where AI Enters: The Decomposition Boundary

AI enters at the point where a vague human intention becomes structured, estimable work packages. This is the seam between natural language and deterministic math — the earliest point where AI adds irreplaceable value.

The foundation (PERT, EVM, the canonical work-records schema) is built first (March–April). AI is designed in parallel but ships when the math it depends on is solid (May). The wave isn't gone — PMOs are still figuring out how to use AI. We have time to be precise.

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
  │  Plugin UI /│  Visual timeline, Kanban,
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
        → Pushes WBS to the plugin UI (work package level)
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
- Non-sensitive plugin sync data

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
- **Phase 2 (OSS distribution surfaces):** Add client-side report generation option. Self-hosting and OSS users choose between convenience and stricter guarantees.
- **Phase 3 (Enterprise):** Full client-side computation for sensitive operations. Plaintext never exists on our infrastructure, even transiently.


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
| Operational UI | Plugin layer — bring your own visual app (Airtable = reference plugin) | WBS work packages only; we do not build a visual UI |
| Dev tool sync | GitHub webhooks | Agent bridge: activity analytics computed, not managed |
| Python vs TypeScript | Both | Python for community, TypeScript for product |
| Model inputs | Measurable, falsifiable inputs only | Personality typologies excluded from the data plane permanently; qualitative colour is narrative-plane and labelled |
| Semantic layer | Fixed upper ontology + generated per-programme extensions | Grounding rule mandatory: an unbound class is pruned, not flagged |


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
- **Security:** gitleaks, opengrep, osv-scanner, ruff, pyright, pre-commit hooks, GitHub Actions CI
