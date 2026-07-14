# pmo.run — Content Flywheel

How R&D, consulting, and code become content, community, and value. Cross-references: [`STRATEGY.md`](STRATEGY.md) for the business model this loop feeds; [`DESIGN.md`](DESIGN.md) for the modules each post explains; [`../skills/operational/content-cadence/SKILL.md`](../skills/operational/content-cadence/SKILL.md) for the executable pipeline.

---

## Content Cadence

Each R&D artefact feeds **one** post — a briefing *or* a deep dive — and that post feeds **one** LinkedIn derivative:

```
R&D / Consulting / Real PMO Problems
      ↓
R&D artefact (PR, PoC, analysis — committed to logic repo, MIT)
      ↓  choose ONE frame
Briefing  |  Deep Dive  (blog post, EN + JA, same slug)
      ↓
LinkedIn derivative
      ↓
Traffic → Consulting inquiries + tool users
      ↓
More real problems → More artefacts → More trust
```

### The Two Frames

- **Briefing** — short, decision-first. Five sections, each heading carrying a tagline: Key Judgements, Situation, Analysis, Evaluation, Recommendation. For findings the reader should act on now.
- **Deep dive** — long-form, method-first, titled `<title>: <tagline>`. Executive Summary, Situation (or Problems), Analysis (data, industry base rates, systems analysis), Evaluation (leverage points via feedback loops and iceberg analysis), Recommendation (which leverage points first, and how). For evergreen reference material.

One artefact, one frame, never both. Frame choice, section templates, editorial conventions (British English, APA 7th title case, EN-only slugs and tags), and the binding anonymisation and image-reference gates are encoded in the [content-cadence skill](../skills/operational/content-cadence/SKILL.md).

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
| 9 | "Bring your own PMO dashboard: Airtable as a plugin" | 使い慣れたツールをPMOダッシュボードに：Airtableプラグイン | Plugin-layer PoC |
| 10 | "How AI + human PMO services actually work" | AI×人間のPMOサービスとは何か | Service marketing |
| 11 | "Open source tools for PMO: why we build in public" | なぜ私たちはオープンソースでPMOツールを作るのか | Brand story |
| 12 | "Cloud migration TCO: numbers your vendor won't show" | クラウド移行のTCO：ベンダーが見せない数字 | TCO tool |
