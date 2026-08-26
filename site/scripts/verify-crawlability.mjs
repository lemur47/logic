/**
 * Post-build gate: the promises in robots.txt must be true of dist/.
 *
 * This runs AFTER `astro build` rather than in `npm test`, because what it
 * checks only exists once the site is built — and CI runs `npm test` before
 * `npm run build`. A test that skipped when dist/ was absent would be worse
 * than no test: a gate that skips and a gate that passes read identically.
 *
 * What went wrong without it: robots.txt named
 * https://pmo.run/sitemap-index.xml as the single entry point we hand a
 * crawler, no sitemap integration was installed, and that URL returned 404 in
 * production for as long as anyone had been looking. Nothing failed, because
 * nothing was watching.
 *
 * Scope, stated honestly: this checks the file WE ship. It cannot see
 * Cloudflare's managed robots.txt, which is a zone setting that prepends its
 * own Disallow rules to the served file and overrides everything below it.
 * Only fetching https://pmo.run/robots.txt shows what crawlers receive. So a
 * green result here proves the repository's intent is coherent — never that
 * production is actually crawlable.
 *
 * The parsing below is exported and unit-tested in test/crawlability.spec.ts.
 * This script is the only guard against the incident described above, so a
 * silent regression in its own regexes would fail exactly the way the original
 * bug did: nothing reported, because nothing was testing the tester.
 */

import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join, resolve } from "node:path";

/**
 * Crawlers this site admits. If that stance is ever reversed, change this list
 * in the same commit as robots.txt, so the reversal is deliberate rather than a
 * stray edit.
 * @type {readonly string[]}
 */
export const ADMITTED = ["ClaudeBot", "GPTBot", "Google-Extended", "CCBot", "PerplexityBot"];

/**
 * Every URL named by a `Sitemap:` directive.
 * @param {string} robots
 * @returns {string[]}
 */
export function sitemapUrls(robots) {
  return [...robots.matchAll(/^[ \t]*Sitemap:[ \t]*(\S+)[ \t]*$/gim)].map((m) => m[1]);
}

/**
 * Parse robots.txt into groups. A group is one or more consecutive `User-agent`
 * lines followed by that group's rules — the shape RFC 9309 defines. Written as
 * a line walk rather than one regex because the regex version could only see
 * single-agent groups, and silently passed a group that named two.
 * @param {string} robots
 * @returns {{ agents: string[], rules: { name: string, value: string }[] }[]}
 */
export function parseGroups(robots) {
  /** @type {{ agents: string[], rules: { name: string, value: string }[] }[]} */
  const groups = [];
  /** @type {{ agents: string[], rules: { name: string, value: string }[] } | null} */
  let current = null;

  for (const raw of robots.split(/\r?\n/)) {
    const line = raw.replace(/#.*$/, "").trim();
    if (line === "") continue;
    const match = line.match(/^([A-Za-z-]+)[ \t]*:[ \t]*(.*)$/);
    if (!match) continue;
    const name = match[1].toLowerCase();
    const value = match[2].trim();

    if (name === "user-agent") {
      // A User-agent line after rules starts a new group; before any rules it
      // adds another agent to the group being opened.
      if (current === null || current.rules.length > 0) {
        current = { agents: [], rules: [] };
        groups.push(current);
      }
      current.agents.push(value);
    } else if (current !== null) {
      current.rules.push({ name, value });
    }
  }
  return groups;
}

/**
 * Admitted crawlers that robots.txt disallows from anything at all.
 *
 * Any non-empty `Disallow` value counts. An earlier version only flagged an
 * exact `Disallow: /`, so `Disallow: /blog/` — a real block of real content —
 * passed the gate. A bare `Disallow:` is the opposite directive (allow all) and
 * is correctly ignored. A bot with no group of its own falls to `*` and is not
 * blocked, so its absence is not a finding.
 * @param {string} robots
 * @param {readonly string[]} [admitted]
 * @returns {{ bot: string, path: string }[]}
 */
export function blockedAdmittedBots(robots, admitted = ADMITTED) {
  /** @type {{ bot: string, path: string }[]} */
  const found = [];
  const groups = parseGroups(robots);
  for (const bot of admitted) {
    for (const group of groups) {
      if (!group.agents.some((a) => a.toLowerCase() === bot.toLowerCase())) continue;
      for (const rule of group.rules) {
        if (rule.name === "disallow" && rule.value !== "") {
          found.push({ bot, path: rule.value });
        }
      }
    }
  }
  return found;
}

/** @param {string} xml @returns {string[]} */
export function locs(xml) {
  return [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
}

/**
 * The gate itself. Returns human-readable failures; empty means green.
 * @param {{ robots: string, distDir: string, exists: (p: string) => boolean, read: (p: string) => string }} io
 * @returns {{ failures: string[], notes: string[] }}
 */
export function check(io) {
  const failures = [];
  const notes = [];
  const urls = sitemapUrls(io.robots);

  if (urls.length === 0) failures.push("robots.txt declares no Sitemap: directive.");

  for (const url of urls) {
    const path = join(io.distDir, new URL(url).pathname);
    if (!io.exists(path)) {
      failures.push(
        `robots.txt advertises ${url}, but ${path} was not emitted. ` +
          "Either the sitemap integration is missing from astro.config.mjs, or the URL is wrong.",
      );
      continue;
    }
    const body = io.read(path);
    const refs = locs(body);
    if (refs.length === 0) {
      failures.push(`${url} contains no <loc> entries.`);
      continue;
    }
    if (!body.includes("<sitemapindex")) continue;
    for (const ref of refs) {
      const child = join(io.distDir, new URL(ref).pathname);
      if (!io.exists(child)) {
        failures.push(`${url} points at ${ref}, which was not emitted.`);
        continue;
      }
      const count = [...io.read(child).matchAll(/<url>/g)].length;
      if (count === 0) failures.push(`${ref} lists zero URLs.`);
      else notes.push(`${ref} lists ${count} URLs.`);
    }
  }

  for (const { bot, path } of blockedAdmittedBots(io.robots)) {
    failures.push(`robots.txt disallows ${bot} from ${path}, and ${bot} is an admitted crawler.`);
  }

  return { failures, notes };
}

// CLI. Guarded so the module can be imported by tests without running or exiting.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  const { failures, notes } = check({
    robots: readFileSync(join(siteRoot, "public", "robots.txt"), "utf8"),
    distDir: join(siteRoot, "dist"),
    exists: existsSync,
    read: (p) => readFileSync(p, "utf8"),
  });
  for (const note of notes) console.log(`[crawlability] ${note}`);
  if (failures.length > 0) {
    console.error("\n[crawlability] FAILED:\n" + failures.map((f) => `  - ${f}`).join("\n") + "\n");
    process.exit(1);
  }
  console.log("[crawlability] robots.txt promises hold against dist/.");
}
