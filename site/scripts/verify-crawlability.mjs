/**
 * Post-build gate: the promises in robots.txt must be true of dist/.
 *
 * Runs after `astro build` rather than in `npm test`, because what it checks
 * only exists once the site is built — and CI runs `npm test` before
 * `npm run build`. A test that skipped when dist/ was absent would report the
 * same green as one that ran.
 *
 * It reads `dist/robots.txt`, not `public/robots.txt`. Astro copies `public/`
 * verbatim so the two are identical today, but the gate's claim is about what
 * was emitted; if robots.txt ever comes from a template or an integration
 * instead of a static file, reading the source would validate a file nobody
 * ships.
 *
 * Scope, stated plainly: this checks the file we emit. It cannot see
 * Cloudflare's managed robots.txt, a zone setting that prepends its own
 * Disallow rules to the served file and overrides everything below. Only
 * fetching https://pmo.run/robots.txt shows what crawlers receive. Green here
 * means the repository's intent is coherent, not that production is crawlable.
 *
 * The parsing is exported and unit-tested in test/crawlability.spec.ts, since a
 * regression in these regexes would fail the same way the original bug did.
 */

import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join, resolve } from "node:path";

/**
 * Strip a robots.txt comment. `#` opens one at line start or after whitespace;
 * a bare `#` mid-token is left alone so a URL fragment survives.
 *
 * Shared by both parsers deliberately. They previously disagreed — the group
 * parser stripped comments and the `Sitemap:` matcher did not, so
 * `Sitemap: https://… # canonical` would have matched nothing and the gate
 * would have failed with "declares no Sitemap: directive" on a harmless edit.
 * A gate that cries wolf gets switched off, which costs more than the bug it
 * was watching for.
 * @param {string} line
 * @returns {string}
 */
export function stripComment(line) {
  return line.replace(/(^|\s)#.*$/, "$1").trim();
}

/**
 * Every URL named by a `Sitemap:` directive.
 * @param {string} robots
 * @returns {string[]}
 */
export function sitemapUrls(robots) {
  return robots
    .split(/\r?\n/)
    .map(stripComment)
    .map((line) => line.match(/^Sitemap:[ \t]*(\S+)$/i))
    .filter((m) => m !== null)
    .map((m) => m[1]);
}

/**
 * Parse robots.txt into groups. A group is one or more consecutive `User-agent`
 * lines followed by that group's rules — the shape RFC 9309 describes. Written
 * as a line walk rather than one regex because the regex version could only see
 * single-agent groups, and silently passed a group naming two.
 * @param {string} robots
 * @returns {{ agents: string[], rules: { name: string, value: string }[] }[]}
 */
export function parseGroups(robots) {
  /** @type {{ agents: string[], rules: { name: string, value: string }[] }[]} */
  const groups = [];
  /** @type {{ agents: string[], rules: { name: string, value: string }[] } | null} */
  let current = null;

  for (const raw of robots.split(/\r?\n/)) {
    const line = stripComment(raw);
    if (line === "") continue;
    const match = line.match(/^([A-Za-z-]+)[ \t]*:[ \t]*(.*)$/);
    if (!match) continue;
    const name = match[1].toLowerCase();
    const value = match[2].trim();

    if (name === "user-agent") {
      // A User-agent line after rules opens a new group; before any rules it
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
 * Every non-empty `Disallow` in the file, with the agents it applies to.
 *
 * This deliberately has no allowlist of crawler names. An earlier version
 * checked five named bots, which was narrower than the eight the file's own
 * comment discusses and drifted from the stance the site actually takes: this
 * site disallows nothing, from anyone. A list of names is a second place for
 * that stance to live, and the two had already disagreed.
 *
 * So the rule is the stance: **any** disallowed path fails the build. If the
 * site ever needs to withhold something — from a crawler or from anyone else —
 * that is a deliberate change to this check, made in the same commit as the
 * robots.txt edit, rather than a name quietly missing from a list.
 *
 * A bare `Disallow:` is the opposite directive (allow all) and is ignored.
 * @param {string} robots
 * @returns {{ agents: string[], path: string }[]}
 */
export function disallowedPaths(robots) {
  return parseGroups(robots).flatMap((group) =>
    group.rules
      .filter((rule) => rule.name === "disallow" && rule.value !== "")
      .map((rule) => ({ agents: group.agents, path: rule.value })),
  );
}

/** @param {string} xml @returns {string[]} */
export function locs(xml) {
  return [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
}

/**
 * The gate itself. Returns human-readable failures; empty means green.
 * @param {{ distDir: string, exists: (p: string) => boolean, read: (p: string) => string }} io
 * @returns {{ failures: string[], notes: string[] }}
 */
export function check(io) {
  /** @type {string[]} */
  const failures = [];
  /** @type {string[]} */
  const notes = [];

  const robotsPath = join(io.distDir, "robots.txt");
  if (!io.exists(robotsPath)) {
    return { failures: [`${robotsPath} was not emitted — the site ships no robots.txt.`], notes };
  }
  const robots = io.read(robotsPath);
  const urls = sitemapUrls(robots);

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

  for (const { agents, path } of disallowedPaths(robots)) {
    failures.push(
      `robots.txt disallows ${path} from ${agents.join(", ")}. ` +
        "This site withholds nothing; change this check in the same commit if that is no longer true.",
    );
  }

  return { failures, notes };
}

// CLI. Guarded so the module can be imported by tests without running or exiting.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  const { failures, notes } = check({
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
