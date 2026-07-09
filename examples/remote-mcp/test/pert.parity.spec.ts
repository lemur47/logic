/**
 * Parity suite: the TS port must match the Python module for identical inputs.
 *
 * Fixtures are generated from `app/pert/core.py` (see fixtures/pert-parity.json).
 * Numeric fields are compared with a ±0.005 tolerance on the 2-dp outputs:
 * Python round() is banker's rounding, toFixed is half-away-from-zero, and the
 * two differ only on exact decimal ties.
 */

import { describe, expect, it } from "vitest";
import { calculateTask } from "../src/pert";
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
