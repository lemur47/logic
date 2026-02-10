# pmo.run — Launch Strategy

**Domain:** pmo.run
**Repo:** github.com/lemur47/logic
**Phase:** Awareness & Prototype
**Last updated:** 2026-02-10

---

## Mission

Provide AI + human PMO services to SMEs, backed by open source tools that serve the global PM/PMO community. Practical, privacy-first, simple.

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

### What Exists (logic repo)

```
app/
├── main.py          → FastAPI entry point
├── database.py      → SQLAlchemy + SQLite
└── tco/             → TCO module (live)
    ├── core.py      → Pure calculation functions
    ├── router.py    → API endpoints
    ├── schemas.py   → Pydantic validation
    ├── models.py    → SQLAlchemy ORM
    └── crud.py      → DB operations

examples/standalone/tco/  → Standalone Python version
```

### TCO Endpoints (Live)

```
POST /tco/calculate    → Stateless TCO calculation
POST /tco/compare      → Compare options, ranked by annual cost
POST /tco/breakeven    → Break-even analysis between two options
POST /tco/scenarios    → Save scenario (CRUD: create/read/update/delete)
GET  /tco/scenarios    → List scenarios (paginated, searchable)
GET  /tco/scenarios/stats → Aggregate statistics
```

### Planned Modules

| Module | Category | Priority | Description |
|--------|----------|----------|-------------|
| PERT | P3M/P3G | Next | Three-point estimation (optimistic/likely/pessimistic) |
| Base-rate | P3M/P3G | High | Reference class forecasting, reduce subjective bias |
| Bayesian | P3M/P3G | Medium | Bayesian updating for base-rate learning |
| NPV | Finance | Medium | Net Present Value analysis |
| IRR | Finance | Medium | Internal Rate of Return |
| Image metadata removal | Privacy | Low | Strip EXIF/metadata from images |

---

## Website: pmo.run

### Tech Stack

- **Framework:** Astro (static + islands)
- **Interactive components:** Svelte or Vue (for calculator UIs)
- **Styling:** Tailwind CSS
- **Hosting:** Cloudflare Pages
- **i18n:** Astro built-in (EN/JA)
- **API backend:** FastAPI on Cloudflare Workers or small VPS

### Site Structure

```
pmo.run/
├── /[lang]/                → Landing page
│   ├── /en/                → "PMO tools + services powered by AI"
│   └── /ja/                → "AIとプロフェッショナルによるPMOサービス"
├── /[lang]/tools/
│   ├── /tools/tco          → Interactive TCO calculator
│   ├── /tools/pert         → PERT estimator (when ready)
│   └── /tools/breakeven    → Break-even analyzer
├── /[lang]/blog/           → R&D notes, case studies (bilingual)
├── /[lang]/docs/           → API documentation
└── /[lang]/contact/        → Consulting inquiry form
```

### Design Principles

- Nerdy but simple — no corporate fluff
- Tools work without signup
- Privacy-first — no tracking, no analytics cookies
- Fast — static pages, edge-deployed
- Real examples — every tool page has a business case story

---

## Monetisation Strategy

### Phase 1: Consulting + Free Tools (Now)

Revenue comes from consulting. Tools and content are free. The website and repo are the storefront.

**Service model:** AI + human working together to:
- Analyse client data
- Provide strategic advice on investments, projects, portfolios
- Calculate with our tools (TCO, PERT, etc.)
- Write small PoC code for client-specific problems
- Deliver reports and recommendations

**Pricing:** Project-based or retainer. Japanese SME market first.

### Phase 2: Freemium SaaS (When Demand Signals Appear)

Free tools remain free. Paid tier adds: saved scenarios, PDF report export, team sharing, encrypted storage, API rate increases, and integrations with tools like Airtable and Baserow.

Pricing TBD based on market feedback.

### Phase 3: Platform (When Phase 2 Validates)

- Encrypted object storage + index DB
- AI interface for natural language queries over project data
- Security/privacy tools for SMEs
- Integrations with NoCode platforms for P3M workflows
- Automation pipelines

---

## Content Flywheel

Every R&D experiment and consulting engagement produces content:

```
R&D / Client Work
      ↓
PoC Script (committed to logic repo)
      ↓
Blog Post (EN/JP) explaining the problem, math, and solution
      ↓
Tool Page on pmo.run (interactive version)
      ↓
Social sharing (LinkedIn JP, dev.to EN, Hacker News)
      ↓
Traffic → Consulting inquiries + API users
      ↓
More client work → More content
```

### Blog Post Ideas

| # | Title (EN) | Title (JA) | Ties to |
|---|-----------|-----------|---------|
| 1 | "Cheap vs Inexpensive: TCO for office equipment" | 「安い」と「お得」は違う：オフィス機器のTCO分析 | TCO tool |
| 2 | "Build vs Buy: A framework with real numbers" | 内製 vs 外注：数字で考えるフレームワーク | TCO breakeven |
| 3 | "Why your project estimates are always wrong" | なぜプロジェクトの見積もりはいつも外れるのか | PERT tool |
| 4 | "Reference class forecasting for SMEs" | 中小企業のための参照クラス予測 | Base-rate tool |
| 5 | "The time value of money, explained with Python" | Pythonで理解するお金の時間的価値 | NPV module |
| 6 | "Privacy-first project data: a PoC with encryption" | プライバシー優先のプロジェクトデータ管理 | Encryption PoC |
| 7 | "Connecting Baserow to automated cost analysis" | Baserowで自動コスト分析を構築する | Integration PoC |
| 8 | "How AI + human PMO services actually work" | AI×人間のPMOサービスとは何か | Service marketing |
| 9 | "Open source tools for PMO: why we build in public" | なぜ私たちはオープンソースでPMOツールを作るのか | Brand story |
| 10 | "Cloud migration TCO: numbers your vendor won't show" | クラウド移行のTCO：ベンダーが見せない数字 | TCO tool |

---

## Go-to-Market: First 90 Days

### Days 1-30: Quiet Launch

- [ ] Deploy Astro site to pmo.run (Cloudflare Pages)
- [ ] Landing page with value prop (bilingual)
- [ ] TCO interactive tool page (bilingual, Svelte/Vue component)
- [ ] Contact/inquiry form
- [ ] Blog post #1: TCO office equipment case study
- [ ] README in logic repo links to pmo.run
- [ ] Share with trusted contacts for feedback

### Days 31-60: LinkedIn Drip + Second Tool

- [ ] PERT module: standalone PoC → FastAPI → interactive page
- [ ] Blog posts #2 and #3
- [ ] API docs page on pmo.run
- [ ] LinkedIn posts (1-2/week): value-first content, not announcements
- [ ] First consulting outreach (JA, warm contacts)

### Days 61-90: Broader Exposure + Validate

- [ ] Blog posts #4 and #5
- [ ] Submit to Hacker News (Show HN: Open source PMO tools)
- [ ] dev.to cross-post (EN)
- [ ] Gather feedback from tool users and early consulting clients
- [ ] Begin encryption PoC and Baserow integration PoC
- [ ] Evaluate: do we have demand signals for Phase 2?

---

## Technical Decisions (Pending)

| Decision | Options | Notes |
|----------|---------|-------|
| API hosting for pmo.run | Cloudflare Workers vs. small VPS | Workers = cheaper, VPS = simpler for SQLite |
| Interactive components | Svelte vs. Vue | Both work with Astro; Svelte is lighter |
| i18n approach | Astro content collections vs. manual | Content collections scale better |
| Auth (Phase 2) | Cloudflare Access vs. custom | Only needed when paid tier launches |
| Storage (Phase 3) | Cloudflare R2 + D1 vs. S3 + Postgres | R2 aligns with Cloudflare stack |

---

## Principles

1. **Ship, don't perfect.** A live page beats a perfect plan.
2. **R&D = Content.** Every experiment becomes a blog post.
3. **Privacy by default.** No tracking, no analytics cookies, encrypted storage.
4. **Two audiences, one brand.** SME clients (JA) and PMO community (EN).
5. **AI + Human.** The service is the product. Tools are the proof.
6. **Open source trust.** The logic repo is the credibility engine.
7. **Platform later.** Consulting revenue first. SaaS when demand is proven.
