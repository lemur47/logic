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

describe("check", () => {
  const index =
    "<sitemapindex><sitemap><loc>https://pmo.run/sitemap-0.xml</loc></sitemap></sitemapindex>";
  const pages = "<urlset><url><loc>https://pmo.run/en/</loc></url></urlset>";

  const io = (files: Record<string, string>) => ({
    distDir: "/dist",
    exists: (p: string) => p in files,
    read: (p: string) => files[p],
  });

  const emitted = {
    "/dist/robots.txt": LIVE,
    "/dist/sitemap-index.xml": index,
    "/dist/sitemap-0.xml": pages,
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

  it("fails on any disallowed path, naming the agents", () => {
    const blocked = `${LIVE}\nUser-agent: Amazonbot\nDisallow: /en/\n`;
    const result = check(io({ ...emitted, "/dist/robots.txt": blocked }));
    expect(result.failures).toHaveLength(1);
    expect(result.failures[0]).toContain("disallows /en/ from Amazonbot");
  });
});
