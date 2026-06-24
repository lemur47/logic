export const languages = {
  en: "English",
  ja: "日本語",
} as const;

export type Lang = keyof typeof languages;

export const defaultLang: Lang = "en";

export const ui = {
  en: {
    "site.title": "pmo.run",
    "site.description":
      "Turn your PMO from a management unit into an intelligence organisation. Open-core decision tools for PMOs and consulting firms — Claude, MCP, Skills and API, with the shared method that makes the numbers reproducible.",
    "nav.home": "Home",
    "nav.tools": "Tools",
    "nav.blog": "Blog",
    "nav.docs": "Docs",
    "nav.about": "About",
    "nav.contact": "Contact",
    "footer.copy": "pmo.run",
    "footer.github": "GitHub",
    "footer.blog": "Blog",
    "footer.docs": "Docs",
    "footer.blurb":
      "Mathematically-grounded tools for AI agents working alongside Project Management Offices.",
    "footer.section.oss": "Open Source",
    "footer.section.paid": "Paid",
    "footer.section.cons": "Consulting",
    "footer.section.resources": "Resources",
    "footer.link.skills": "Skills",
    "footer.link.api": "API",
    "footer.link.tools": "Tools",
    "footer.link.plugins": "Plugins",
    "footer.link.engagement": "Engagement model",
    "footer.builton": "Built with Astro + Svelte on Cloudflare",
    "footer.location": "Japan · Open from 2026",

    "tools.tco": "TCO Calculator",
    "tools.tco.desc": "Total Cost of Ownership Analysis for Informed Purchasing Decisions.",
    "tools.breakeven": "Break-Even Analysis",
    "tools.breakeven.desc": "Find the Point Where Revenue Meets Costs.",

    /* Homepage — renewal copy from design handoff */
    "home.hero.eyebrow": "v0.4 · alpha",
    "home.hero.meta1": "§00 / index",
    "home.hero.meta2": "MIT + commercial",
    "home.hero.meta3": "EN · JA",
    "home.hero.meta4": "japan · remote",
    "home.hero.line1": "From a management unit",
    "home.hero.line2": "to an intelligence organisation.",
    "home.hero.body":
      "Open-core decision tools for PMOs and consulting firms — give Claude and your team the method to turn project data into intelligence everyone can reproduce.",
    "home.hero.ctaPrimary": "Read the docs",
    "home.hero.ctaSecondary": "Install the skills",
    "home.metric.skills.label": "Skills",
    "home.metric.skills.value": "4",
    "home.metric.skills.sub": "Claude-native",
    "home.metric.mcp.label": "MCP tools",
    "home.metric.mcp.value": "5",
    "home.metric.mcp.sub": "stdio · on PyPI",
    "home.metric.apis.label": "APIs",
    "home.metric.apis.value": "REST",
    "home.metric.apis.sub": "FastAPI",
    "home.metric.methods.label": "Methods",
    "home.metric.methods.value": "PERT · MC · Bayes",
    "home.metric.methods.sub": "peer-reviewed",

    "home.premise.title":
      "The administrative PMO won't survive agents. The intelligence-led PMO will run on them.",
    "home.premise.body":
      "We're not selling a replacement. We're shipping what the next generation of PMO work runs on — open-core, with premium plugins where data integration warrants it and consulting where the judgement is bespoke.",
    "home.premise.quote":
      "An AI agent can estimate a delivery date in seconds, but it can't judge which task to unblock next. pmo.run gives PMOs and their agents the maths to do both — with every number traceable.",

    "home.methods.title": "Maths-proved logic, packaged as tools.",
    "home.methods.lede":
      "Each method ships as a Skill (for Claude), an MCP server (for any agent), and an HTTP API. Same logic, three surfaces.",
    "home.methods.pert.title": "Program Evaluation & Review Technique",
    "home.methods.pert.body":
      "Weighted three-point estimates with critical-path detection. Surfaces float, slack, and which task to actually unblock.",
    "home.methods.mc.title": "Schedule simulation across thousands of runs",
    "home.methods.mc.body":
      "Replaces single-point dates with distributions. p50 / p90 ship dates, sensitivity per task, and confidence intervals you can defend.",
    "home.methods.bayes.title": "Estimates that learn from delivery",
    "home.methods.bayes.body":
      "Updates prior beliefs as tickets close. Replaces the \"gut feel re-baseline\" with an auditable likelihood update.",
    "home.methods.tco.title": "Total cost of ownership, decomposed",
    "home.methods.tco.body":
      "License + ops + integration + training + the hidden line items. Used by SIers to defend procurement decisions.",
    "home.methods.more":
      "+ earned-value, throughput accounting, queueing models, risk-adjusted NPV — see /docs",

    "home.install.title": "Drop-in for Claude, Cursor, or any MCP client.",
    "home.install.lede":
      "No platform lock. Skills load into Claude. The same tools run as a local MCP server, or behind your gateway as an HTTP API.",

    "home.opencore.title": "Three layers. One contract.",
    "home.opencore.lede":
      "The three-layer core is open source: the core logic and tools stay MIT-licensed. Paid plugins and consulting services add on top — your own proprietary layer.",
    "home.opencore.col.layer": "Layer",
    "home.opencore.col.contents": "What's in it",
    "home.opencore.col.audience": "Who it's for",
    "home.opencore.col.license": "License",
    "home.opencore.col.pricing": "Pricing",
    "home.opencore.row1.contents":
      "Skills, MCP servers, APIs. PERT, Monte Carlo, Bayes, EVM, TCO, queueing.",
    "home.opencore.row1.audience":
      "PMO communities, contract PMOs.",
    "home.opencore.row2.contents":
      "Proprietary connectors: Jira Cloud, ServiceNow, SAP, MS Project, Salesforce. Industry datasets, benchmark libraries.",
    "home.opencore.row2.audience":
      "Systems integrators, internal platform teams.",
    "home.opencore.row3.contents":
      "Bespoke analysis, model calibration, rollout, executive briefings, training programmes.",
    "home.opencore.row3.audience":
      "Consulting firms, large transformation programmes.",

    "home.audience.title": "For PMOs evolving from a management unit into an intelligence organisation.",
    "home.audience.lede":
      "The administrative half of the PMO role — status rollups, variance reports, schedule maintenance — will be done by agents. Our work is to give those agents the same rigorous tools your best analysts use, so the human half can move upstream into intelligence work.",
    "home.audience.practitioner.label": "practitioner",
    "home.audience.practitioner.body":
      "Stop hand-rolling Monte Carlo in Excel. Drop the skill in Claude. Get the same numbers, defensible.",
    "home.audience.sier.label": "SIer",
    "home.audience.sier.body":
      "Plug into your client's Jira / ServiceNow / SAP. Ship licensed integrations under your brand if you need to.",
    "home.audience.consulting.label": "consulting firm",
    "home.audience.consulting.body":
      "Put your historical data to work with PMO logic and tools, and sharpen your firm's insight.",

    "home.start.title": "Clone the repo and start using it right away.",
    "home.start.docs": "Read the docs",
    "home.start.github": "Browse on GitHub",
    "home.start.consult": "or: brief us on a consulting engagement →",

    "landing.trust.opensource": "Open Source",
    "landing.trust.privacy": "Privacy-First",
    "landing.trust.noaccount": "No Account Required",
    "landing.trust.api": "API Available",

    "blog.title": "Blog",
    "blog.empty": "No posts yet.",
    "docs.title": "Documentation",
    "docs.empty": "No docs yet.",
    "tools.title": "Tools",
    "contact.title": "Contact",
    "contact.body": "Questions, feedback, or partnership inquiries:",
    "contact.email": "Email us",

    /* About page */
    "about.hero.eyebrow": "§00 / about",
    "about.hero.title": "Open methods, in service of intelligence-led PMOs.",
    "about.hero.body":
      "pmo.run is the open foundation of a PMO service combining AI tooling and human judgement. We publish the maths, ship the surfaces (Skills, MCP, APIs), and engage on the bespoke work where calibration matters.",
    "about.thesis.title": "Why we exist",
    "about.thesis.lede":
      "Three PMO challenges in the age of AI.",
    "about.thesis.cell1.title": "AI agents need mathematical logic",
    "about.thesis.cell1.body":
      "Plausible-sounding reasoning and ad-hoc fixes don't solve the problem. Giving AI agents mathematically verified tools turns your organisation's tacit knowledge into a reproducible system.",
    "about.thesis.cell2.title": "Open-core, paid plugins",
    "about.thesis.cell2.body":
      "Core logic and tools are open source — we contribute to the PMO community. The value lies in accumulated data and the systematising of tacit knowledge, not in monetising the basic tools.",
    "about.thesis.cell3.title": "Judgement is the human work",
    "about.thesis.cell3.body":
      "Status rollups, variance reports, schedule maintenance — agents will do all of it. The judgement work — where to invest, what to stop, how to communicate trade-offs — is upstream and stays human.",
    "about.people.title": "Team",
    "about.people.lede":
      "A Japan-based human + AI team — practising PMOs, AI mathematicians, and an AI DevSecOps team. We turn the PMO's tacit knowledge into maths and build it into tools.",
    "about.contact.title": "Get in touch",
    "about.contact.lede":
      "Three ways to reach us.",
    "about.contact.method1.label": "open source",
    "about.contact.method1.body":
      "Issues and RFCs on GitHub. To guard against malware and supply-chain attacks, we don't accept pull requests from external or unverified parties.",
    "about.contact.method2.label": "consulting",
    "about.contact.method2.body":
      "Email us with a one-paragraph brief. We respond within two business days.",
    "about.contact.method3.label": "partnerships",
    "about.contact.method3.body":
      "SIers, consulting firms, integration partners. Drop a note and we'll set up a call.",

    /* TCO calculator (kept as before) */
    "tco.calc.mode.single": "Single",
    "tco.calc.mode.compare": "Compare",
    "tco.calc.initialPrice": "Initial Price",
    "tco.calc.usefulLife": "Useful Life (years)",
    "tco.calc.residualValue": "Residual Value",
    "tco.calc.annualMaintenance": "Annual Maintenance",
    "tco.calc.annualOperating": "Annual Operating Cost",
    "tco.calc.discountRate": "Discount Rate (%)",
    "tco.calc.calculate": "Calculate",
    "tco.calc.reset": "Reset",
    "tco.calc.addOption": "Add Option",
    "tco.calc.remove": "Remove",
    "tco.calc.totalCost": "Total Cost",
    "tco.calc.annualCost": "Annual Cost",
    "tco.calc.monthlyCost": "Monthly Cost",
    "tco.calc.costPerDay": "Daily Cost",
    "tco.calc.npvTco": "NPV-Adjusted TCO",
    "tco.calc.npvAnnual": "NPV Annual Cost",
    "tco.calc.simpleTco": "Simple TCO",
    "tco.calc.npvAdjusted": "NPV-Adjusted",
    "tco.calc.bestValue": "Best Value",
    "tco.calc.validation.positive": "Must be positive",
    "tco.calc.validation.nonNegative": "Cannot be negative",
    "tco.calc.currency": "$",
    "tools.pert": "PERT Estimator",
    "tools.pert.desc": "Three-Point Estimation with Reality Adjustments for Project Schedules.",
    "pert.calc.title": "PERT Estimation",
    "pert.calc.optimistic": "Optimistic (O)",
    "pert.calc.mostLikely": "Most Likely (M)",
    "pert.calc.pessimistic": "Pessimistic (P)",
    "pert.calc.unit": "days",
    "pert.calc.calculate": "Calculate",
    "pert.calc.reset": "Reset",
    "pert.calc.textbook": "Textbook PERT",
    "pert.calc.adjusted": "Reality-Adjusted",
    "pert.calc.expected": "Expected",
    "pert.calc.stdDev": "Std Dev",
    "pert.calc.range68": "68% Range",
    "pert.calc.range95": "95% Range",
    "pert.calc.range99": "99.7% Range",
    "pert.calc.delta": "Delta",
    "pert.calc.adjustedP": "Adjusted P",
    "pert.calc.combinedMultiplier": "Combined Multiplier",
    "pert.calc.insightTags": "Insight Tags",
    "pert.calc.insightTags.desc": "Toggle reality factors to see how they shift estimates.",
    "pert.calc.tag.fragmented": "Fragmented Communication",
    "pert.calc.tag.fragmented.desc": "Chat/meetings/manual workflows increase overhead",
    "pert.calc.tag.stakeholders": "Multiple Stakeholders",
    "pert.calc.tag.stakeholders.desc": "Misaligned interests across orgs",
    "pert.calc.tag.dependencies": "Hidden Dependencies",
    "pert.calc.tag.dependencies.desc": "Undocumented task relationships, upstream blockers",
    "pert.calc.severity.mild": "Mild",
    "pert.calc.severity.severe": "Severe",
    "pert.calc.rangeComparison": "Range Comparison",
    "pert.calc.validation.order": "Must satisfy O ≤ M ≤ P",
    "pert.calc.validation.nonNegative": "Cannot be negative",
    "tools.evm": "EVM Tracker",
    "tools.evm.desc":
      "Earned Value Management — track schedule and cost performance against your project baseline.",
    "blog.cta.pert": "Try the PERT Estimator",
    "blog.cta.pert.desc": "See how reality adjustments change your estimates.",
    "blog.cta.tco": "Try the TCO Calculator",
    "blog.cta.tco.desc": "Compare the real cost of your options.",
  },
  ja: {
    "site.title": "pmo.run",
    "site.description":
      "PMOを「管理部門」から「インテリジェンス組織」へ。PMOとコンサルティングファームのためのオープンコアな意思決定ツール群 — Claude・MCP・Skill・API、そして数値を再現可能にする共通の手法。",
    "nav.home": "ホーム",
    "nav.tools": "ツール",
    "nav.blog": "ブログ",
    "nav.docs": "ドキュメント",
    "nav.about": "チーム",
    "nav.contact": "お問い合わせ",
    "footer.copy": "pmo.run",
    "footer.github": "GitHub",
    "footer.blog": "ブログ",
    "footer.docs": "ドキュメント",
    "footer.blurb":
      "PMOと、それを支援するAIエージェントのための、数理に基づくツール群。",
    "footer.section.oss": "オープンソース",
    "footer.section.paid": "有償",
    "footer.section.cons": "コンサルティング",
    "footer.section.resources": "リソース",
    "footer.link.skills": "Skills",
    "footer.link.api": "API",
    "footer.link.tools": "ツール",
    "footer.link.plugins": "プラグイン",
    "footer.link.engagement": "エンゲージメントモデル",
    "footer.builton": "Astro + Svelte / Cloudflareで構築",
    "footer.location": "日本 · 2026年から",

    "tools.tco": "TCO計算ツール",
    "tools.tco.desc": "総所有コスト分析で、購買判断を数値で裏付ける。",
    "tools.breakeven": "損益分岐点分析",
    "tools.breakeven.desc": "収益がコストを上回るポイントを見つける。",

    "home.hero.eyebrow": "v0.4 · alpha",
    "home.hero.meta1": "§00 / index",
    "home.hero.meta2": "MIT + 商用",
    "home.hero.meta3": "EN · JA",
    "home.hero.meta4": "日本 · リモート",
    "home.hero.line1": "「管理部門」から",
    "home.hero.line2": "「インテリジェンス組織」へ。",
    "home.hero.body":
      "PMOとコンサルティングファームのためのオープンコアな意思決定ツール群。Claudeとチームに、プロジェクトのデータを誰もが再現できるインテリジェンスへと変える手法を。",
    "home.hero.ctaPrimary": "ドキュメントを読む",
    "home.hero.ctaSecondary": "Skillをインストール",
    "home.metric.skills.label": "Skills",
    "home.metric.skills.value": "4",
    "home.metric.skills.sub": "Claudeネイティブ",
    "home.metric.mcp.label": "MCPツール",
    "home.metric.mcp.value": "5",
    "home.metric.mcp.sub": "stdio · PyPI公開",
    "home.metric.apis.label": "API",
    "home.metric.apis.value": "REST",
    "home.metric.apis.sub": "FastAPI",
    "home.metric.methods.label": "手法",
    "home.metric.methods.value": "PERT · MC · ベイズ",
    "home.metric.methods.sub": "査読済み",

    "home.premise.title":
      "管理業務としてのPMOは消える。インテリジェンスを担うPMOには、エージェントが必要になる。",
    "home.premise.body":
      "代替を売るのではなく、次世代のPMO業務が動く土台を提供します。オープンコアを基盤に、データ連携は有償プラグイン、案件固有の判断は伴走型コンサルティングで。",
    "home.premise.quote":
      "AIエージェントは納期を数秒で見積もれますが、次にどのタスクを解放すべきかは判断できません。pmo.runは、PMOとそのエージェントに、その両方を担うための数理ロジックを — すべての数値を追跡可能な形で提供します。",

    "home.methods.title": "数理に裏づけられたロジックを、ツールとして。",
    "home.methods.lede":
      "各手法はClaude向けのSkill、任意のエージェント向けMCPサーバー、HTTP APIとして提供。同じロジックを、三つの接点から。",
    "home.methods.pert.title": "PERT — プログラム評価・レビュー手法",
    "home.methods.pert.body":
      "重みづけ三点見積もりとクリティカルパス検出。フロート、スラック、解放すべきタスクを可視化。",
    "home.methods.mc.title": "モンテカルロ — 数千回試行のスケジュール模擬",
    "home.methods.mc.body":
      "単点の納期予測を分布に置き換える。p50・p90納期、タスク別感度、根拠を示せる信頼区間。",
    "home.methods.bayes.title": "ベイズ更新 — 実績から学ぶ見積もり",
    "home.methods.bayes.body":
      "チケット消化に応じて事前分布を更新。「勘で再ベースライン」を、監査可能な尤度更新に置き換える。",
    "home.methods.tco.title": "TCO — 総所有コストを項目に分解",
    "home.methods.tco.body":
      "ライセンス + 運用 + 統合 + 教育 + 隠れコスト。SIerが調達判断の根拠として使う指標。",
    "home.methods.more":
      "＋アーンドバリュー、スループット会計、待ち行列モデル、リスク調整NPV — /docs を参照",

    "home.install.title": "Claude・Cursor・任意のMCPクライアントに、そのまま組み込み。",
    "home.install.lede":
      "プラットフォーム依存なし。SkillはClaudeに読み込む。同じツールがローカルMCPサーバーとしても、ゲートウェイ越しのHTTP APIとしても動きます。",

    "home.opencore.title": "三層、ひとつの契約。",
    "home.opencore.lede":
      "3層のコアはオープンソース。基幹ロジックとツールはMITライセンス。有償プラグインとコンサルティングサービスは貴社独自の層として追加可能です。",
    "home.opencore.col.layer": "層",
    "home.opencore.col.contents": "内容",
    "home.opencore.col.audience": "対象",
    "home.opencore.col.license": "ライセンス",
    "home.opencore.col.pricing": "価格",
    "home.opencore.row1.contents":
      "Skills・MCPサーバー・API。PERT、モンテカルロ、ベイズ、EVM、TCO、待ち行列。",
    "home.opencore.row1.audience":
      "PMOコミュニティ、業務委託PMO。",
    "home.opencore.row2.contents":
      "独自コネクタ: Jira Cloud、ServiceNow、SAP、MS Project、Salesforce。業種別データセット、ベンチマーク。",
    "home.opencore.row2.audience":
      "システムインテグレーター、社内プラットフォームチーム。",
    "home.opencore.row3.contents":
      "個別分析、モデル校正、展開支援、経営報告、研修プログラム。",
    "home.opencore.row3.audience":
      "コンサルティングファーム、大規模変革プログラム。",

    "home.audience.title": "「管理部門」から「インテリジェンス組織」へ進化するPMOのために。",
    "home.audience.lede":
      "ステータス集約、差異報告、スケジュール維持といったPMOの管理業務はエージェントが担います。私たちの仕事は、優秀なアナリストが使うのと同じ厳密なツールをエージェントに渡し、人間の役割をより上流のインテリジェンス活動へ移すことです。",
    "home.audience.practitioner.label": "実務者",
    "home.audience.practitioner.body":
      "Excelで手作りのモンテカルロをやめる。ClaudeにSkillを入れる。根拠を示せる同じ数値が得られます。",
    "home.audience.sier.label": "SIer",
    "home.audience.sier.body":
      "顧客のJira / ServiceNow / SAPに接続。必要ならOEMでライセンス統合も。",
    "home.audience.consulting.label": "コンサルティングファーム",
    "home.audience.consulting.body":
      "PMOロジックとツールで過去データを活用。貴社のインサイトを強化します。",

    "home.start.title": "リポジトリをクローンして、すぐに利用可能。",
    "home.start.docs": "ドキュメントを読む",
    "home.start.github": "GitHubで見る",
    "home.start.consult": "あるいは: コンサルティングをご相談ください →",

    "landing.trust.opensource": "オープンソース",
    "landing.trust.privacy": "プライバシー優先",
    "landing.trust.noaccount": "アカウント不要",
    "landing.trust.api": "API提供",

    "blog.title": "ブログ",
    "blog.empty": "まだ投稿はありません。",
    "docs.title": "ドキュメント",
    "docs.empty": "まだドキュメントはありません。",
    "tools.title": "ツール",
    "contact.title": "お問い合わせ",
    "contact.body": "ご質問、フィードバック、提携に関するお問い合わせ：",
    "contact.email": "メールで連絡",

    "about.hero.eyebrow": "§00 / about",
    "about.hero.title": "オープンな手法を、インテリジェンスを担うPMOのために。",
    "about.hero.body":
      "pmo.runは、AIツールと人の判断を組み合わせたPMOサービスのオープンな基盤です。数理を公開し、提供面（Skills・MCP・API）を運用し、校正が要となる個別案件に伴走します。",
    "about.thesis.title": "私たちの存在意義",
    "about.thesis.lede":
      "AI時代における3つのPMO課題。",
    "about.thesis.cell1.title": "AIエージェントには数理ロジックが必要",
    "about.thesis.cell1.body":
      "それっぽい推論や、場当たり的な対応は問題を解決しません。AIエージェントに数理的に検証されたツールを与えることで、貴社の「暗黙知」を再現性のあるシステムに変容させます。",
    "about.thesis.cell2.title": "オープンコア、有償プラグイン",
    "about.thesis.cell2.body":
      "基幹ロジックとツールはオープンソース。PMOコミュニティに貢献します。価値は蓄積されたデータや暗黙知のシステム化にあり、基本ツールの収益化ではありません。",
    "about.thesis.cell3.title": "判断は人の仕事",
    "about.thesis.cell3.body":
      "ステータス集約、差異報告、スケジュール維持 — すべてエージェントが担います。判断を要する業務 — どこに投資するか、何を止めるか、トレードオフをどう伝えるか — は上流の人の仕事として残ります。",
    "about.people.title": "チームメンバー",
    "about.people.lede":
      "日本を拠点とする「人間＋AI」チーム。現役PMO、AI数学者、AI DevSecOpsチーム。PMOの暗黙知をAIが数式化し、ツールを開発しています。",
    "about.contact.title": "コンタクト",
    "about.contact.lede":
      "三つの連絡経路。",
    "about.contact.method1.label": "オープンソース",
    "about.contact.method1.body":
      "GitHubのIssueとRFCをどうぞ。マルウェアやサプライチェーン攻撃を防ぐため、外部・未確認の主体からのプルリクエストは受け付けていません。",
    "about.contact.method2.label": "コンサルティング",
    "about.contact.method2.body":
      "概要を一段落でメールください。二営業日以内に返信します。",
    "about.contact.method3.label": "パートナーシップ",
    "about.contact.method3.body":
      "SIer、コンサルティングファーム、統合パートナーの皆様。一言いただければ、通話を設定します。",

    "tco.calc.mode.single": "単体",
    "tco.calc.mode.compare": "比較",
    "tco.calc.initialPrice": "初期価格",
    "tco.calc.usefulLife": "耐用年数（年）",
    "tco.calc.residualValue": "残存価値",
    "tco.calc.annualMaintenance": "年間メンテナンス費",
    "tco.calc.annualOperating": "年間運用コスト",
    "tco.calc.discountRate": "割引率（%）",
    "tco.calc.calculate": "計算する",
    "tco.calc.reset": "リセット",
    "tco.calc.addOption": "選択肢を追加",
    "tco.calc.remove": "削除",
    "tco.calc.totalCost": "総コスト",
    "tco.calc.annualCost": "年間コスト",
    "tco.calc.monthlyCost": "月間コスト",
    "tco.calc.costPerDay": "日間コスト",
    "tco.calc.npvTco": "NPV調整済みTCO",
    "tco.calc.npvAnnual": "NPV年間コスト",
    "tco.calc.simpleTco": "シンプルTCO",
    "tco.calc.npvAdjusted": "NPV調整済み",
    "tco.calc.bestValue": "最良",
    "tco.calc.validation.positive": "正の値を入力してください",
    "tco.calc.validation.nonNegative": "負の値は入力できません",
    "tco.calc.currency": "¥",
    "tools.pert": "PERT見積もりツール",
    "tools.pert.desc": "三点見積もりに現実補正を加え、プロジェクトスケジュールを精緻化。",
    "pert.calc.title": "PERT見積もり",
    "pert.calc.optimistic": "楽観値 (O)",
    "pert.calc.mostLikely": "最頻値 (M)",
    "pert.calc.pessimistic": "悲観値 (P)",
    "pert.calc.unit": "日",
    "pert.calc.calculate": "計算する",
    "pert.calc.reset": "リセット",
    "pert.calc.textbook": "教科書的PERT",
    "pert.calc.adjusted": "現実補正済み",
    "pert.calc.expected": "期待値",
    "pert.calc.stdDev": "標準偏差",
    "pert.calc.range68": "68%区間",
    "pert.calc.range95": "95%区間",
    "pert.calc.range99": "99.7%区間",
    "pert.calc.delta": "差分",
    "pert.calc.adjustedP": "補正後P",
    "pert.calc.combinedMultiplier": "合成倍率",
    "pert.calc.insightTags": "インサイトタグ",
    "pert.calc.insightTags.desc": "現実の要因を切り替えて、見積もりへの影響を確認。",
    "pert.calc.tag.fragmented": "コミュニケーション分断",
    "pert.calc.tag.fragmented.desc": "チャット・会議・手作業ワークフローによるオーバーヘッド",
    "pert.calc.tag.stakeholders": "複数ステークホルダー",
    "pert.calc.tag.stakeholders.desc": "組織間の利害不一致",
    "pert.calc.tag.dependencies": "隠れた依存関係",
    "pert.calc.tag.dependencies.desc": "文書化されていないタスク関係、上流ブロッカー",
    "pert.calc.severity.mild": "軽度",
    "pert.calc.severity.severe": "重度",
    "pert.calc.rangeComparison": "区間比較",
    "pert.calc.validation.order": "O ≦ M ≦ P を満たしてください",
    "pert.calc.validation.nonNegative": "負の値は入力できません",
    "tools.evm": "EVMトラッカー",
    "tools.evm.desc":
      "アーンドバリューマネジメント — プロジェクトのスケジュールとコストのパフォーマンスをベースラインに対して追跡。",
    "blog.cta.pert": "PERTツールを試す",
    "blog.cta.pert.desc": "現実の調整がどう見積もりを変えるか、試してみてください。",
    "blog.cta.tco": "TCO計算ツールを試す",
    "blog.cta.tco.desc": "選択肢の本当のコストを比較してみてください。",
  },
} as const;
