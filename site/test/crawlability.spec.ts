/**
 * Unit tests for the crawlability gate's own parsing.
 *
 * The gate in `scripts/verify-crawlability.mjs` guards against robots.txt
 * advertising a sitemap that production returns 404 for, with nothing failing.
 * A regression in its regexes would reproduce that silence exactly, so the
 * parsing is tested here; the end-to-end behaviour against a real `dist/` stays
 * a canary run at build time, which is the part a unit test cannot stand in for.
 *
 * Pure string-in / findings-out, so these run in `npm test` without a build.
 */

import { describe, expect, it } from "vitest";

import {
  advertisedUrls,
  isExemptFromSitemap,
  candidatePaths,
  pathnameOf,
  check,
  disallowedPaths,
  parseGroups,
  sitemapUrls,
  stripComment,
} from "../scripts/verify-crawlability.mjs";

const LIVE = `User-agent: *
Content-Signal: search=yes, ai-input=yes, ai-train=yes, use=full
Allow: /

Sitemap: https://pmo.run/sitemap-index.xml
`;

describe("stripComment", () => {
  it("removes a trailing comment", () => {
    expect(stripComment("Allow: / # everything")).toBe("Allow: /");
  });

  it("removes a whole-line comment", () => {
    expect(stripComment("  # just a note")).toBe("");
  });

  it("leaves a URL fragment alone — # only opens a comment after whitespace", () => {
    expect(stripComment("Sitemap: https://x/y.xml#frag")).toBe("Sitemap: https://x/y.xml#frag");
  });
});

describe("sitemapUrls", () => {
  it("finds the declared sitemap", () => {
    expect(sitemapUrls(LIVE)).toEqual(["https://pmo.run/sitemap-index.xml"]);
  });

  it("is case-insensitive and tolerates extra whitespace", () => {
    expect(sitemapUrls("  sitemap:   https://x/y.xml  ")).toEqual(["https://x/y.xml"]);
  });

  it("survives a trailing comment, which an end-anchored regex did not", () => {
    expect(sitemapUrls("Sitemap: https://x/y.xml # canonical")).toEqual(["https://x/y.xml"]);
  });

  it("finds nothing when none is declared", () => {
    expect(sitemapUrls("User-agent: *\nAllow: /\n")).toEqual([]);
  });
});

describe("parseGroups", () => {
  it("keeps consecutive User-agent lines in one group", () => {
    const groups = parseGroups("User-agent: A\nUser-agent: B\nDisallow: /\n");
    expect(groups).toHaveLength(1);
    expect(groups[0].agents).toEqual(["A", "B"]);
  });

  it("starts a new group at a User-agent line that follows rules", () => {
    const groups = parseGroups("User-agent: A\nDisallow: /\nUser-agent: B\nAllow: /\n");
    expect(groups.map((g) => g.agents)).toEqual([["A"], ["B"]]);
  });

  it("ignores comments and blank lines", () => {
    expect(parseGroups("# note\n\nUser-agent: A # trailing\nAllow: /\n")[0].agents).toEqual(["A"]);
  });
});

describe("disallowedPaths", () => {
  it("passes the file we ship — this site withholds nothing", () => {
    expect(disallowedPaths(LIVE)).toEqual([]);
  });

  it("catches a full block", () => {
    expect(disallowedPaths(`${LIVE}\nUser-agent: ClaudeBot\nDisallow: /\n`)).toEqual([
      { agents: ["ClaudeBot"], path: "/" },
    ]);
  });

  it("catches a PARTIAL block, which an exact-match check missed", () => {
    expect(disallowedPaths(`${LIVE}\nUser-agent: GPTBot\nDisallow: /blog/\n`)).toEqual([
      { agents: ["GPTBot"], path: "/blog/" },
    ]);
  });

  it("catches a crawler no allowlist happened to name", () => {
    expect(disallowedPaths(`${LIVE}\nUser-agent: Bytespider\nDisallow: /\n`)).toEqual([
      { agents: ["Bytespider"], path: "/" },
    ]);
  });

  it("reports every agent in a shared group", () => {
    expect(disallowedPaths("User-agent: A\nUser-agent: CCBot\nDisallow: /docs/\n")).toEqual([
      { agents: ["A", "CCBot"], path: "/docs/" },
    ]);
  });

  it("treats a bare Disallow: as the allow-all directive it is", () => {
    expect(disallowedPaths("User-agent: ClaudeBot\nDisallow:\n")).toEqual([]);
  });
});

describe("advertisedUrls", () => {
  const entry = `<url><loc>https://pmo.run/en/x/</loc>` +
    `<xhtml:link rel="alternate" hreflang="en" href="https://pmo.run/en/x/"/>` +
    `<xhtml:link rel="alternate" hreflang="ja" href="https://pmo.run/ja/x/"/></url>`;

  it("returns locations and hreflang alternates alike", () => {
    expect(advertisedUrls(entry).sort()).toEqual([
      "https://pmo.run/en/x/",
      "https://pmo.run/ja/x/",
    ]);
  });

  it("deduplicates a location that is also its own alternate", () => {
    expect(advertisedUrls(entry)).toHaveLength(2);
  });
});

describe("pathnameOf", () => {
  it("returns the pathname of an absolute URL", () => {
    expect(pathnameOf("https://pmo.run/en/blog/")).toBe("/en/blog/");
  });

  it("returns null rather than throwing on a relative URL", () => {
    expect(pathnameOf("/en/blog/")).toBeNull();
  });
});

describe("candidatePaths", () => {
  it("maps a directory URL to its index.html", () => {
    expect(candidatePaths("/dist", "https://pmo.run/en/blog/")).toEqual(["/dist/en/blog/index.html"]);
  });

  it("yields nothing for a URL it cannot parse", () => {
    expect(candidatePaths("/dist", "not a url")).toEqual([]);
  });

  it("accepts every shape a build format might emit", () => {
    expect(candidatePaths("/dist", "https://pmo.run/feed.xml")).toEqual([
      "/dist/feed.xml",
      "/dist/feed.xml/index.html",
      "/dist/feed.xml.html",
    ]);
  });
});

describe("isExemptFromSitemap", () => {
  it("exempts the 404 page", () => {
    expect(isExemptFromSitemap("404.html", "<html></html>")).toBe(true);
  });

  it("exempts a page that declares noindex", () => {
    const stub = '<meta name="robots" content="noindex"><title>Redirecting</title>';
    expect(isExemptFromSitemap("index.html", stub)).toBe(true);
  });

  it("exempts noindex written with the attributes reversed", () => {
    expect(isExemptFromSitemap("x.html", '<meta content="noindex" name="robots">')).toBe(true);
  });

  it("does not confuse two separate meta tags for one", () => {
    const decoys = '<meta name="robots" content="all"><meta name="description" content="noindex">';
    expect(isExemptFromSitemap("x.html", decoys)).toBe(false);
  });

  it("does NOT exempt an ordinary page — that is the point", () => {
    expect(isExemptFromSitemap("index.html", "<html><body>Home</body></html>")).toBe(false);
  });
});

describe("check", () => {
  const index =
    "<sitemapindex><sitemap><loc>https://pmo.run/sitemap-0.xml</loc></sitemap></sitemapindex>";
  const pages =
    "<urlset><url><loc>https://pmo.run/en/</loc>" +
    '<xhtml:link rel="alternate" hreflang="ja" href="https://pmo.run/ja/"/></url></urlset>';

  const io = (files: Record<string, string>) => ({
    distDir: "/dist",
    exists: (p: string) => p in files,
    read: (p: string) => files[p],
    listHtml: () =>
      Object.keys(files)
        .filter((p) => p.endsWith(".html"))
        .map((p) => p.replace("/dist/", "")),
  });

  const emitted = {
    "/dist/robots.txt": LIVE,
    "/dist/sitemap-index.xml": index,
    "/dist/sitemap-0.xml": pages,
    "/dist/en/index.html": "<html></html>",
    "/dist/ja/index.html": "<html></html>",
  };

  it("is green when the advertised sitemap resolves and lists URLs", () => {
    const result = check(io(emitted));
    expect(result.failures).toEqual([]);
    expect(result.notes).toEqual(["https://pmo.run/sitemap-0.xml lists 1 URLs."]);
  });

  it("fails when no robots.txt was emitted at all", () => {
    const result = check(io({}));
    expect(result.failures).toEqual(["/dist/robots.txt was not emitted — the site ships no robots.txt."]);
  });

  it("reads dist/, not public/ — a stale source file cannot make it pass", () => {
    const result = check(io({ ...emitted, "/dist/robots.txt": "User-agent: *\nAllow: /\n" }));
    expect(result.failures).toEqual(["robots.txt declares no Sitemap: directive."]);
  });

  it("fails when the advertised sitemap was not emitted", () => {
    const result = check(io({ "/dist/robots.txt": LIVE }));
    expect(result.failures).toHaveLength(1);
    expect(result.failures[0]).toContain("sitemap-index.xml");
  });

  it("fails when the index points at a child that was not emitted", () => {
    const result = check(io({ "/dist/robots.txt": LIVE, "/dist/sitemap-index.xml": index }));
    expect(result.failures).toHaveLength(1);
    expect(result.failures[0]).toContain("sitemap-0.xml");
  });

  it("fails when the child sitemap lists no pages", () => {
    const result = check(io({ ...emitted, "/dist/sitemap-0.xml": "<urlset></urlset>" }));
    expect(result.failures).toEqual(["https://pmo.run/sitemap-0.xml lists zero URLs."]);
  });

  it("fails when an advertised page was not emitted", () => {
    const { "/dist/ja/index.html": _dropped, ...withoutJa } = emitted;
    const result = check(io(withoutJa));
    expect(result.failures).toHaveLength(1);
    expect(result.failures[0]).toContain("https://pmo.run/ja/");
  });

  it("fails on an hreflang alternate pointing at a slug that does not exist", () => {
    const mismatched = pages.replace("https://pmo.run/ja/\"", "https://pmo.run/ja/other/\"");
    const result = check(io({ ...emitted, "/dist/sitemap-0.xml": mismatched }));
    expect(result.failures).toHaveLength(1);
    expect(result.failures[0]).toContain("https://pmo.run/ja/other/");
  });

  it("logs the page count for a leaf sitemap with no index above it", () => {
    const flat = { ...emitted, "/dist/robots.txt": LIVE.replace("sitemap-index.xml", "sitemap-0.xml") };
    const result = check(io(flat));
    expect(result.failures).toEqual([]);
    expect(result.notes).toEqual(["https://pmo.run/sitemap-0.xml lists 1 URLs."]);
  });

  it("reports a relative sitemap URL as a gate failure, not a crash", () => {
    const relative = LIVE.replace("https://pmo.run/sitemap-index.xml", "/sitemap-index.xml");
    const result = check(io({ ...emitted, "/dist/robots.txt": relative }));
    expect(result.failures).toEqual([
      "robots.txt advertises /sitemap-index.xml, which is not an absolute URL.",
    ]);
  });

  it("reports a relative page URL as a gate failure, not a crash", () => {
    const relative = pages.replace("https://pmo.run/en/", "/en/");
    const result = check(io({ ...emitted, "/dist/sitemap-0.xml": relative }));
    expect(result.failures).toHaveLength(1);
    expect(result.failures[0]).toContain("not absolute");
  });

  it("fails when an emitted page appears in no sitemap", () => {
    const orphan = { ...emitted, "/dist/en/orphan/index.html": "<html>lost</html>" };
    const result = check(io(orphan));
    expect(result.failures).toHaveLength(1);
    expect(result.failures[0]).toContain("en/orphan/index.html");
  });

  it("does not fault a page that declares noindex", () => {
    const stub = { ...emitted, "/dist/index.html": '<meta name="robots" content="noindex">' };
    expect(check(io(stub)).failures).toEqual([]);
  });

  it("does not fault the 404 page", () => {
    expect(check(io({ ...emitted, "/dist/404.html": "<html>gone</html>" })).failures).toEqual([]);
  });

  it("does not pile completeness noise on top of a broken sitemap", () => {
    // Every page would be 'unadvertised' when the sitemap cannot be read. The
    // build fails on the root cause alone.
    const result = check(io({ "/dist/robots.txt": LIVE, "/dist/en/index.html": "<html></html>" }));
    expect(result.failures).toHaveLength(1);
    expect(result.failures[0]).toContain("sitemap-index.xml");
  });

  it("fails on any disallowed path, naming the agents", () => {
    const blocked = `${LIVE}\nUser-agent: Amazonbot\nDisallow: /en/\n`;
    const result = check(io({ ...emitted, "/dist/robots.txt": blocked }));
    expect(result.failures).toHaveLength(1);
    expect(result.failures[0]).toContain("disallows /en/ from Amazonbot");
  });
});
