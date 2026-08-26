/**
 * Unit tests for the crawlability gate's own parsing.
 *
 * The gate in `scripts/verify-crawlability.mjs` is the only guard against the
 * incident it documents: robots.txt advertising a sitemap that production
 * returned 404 for, with nothing failing. A regression in its regexes would
 * reproduce that failure exactly — nothing reported, because nothing was
 * testing the tester. So the parsing is tested here, and the end-to-end
 * behaviour against a real `dist/` stays a canary run at build time.
 *
 * These cases are pure string-in / findings-out, so they run in `npm test`
 * without needing a build.
 */

import { describe, expect, it } from "vitest";

import {
  blockedAdmittedBots,
  check,
  parseGroups,
  sitemapUrls,
} from "../scripts/verify-crawlability.mjs";

const LIVE = `User-agent: *
Content-Signal: search=yes, ai-input=yes, ai-train=yes, use=full
Allow: /

Sitemap: https://pmo.run/sitemap-index.xml
`;

describe("sitemapUrls", () => {
  it("finds the declared sitemap", () => {
    expect(sitemapUrls(LIVE)).toEqual(["https://pmo.run/sitemap-index.xml"]);
  });

  it("is case-insensitive and tolerates extra whitespace", () => {
    expect(sitemapUrls("  sitemap:   https://x/y.xml  ")).toEqual(["https://x/y.xml"]);
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

describe("blockedAdmittedBots", () => {
  it("passes the file we ship", () => {
    expect(blockedAdmittedBots(LIVE)).toEqual([]);
  });

  it("catches a full block", () => {
    expect(blockedAdmittedBots(`${LIVE}\nUser-agent: ClaudeBot\nDisallow: /\n`)).toEqual([
      { bot: "ClaudeBot", path: "/" },
    ]);
  });

  it("catches a PARTIAL block, which an exact-match check missed", () => {
    expect(blockedAdmittedBots(`${LIVE}\nUser-agent: GPTBot\nDisallow: /blog/\n`)).toEqual([
      { bot: "GPTBot", path: "/blog/" },
    ]);
  });

  it("catches a bot named alongside others in a shared group", () => {
    const robots = `${LIVE}\nUser-agent: SomeBot\nUser-agent: CCBot\nDisallow: /docs/\n`;
    expect(blockedAdmittedBots(robots)).toEqual([{ bot: "CCBot", path: "/docs/" }]);
  });

  it("matches the agent name case-insensitively, as the RFC requires", () => {
    expect(blockedAdmittedBots("User-agent: claudebot\nDisallow: /\n")).toEqual([
      { bot: "ClaudeBot", path: "/" },
    ]);
  });

  it("treats a bare Disallow: as the allow-all directive it is", () => {
    expect(blockedAdmittedBots("User-agent: ClaudeBot\nDisallow:\n")).toEqual([]);
  });

  it("reports nothing for a bot with no group — it falls to *", () => {
    expect(blockedAdmittedBots("User-agent: *\nAllow: /\n")).toEqual([]);
  });
});

describe("check", () => {
  const index = "<sitemapindex><sitemap><loc>https://pmo.run/sitemap-0.xml</loc></sitemap></sitemapindex>";
  const pages = "<urlset><url><loc>https://pmo.run/en/</loc></url></urlset>";

  const io = (files: Record<string, string>) => ({
    robots: LIVE,
    distDir: "/dist",
    exists: (p: string) => p in files,
    read: (p: string) => files[p],
  });

  it("is green when the advertised sitemap resolves and lists URLs", () => {
    const result = check(io({ "/dist/sitemap-index.xml": index, "/dist/sitemap-0.xml": pages }));
    expect(result.failures).toEqual([]);
    expect(result.notes).toEqual(["https://pmo.run/sitemap-0.xml lists 1 URLs."]);
  });

  it("fails when the advertised sitemap was not emitted", () => {
    const result = check(io({}));
    expect(result.failures).toHaveLength(1);
    expect(result.failures[0]).toContain("sitemap-index.xml");
  });

  it("fails when the index points at a child that was not emitted", () => {
    const result = check(io({ "/dist/sitemap-index.xml": index }));
    expect(result.failures).toHaveLength(1);
    expect(result.failures[0]).toContain("sitemap-0.xml");
  });

  it("fails when the child sitemap lists no pages", () => {
    const empty = "<urlset></urlset>";
    const result = check(io({ "/dist/sitemap-index.xml": index, "/dist/sitemap-0.xml": empty }));
    expect(result.failures).toEqual(["https://pmo.run/sitemap-0.xml lists zero URLs."]);
  });

  it("fails when robots.txt declares no sitemap at all", () => {
    const result = check({ ...io({}), robots: "User-agent: *\nAllow: /\n" });
    expect(result.failures).toEqual(["robots.txt declares no Sitemap: directive."]);
  });
});
