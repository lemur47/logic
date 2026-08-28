/**
 * Unit tests for the npm audit gate's verdict.
 *
 * The gate counted `report.vulnerabilities ?? {}`, so a report that carried no
 * vulnerability key at all counted zero and printed a clean verdict. `npm
 * audit` emits exactly that shape when it cannot reach the registry: a
 * well-formed JSON document with a top-level `error` object and no
 * `vulnerabilities`. A network failure therefore read as "no vulnerabilities",
 * which is the same class as a scanner reporting `0 commits scanned … no leaks
 * detected`.
 *
 * A genuinely clean audit is distinguishable — it emits `"vulnerabilities": {}`,
 * the key present and empty, verified against the real command rather than
 * assumed. Absent is not empty, and only one of the two is evidence.
 *
 * Pure report-in / verdict-out, so these run in `npm test` without a network.
 */

import { describe, expect, it } from "vitest";

import { evaluate } from "../scripts/npm-audit-gate.mjs";

/** What `npm audit --json` returns when the registry is unreachable. */
const REGISTRY_ERROR = {
  error: {
    code: "ENOTFOUND",
    summary: "request to https://registry.npmjs.org/-/npm/v1/security/advisories/bulk failed",
    detail: "This is a problem related to network connectivity.",
  },
};

/** A real clean audit: the key is present and empty. */
const CLEAN = { auditReportVersion: 2, vulnerabilities: {}, metadata: {} };

const WITH_MODERATE = {
  auditReportVersion: 2,
  vulnerabilities: {
    "some-package": {
      name: "some-package",
      severity: "moderate",
      via: [{ title: "something", url: "https://github.com/advisories/GHSA-aaaa-bbbb-cccc" }],
    },
  },
  metadata: {},
};

describe("evaluate", () => {
  it("refuses a report whose audit did not run", () => {
    expect(() => evaluate(REGISTRY_ERROR)).toThrow(/error/i);
  });

  it("refuses a report with no vulnerabilities key at all", () => {
    // Absent is not empty. This is the shape the old fallback silently read as
    // a clean bill of health.
    expect(() => evaluate({ auditReportVersion: 2, metadata: {} })).toThrow(/vulnerabilities/i);
  });

  it("refuses anything that is not an object", () => {
    expect(() => evaluate(null)).toThrow();
    expect(() => evaluate([])).toThrow();
  });

  it("accepts a genuinely clean audit", () => {
    const { blocking, waived } = evaluate(CLEAN);
    expect(blocking).toHaveLength(0);
    expect(waived).toHaveLength(0);
  });

  it("still blocks an unwaived advisory at moderate or above", () => {
    const { blocking } = evaluate(WITH_MODERATE);
    expect(blocking).toHaveLength(1);
    expect(blocking[0].ids).toContain("GHSA-AAAA-BBBB-CCCC");
  });

  it("still ignores severities below moderate", () => {
    const low = {
      vulnerabilities: { p: { name: "p", severity: "low", via: [{ url: "GHSA-dddd-eeee-ffff" }] } },
    };
    expect(evaluate(low).blocking).toHaveLength(0);
  });
});
