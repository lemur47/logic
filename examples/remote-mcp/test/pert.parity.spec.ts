/**
 * Parity suite: the TS port must match the Python module for identical inputs.
 *
 * Fixtures are generated from `app/pert/core.py` (see fixtures/pert-parity.json).
 * Numeric fields are compared with a ±0.005 tolerance on the 2-dp outputs, which
 * absorbs accumulated float noise. It does NOT absorb a rounding-mode
 * divergence: at 2 dp that is always exactly 0.01, twice the tolerance. The
 * rounding mode is pinned separately and at exact equality below, because a
 * tolerance comparison can only report on the ties the PERT cases happen to
 * reach — and for a year they reached none.
 */

import { describe, expect, it } from "vitest";
import { calculateTask } from "../src/pert";
import { roundHalfEven } from "../src/round";
import fixtures from "./fixtures/pert-parity.json";

const TOLERANCE = 0.005;

function expectClose(actual: number, expected: number, label: string): void {
  expect(Math.abs(actual - expected), `${label}: ${actual} vs ${expected}`).toBeLessThanOrEqual(
    TOLERANCE,
  );
}

describe("calculateTask parity with app/pert/core.py", () => {
  for (const { args, expected } of fixtures.cases) {
    it(`O=${args.optimistic} M=${args.most_likely} P=${args.pessimistic}`, () => {
      const result = calculateTask(args.optimistic, args.most_likely, args.pessimistic);

      expect(result.input).toEqual(expected.input);
      expect(result.adjusted).toBeNull();

      const t = result.textbook;
      const e = expected.textbook;
      expectClose(t.expected, e.expected, "expected");
      expectClose(t.std_dev, e.std_dev, "std_dev");
      expectClose(t.variance, e.variance, "variance");
      for (const range of ["range_68", "range_95", "range_99"] as const) {
        const [eLow, eHigh] = e[range] as [number, number];
        expectClose(t[range][0], eLow, `${range}[0]`);
        expectClose(t[range][1], eHigh, `${range}[1]`);
      }
    });
  }

  for (const { args, message } of fixtures.errors) {
    it(`rejects O=${args.optimistic} M=${args.most_likely} P=${args.pessimistic}`, () => {
      expect(() => calculateTask(args.optimistic, args.most_likely, args.pessimistic)).toThrow(
        message,
      );
    });
  }

  it("rejects non-finite inputs (no Python counterpart: JSON cannot carry NaN)", () => {
    expect(() => calculateTask(Number.NaN, 1, 2)).toThrow("finite");
    expect(() => calculateTask(1, Number.POSITIVE_INFINITY, 2)).toThrow("finite");
  });
});

describe("roundHalfEven — matches Python's round()", () => {
  /**
   * Exact equality, not tolerance. This is the control the PERT cases cannot
   * be: it asserts the rounding MODE rather than sampling whichever ties the
   * three-point inputs produce. Revert `round.ts` to a scale-then-compare
   * implementation and these cases go red immediately, which is the whole
   * point of pinning them.
   */
  for (const c of fixtures.rounding) {
    it(`round(${c.value}, ${c.dp}) === ${c.expected}`, () => {
      expect(roundHalfEven(c.value, c.dp)).toBe(c.expected);
    });
  }
});
