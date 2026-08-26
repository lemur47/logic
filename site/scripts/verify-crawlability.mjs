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
 * Every URL a sitemap advertises to a crawler: the `<loc>` of each entry AND
 * every `hreflang` alternate. The alternates matter as much as the locations —
 * an alternate is a promise that the same document exists at that URL in that
 * language, and a crawler follows it.
 * @param {string} xml
 * @returns {string[]}
 */
export function advertisedUrls(xml) {
  const alternates = [...xml.matchAll(/<xhtml:link\b[^>]*\bhref="([^"]+)"/g)].map((m) => m[1]);
  return [...new Set([...locs(xml), ...alternates])];
}

/**
 * A URL's pathname, or null if it is not an absolute URL.
 *
 * Every URL here arrives from a generated file rather than from us, so a
 * malformed one is possible — `@astrojs/sitemap` emits relative URLs if `site`
 * is unset in astro.config.mjs, and emission has changed shape across major
 * versions before. Unguarded, `new URL()` would throw a raw TypeError and take
 * the build down with a stack trace, which defeats the point of a gate whose
 * whole value is a readable failure message.
 * @param {string} url
 * @returns {string | null}
 */
export function pathnameOf(url) {
  try {
    return new URL(url).pathname;
  } catch {
    return null;
  }
}

/**
 * Where a URL's page should have been emitted. A directory-style URL is
 * `index.html` inside it; a file-style URL may be either the file itself or a
 * directory with an index, depending on the build's trailing-slash handling, so
 * both are accepted.
 * @param {string} distDir
 * @param {string} url
 * @returns {string[]}
 */
export function candidatePaths(distDir, url) {
  const pathname = pathnameOf(url);
  if (pathname === null) return [];
  if (pathname.endsWith("/")) return [join(distDir, pathname, "index.html")];
  return [join(distDir, pathname), join(distDir, pathname, "index.html")];
}

/**
 * Check one leaf sitemap: it must list pages, and every URL it advertises must
 * have been emitted.
 *
 * The second half is the gate's real claim. Counting `<url>` elements only
 * proves the sitemap is non-empty — a route that failed to render, or a stale
 * entry, still counts. A crawler does not count entries; it fetches them, and
 * a sitemap full of 404s is worse than no sitemap.
 * @param {{ distDir: string, exists: (p: string) => boolean, read: (p: string) => string }} io
 * @param {string} label
 * @param {string} body
 * @param {string[]} failures
 * @param {string[]} notes
 */
function checkLeaf(io, label, body, failures, notes) {
  const count = [...body.matchAll(/<url>/g)].length;
  if (count === 0) {
    failures.push(`${label} lists zero URLs.`);
    return;
  }
  notes.push(`${label} lists ${count} URLs.`);

  const advertised = advertisedUrls(body);
  const malformed = advertised.filter((url) => pathnameOf(url) === null);
  if (malformed.length > 0) {
    failures.push(
      `${label} advertises ${malformed.length} URL(s) that are not absolute: ` +
        `${malformed.slice(0, 5).join(", ")}. Check that \`site\` is set in astro.config.mjs.`,
    );
  }

  const missing = advertised.filter(
    (url) => pathnameOf(url) !== null && !candidatePaths(io.distDir, url).some(io.exists),
  );
  if (missing.length > 0) {
    const shown = missing.slice(0, 5).join(", ");
    const rest = missing.length > 5 ? ` (and ${missing.length - 5} more)` : "";
    failures.push(
      `${label} advertises ${missing.length} URL(s) that were not emitted: ${shown}${rest}. ` +
        "A sitemap entry is a promise a crawler will follow.",
    );
  }
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
    const pathname = pathnameOf(url);
    if (pathname === null) {
      failures.push(`robots.txt advertises ${url}, which is not an absolute URL.`);
      continue;
    }
    const path = join(io.distDir, pathname);
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
    // A sitemap index points at further sitemaps; anything else is a leaf. Both
    // shapes get the same leaf treatment, so the single-sitemap case is not
    // silently skipped — an earlier version logged its page count only when an
    // index happened to sit above it, which is the common case here inverted.
    if (body.includes("<sitemapindex")) {
      for (const ref of refs) {
        const childPath = pathnameOf(ref);
        if (childPath === null) {
          failures.push(`${url} points at ${ref}, which is not an absolute URL.`);
          continue;
        }
        const child = join(io.distDir, childPath);
        if (!io.exists(child)) {
          failures.push(`${url} points at ${ref}, which was not emitted.`);
          continue;
        }
        checkLeaf(io, ref, io.read(child), failures, notes);
      }
    } else {
      checkLeaf(io, url, body, failures, notes);
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
