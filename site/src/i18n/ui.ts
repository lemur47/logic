export const languages = {
  en: "English",
  ja: "日本語",
} as const;

export type Lang = keyof typeof languages;

export const defaultLang: Lang = "en";

export const ui = {
  en: {
    "site.title": "PMO — Decision Logic",
    "site.description":
      "Atomic logic for decision-making. Open-source calculators for TCO, NPV, IRR, and more.",
    "nav.home": "Home",
    "nav.tools": "Tools",
    "nav.blog": "Blog",
    "nav.docs": "Docs",
    "nav.contact": "Contact",
    "footer.copy": "PMO. Open source.",
    "tools.tco": "TCO Calculator",
    "tools.tco.desc": "Total Cost of Ownership analysis for informed purchasing decisions.",
    "tools.breakeven": "Break-Even Analysis",
    "tools.breakeven.desc": "Find the point where revenue meets costs.",
    "landing.hero": "Decision logic, not gut feeling.",
    "landing.sub":
      "Open-source calculators that turn abstract costs into concrete numbers.",
    "landing.cta": "Try the TCO Calculator",
    "blog.title": "Blog",
    "blog.empty": "No posts yet.",
    "docs.title": "Documentation",
    "docs.empty": "No docs yet.",
    "contact.title": "Contact",
    "contact.body": "Questions, feedback, or partnership inquiries:",
    "contact.email": "Email us",
  },
  ja: {
    "site.title": "PMO — 意思決定ロジック",
    "site.description":
      "意思決定のためのアトミックロジック。TCO、NPV、IRRなどのオープンソース計算ツール。",
    "nav.home": "ホーム",
    "nav.tools": "ツール",
    "nav.blog": "ブログ",
    "nav.docs": "ドキュメント",
    "nav.contact": "お問い合わせ",
    "footer.copy": "PMO. オープンソース。",
    "tools.tco": "TCO計算ツール",
    "tools.tco.desc": "総所有コスト分析で、購買判断を数値で裏付ける。",
    "tools.breakeven": "損益分岐点分析",
    "tools.breakeven.desc": "収益がコストを上回るポイントを見つける。",
    "landing.hero": "勘ではなく、ロジックで決める。",
    "landing.sub": "抽象的なコストを具体的な数字に変えるオープンソース計算ツール。",
    "landing.cta": "TCO計算ツールを試す",
    "blog.title": "ブログ",
    "blog.empty": "まだ投稿はありません。",
    "docs.title": "ドキュメント",
    "docs.empty": "まだドキュメントはありません。",
    "contact.title": "お問い合わせ",
    "contact.body": "ご質問、フィードバック、提携に関するお問い合わせ：",
    "contact.email": "メールで連絡",
  },
} as const;
