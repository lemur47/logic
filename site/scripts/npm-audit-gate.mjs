#!/usr/bin/env node
/**
 * npm audit gate with a time-boxed allowlist.
 *
 * `npm audit` is a second, independent vulnerability gate alongside
 * osv-scanner, and it does not read osv-scanner.toml. Without this script the
 * only ways to get a green build past a deferred advisory are to raise
 * --audit-level (which weakens the gate for every future finding) or to run
 * `npm audit fix --force` (which is the very major upgrade we deferred).
 *
 * So: fail on anything at moderate or above, EXCEPT advisories explicitly
 * allowlisted below. Keep this list in step with osv-scanner.toml — same IDs,
 * same reasons, same review-by date. If they ever disagree, one of the two
 * gates is lying.
 *
 * Usage: npm audit --json --omit=dev | node scripts/npm-audit-gate.mjs
 */

/**
 * Advisories deliberately deferred. Every entry needs a reason and a
 * reviewBy — an allowlist without an expiry becomes permanent by accident.
 */
const ALLOWLIST = [
  {
    id: "GHSA-4g3v-8h47-v7g6",
    reason:
      "Astro 6.4.8 reflected XSS via View Transition animation properties. Fix requires Astro 7.1.0 (major upgrade of the live site). Unreachable: site uses no view transitions and imports no ClientRouter.",
    reviewBy: "2026-08-21",
  },
  {
    id: "GHSA-f48w-9m4c-m7f5",
    reason:
      "Astro 6.4.8 XSS via unescaped spread attribute names in renderHTMLElement. Fix requires Astro 7.0.6 (major upgrade of the live site). Unreachable: no spread attributes on elements in any .astro file.",
    reviewBy: "2026-08-21",
  },
  {
    id: "GHSA-7pw4-f3q4-r2p2",
    reason:
      "Astro 6.4.8 XSS via unescaped transition:* directive values. Fix requires Astro 7.0.4 (major upgrade of the live site). Unreachable: no transition:* directives anywhere in site/src.",
    reviewBy: "2026-08-21",
  },
];

const BLOCKING_SEVERITIES = new Set(["moderate", "high", "critical"]);
const ADVISORY_ID = /GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}/gi;

const allowed = new Map(ALLOWLIST.map((entry) => [entry.id.toUpperCase(), entry]));

/** Pull every advisory ID mentioned anywhere in a vulnerability's `via` chain. */
function advisoryIds(vulnerability) {
  const found = new Set();
  for (const via of vulnerability.via ?? []) {
    // `via` entries are either advisory objects or plain strings naming the
    // upstream package that caused this one. Strings carry no advisory of
    // their own — the causing package reports it, and is judged on its own row.
    if (typeof via !== "object") continue;
    for (const match of JSON.stringify(via).matchAll(ADVISORY_ID)) {
      found.add(match[0].toUpperCase());
    }
  }
  return found;
}

function main(raw) {
  let report;
  try {
    report = JSON.parse(raw);
  } catch (error) {
    console.error(`npm-audit-gate: could not parse npm audit JSON — ${error.message}`);
    process.exit(2);
  }

  const vulnerabilities = Object.values(report.vulnerabilities ?? {});
  const blocking = [];
  const waived = [];

  for (const vulnerability of vulnerabilities) {
    if (!BLOCKING_SEVERITIES.has(vulnerability.severity)) continue;

    const ids = advisoryIds(vulnerability);
    const unwaived = [...ids].filter((id) => !allowed.has(id));

    // No advisory IDs of its own means this package is only implicated through
    // a dependency, which is judged on its own row — don't double-report it.
    if (ids.size > 0 && unwaived.length === 0) {
      waived.push({ name: vulnerability.name, ids: [...ids] });
      continue;
    }
    if (unwaived.length > 0) {
      blocking.push({ name: vulnerability.name, severity: vulnerability.severity, ids: unwaived });
    }
  }

  const expired = ALLOWLIST.filter((entry) => entry.reviewBy < new Date().toISOString().slice(0, 10));
  for (const entry of expired) {
    console.error(
      `npm-audit-gate: allowlist entry ${entry.id} passed its review-by date (${entry.reviewBy}). ` +
        `Re-verify reachability and either fix or re-date it — do not extend it silently.`,
    );
  }

  for (const { name, ids } of waived) {
    console.log(`waived: ${name} (${ids.join(", ")}) — see scripts/npm-audit-gate.mjs`);
  }

  if (blocking.length > 0) {
    console.error("\nnpm-audit-gate: unwaived vulnerabilities at moderate or above:\n");
    for (const { name, severity, ids } of blocking) {
      console.error(`  ${name} [${severity}] ${ids.join(", ")}`);
    }
    console.error("\nFix them, or add a dated allowlist entry with a reachability justification.");
    process.exit(1);
  }

  if (expired.length > 0) process.exit(1);

  console.log(`npm-audit-gate: clean (${waived.length} waived, 0 blocking).`);
}

let stdin = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (stdin += chunk));
process.stdin.on("end", () => main(stdin));
