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
      "Free, open-source TCO calculator and cost analysis tools for project managers and PMO teams.",
    "nav.home": "Home",
    "nav.tools": "Tools",
    "nav.blog": "Blog",
    "nav.docs": "Docs",
    "nav.contact": "Contact",
    "footer.copy": "pmo.run",
    "footer.github": "GitHub",
    "footer.blog": "Blog",
    "footer.docs": "Docs",
    "tools.tco": "TCO Calculator",
    "tools.tco.desc": "Total Cost of Ownership analysis for informed purchasing decisions.",
    "tools.breakeven": "Break-Even Analysis",
    "tools.breakeven.desc": "Find the point where revenue meets costs.",
    "landing.hero": "Ship decisions, not spreadsheets.",
    "landing.sub":
      "Free, open-source tools for TCO analysis and cost comparison. No account required. Your data never leaves your browser.",
    "landing.cta": "Calculate TCO — Free",
    "landing.features.title": "Built for real decisions",
    "landing.features.tco.title": "TCO Analysis",
    "landing.features.tco.desc":
      "Compare total cost of ownership across options with NPV adjustment, maintenance factors, and replacement cycles.",
    "landing.features.compare.title": "Side-by-Side Comparison",
    "landing.features.compare.desc":
      "Rank multiple options by annual cost. See which choice actually saves money over 3, 5, or 10 years.",
    "landing.features.breakeven.title": "Break-Even Point",
    "landing.features.breakeven.desc":
      "Find exactly when a higher upfront investment pays off compared to the cheaper alternative.",
    "landing.trust.opensource": "Open Source",
    "landing.trust.privacy": "Privacy-First",
    "landing.trust.noaccount": "No Account Required",
    "landing.trust.api": "API Available",
    "landing.secondary.text": "View source on GitHub",
    "landing.secondary.url": "https://github.com/lemur47/logic",
    "blog.title": "Blog",
    "blog.empty": "No posts yet.",
    "docs.title": "Documentation",
    "docs.empty": "No docs yet.",
    "contact.title": "Contact",
    "contact.body": "Questions, feedback, or partnership inquiries:",
    "contact.email": "Email us",
  },
  ja: {
    "site.title": "pmo.run",
    "site.description":
      "PM/PMOのための、無料・オープンソースのTCO計算ツール。",
    "nav.home": "ホーム",
    "nav.tools": "ツール",
    "nav.blog": "ブログ",
    "nav.docs": "ドキュメント",
    "nav.contact": "お問い合わせ",
    "footer.copy": "pmo.run",
    "footer.github": "GitHub",
    "footer.blog": "ブログ",
    "footer.docs": "ドキュメント",
    "tools.tco": "TCO計算ツール",
    "tools.tco.desc": "総所有コスト分析で、購買判断を数値で裏付ける。",
    "tools.breakeven": "損益分岐点分析",
    "tools.breakeven.desc": "収益がコストを上回るポイントを見つける。",
    "landing.hero": "スプレッドシートではなく、意思決定の質を高めよう。",
    "landing.sub":
      "TCO分析とコスト比較のためのオープンソースツール。アカウント不要、データは収集されません。",
    "landing.cta": "TCOを計算する（無料）",
    "landing.features.title": "実践的な意思決定ツール",
    "landing.features.tco.title": "TCO分析",
    "landing.features.tco.desc":
      "NPV調整、メンテナンス係数、リプレースサイクルを考慮し、選択肢ごとの総所有コストを比較。",
    "landing.features.compare.title": "並列比較",
    "landing.features.compare.desc":
      "複数の選択肢を年間コスト順にランキング。3年、5年、10年で本当に節約できるのはどれか。",
    "landing.features.breakeven.title": "損益分岐点",
    "landing.features.breakeven.desc":
      "初期投資が高い選択肢が、安価な代替案と比べて何年で元が取れるかを正確に算出。",
    "landing.trust.opensource": "オープンソース",
    "landing.trust.privacy": "プライバシー優先",
    "landing.trust.noaccount": "アカウント不要",
    "landing.trust.api": "API提供",
    "landing.secondary.text": "GitHubでソースを見る",
    "landing.secondary.url": "https://github.com/lemur47/logic",
    "blog.title": "ブログ",
    "blog.empty": "まだ投稿はありません。",
    "docs.title": "ドキュメント",
    "docs.empty": "まだドキュメントはありません。",
    "contact.title": "お問い合わせ",
    "contact.body": "ご質問、フィードバック、提携に関するお問い合わせ：",
    "contact.email": "メールで連絡",
  },
} as const;
