/**
 * Post-build gate: the promises in robots.txt must be true of dist/.
 *
 * This runs AFTER `astro build` rather than in `npm test`, because the thing it
 * checks only exists once the site is built — and CI runs `npm test` before
 * `npm run build`. A test that skipped when dist/ was absent would be worse than
 * no test: a gate that skips and a gate that passes read identically.
 *
 * What went wrong without it: robots.txt named
 * https://pmo.run/sitemap-index.xml as the single entry point we hand a
 * crawler, no sitemap integration was installed, and that URL returned 404 in
 * production for as long as anyone had been looking. Nothing failed, because
 * nothing was watching.
 *
 * Scope, stated honestly: this checks the file WE ship. It cannot see
 * Cloudflare's managed robots.txt, which is a zone setting that prepends its own
 * Disallow rules to the served file and overrides everything below. Only
 * fetching https://pmo.run/robots.txt shows what crawlers actually receive.
 */

import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const siteRoot = resolve(here, "..");
const dist = join(siteRoot, "dist");
const robotsPath = join(siteRoot, "public", "robots.txt");

const failures = [];
const robots = readFileSync(robotsPath, "utf8");

// 1. Every Sitemap: directive must resolve to a file we actually emitted.
const sitemapUrls = [...robots.matchAll(/^\s*Sitemap:\s*(\S+)\s*$/gim)].map((m) => m[1]);
if (sitemapUrls.length === 0) {
  failures.push("robots.txt declares no Sitemap: directive.");
}
for (const url of sitemapUrls) {
  const path = join(dist, new URL(url).pathname);
  if (!existsSync(path)) {
    failures.push(
      `robots.txt advertises ${url}, but ${path.replace(siteRoot + "/", "")} was not emitted. ` +
        "Either the sitemap integration is missing from astro.config.mjs, or the URL is wrong.",
    );
    continue;
  }
  const body = readFileSync(path, "utf8");
  const refs = [...body.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
  if (refs.length === 0) {
    failures.push(`${url} contains no <loc> entries.`);
  }
  // A sitemap index points at further sitemaps; follow one level.
  if (body.includes("<sitemapindex")) {
    for (const ref of refs) {
      const child = join(dist, new URL(ref).pathname);
      if (!existsSync(child)) {
        failures.push(`${url} points at ${ref}, which was not emitted.`);
      } else {
        const count = [...readFileSync(child, "utf8").matchAll(/<url>/g)].length;
        if (count === 0) failures.push(`${ref} lists zero URLs.`);
        else console.log(`[crawlability] ${ref} lists ${count} URLs.`);
      }
    }
  }
}

// 2. Our own file must not disallow the crawlers we have decided to admit.
//    (CEO decision, 2026-08-26 — AI systems may index, ground on and train from
//    this site. If that decision is ever reversed, change this list in the same
//    commit as robots.txt, so the reversal is deliberate rather than a typo.)
const ADMITTED = ["ClaudeBot", "GPTBot", "Google-Extended", "CCBot", "PerplexityBot"];
for (const bot of ADMITTED) {
  const group = new RegExp(`^\\s*User-agent:\\s*${bot}\\s*$([\\s\\S]*?)(?=^\\s*User-agent:|(?![\\s\\S]))`, "im");
  const m = robots.match(group);
  if (m && /^\s*Disallow:\s*\/\s*$/im.test(m[1])) {
    failures.push(`robots.txt disallows ${bot}, which the standing decision admits.`);
  }
}

if (failures.length > 0) {
  console.error("\n[crawlability] FAILED:\n" + failures.map((f) => `  - ${f}`).join("\n") + "\n");
  process.exit(1);
}
console.log("[crawlability] robots.txt promises hold against dist/.");
