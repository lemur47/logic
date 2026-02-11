import { ui, defaultLang, type Lang } from "./ui";

/** Extract language code from a URL pathname like /en/blog/... */
export function getLangFromUrl(url: URL): Lang {
  const [, lang] = url.pathname.split("/");
  if (lang in ui) return lang as Lang;
  return defaultLang;
}

/** Return a translation function bound to a language. */
export function useTranslations(lang: Lang) {
  return function t(key: keyof (typeof ui)[typeof defaultLang]): string {
    return (ui[lang] as Record<string, string>)[key] ?? ui[defaultLang][key];
  };
}

/** Build a localized path: getLocalizedPath("/tools/tco", "ja") → "/ja/tools/tco" */
export function getLocalizedPath(path: string, lang: Lang): string {
  const clean = path.replace(/^\/(?:en|ja)/, "");
  return `/${lang}${clean || "/"}`;
}

/**
 * Parse a content entry id like "en/my-post" into { lang, slug }.
 * Works with both flat ("en/my-post.md") and nested ("en/my-post/index.md") layouts.
 */
export function parseEntryLocale(id: string): { lang: Lang; slug: string } {
  const [lang, ...rest] = id.split("/");
  const slug = rest.join("/").replace(/\.mdx?$/, "");
  return { lang: (lang in ui ? lang : defaultLang) as Lang, slug };
}
