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
// Currently empty. The three Astro 6.4.8 XSS advisories that lived here
// (GHSA-4g3v-8h47-v7g6, GHSA-f48w-9m4c-m7f5, GHSA-7pw4-f3q4-r2p2) each
// required Astro 6 -> 7 to fix. That upgrade has landed, so they are deleted
// rather than left to expire on their review-by date.
const ALLOWLIST = [];

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

/**
 * Decide the verdict from a parsed report. Pure: no printing, no exit.
 *
 * Split out so the decision can be unit-tested the way the crawlability gate's
 * parsing is. The process contract — what gets printed and which exit code —
 * stays in `main` below.
 */
export function evaluate(report) {
  // Refuse before counting. `npm audit` answers a registry failure with a
  // well-formed JSON document carrying a top-level `error` and no
  // `vulnerabilities`, so the old `?? {}` fallback counted zero and printed a
  // clean verdict — a gate reporting success for a scan that never happened.
  //
  // Absent is not empty, and the difference is load-bearing: a genuinely clean
  // audit emits `"vulnerabilities": {}`, the key present. Verified against the
  // real command, not assumed.
  //
  // These throw rather than returning a flag. A returned `invalid` field can be
  // dropped by a caller that forgets to read it, which is this defect's own
  // failure mode one level up; an uncaught throw exits non-zero.
  if (report === null || typeof report !== "object" || Array.isArray(report)) {
    throw new Error("npm-audit-gate: expected an audit report object, got something else.");
  }
  if (report.error) {
    const summary = report.error.summary ?? report.error.code ?? "no detail given";
    throw new Error(
      `npm-audit-gate: the audit did not run — npm reported an error (${summary}). ` +
        "This is not a clean result; re-run once the registry is reachable.",
    );
  }
  if (!Object.hasOwn(report, "vulnerabilities")) {
    throw new Error(
      "npm-audit-gate: the report carries no `vulnerabilities` key. A clean audit " +
        "reports it present and empty, so its absence means the audit did not " +
        "produce a result — it does not mean there is nothing to find.",
    );
  }

  const blocking = [];
  const waived = [];
  const vulnerabilities = Object.values(report.vulnerabilities);

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

  return { blocking, waived, expired };
}

function main(raw) {
  let report;
  try {
    report = JSON.parse(raw);
  } catch (error) {
    console.error(`npm-audit-gate: could not parse npm audit JSON — ${error.message}`);
    process.exit(2);
  }

  let verdict;
  try {
    verdict = evaluate(report);
  } catch (error) {
    console.error(error.message);
    process.exit(2);
  }
  const { blocking, waived, expired } = verdict;

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

// Only read stdin when run as a command. Imported by a test, this module must
// expose `evaluate` without hanging on a stdin that will never close.
if (process.argv[1] && import.meta.url === `file://${process.argv[1]}`) {
  let stdin = "";
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk) => (stdin += chunk));
  process.stdin.on("end", () => main(stdin));
}
