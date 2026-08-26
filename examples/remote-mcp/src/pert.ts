/**
 * PERT core calculation logic — TypeScript port of `app/pert/core.py` (textbook path only).
 *
 * Deliberately excludes the insight-tag adjustment path: this PoC ships the
 * unit-agnostic three-point estimate maths and nothing else. Parity with the
 * Python module is enforced by test/pert.parity.spec.ts against fixtures
 * generated from the Python implementation.
 */

import { round2 } from "./round";

export interface PertStats {
  expected: number;
  std_dev: number;
  variance: number;
  range_68: [number, number];
  range_95: [number, number];
  range_99: [number, number];
}

export interface TaskEstimation {
  input: {
    optimistic: number;
    most_likely: number;
    pessimistic: number;
  };
  textbook: PertStats;
  /** Always null in this PoC — the tag-adjustment path is not ported. */
  adjusted: null;
}

function pertStats(optimistic: number, mostLikely: number, pessimistic: number): PertStats {
  const expected = (optimistic + 4 * mostLikely + pessimistic) / 6;
  const stdDev = (pessimistic - optimistic) / 6;
  const variance = stdDev ** 2;

  return {
    expected: round2(expected),
    std_dev: round2(stdDev),
    variance: round2(variance),
    range_68: [round2(expected - stdDev), round2(expected + stdDev)],
    range_95: [round2(expected - 2 * stdDev), round2(expected + 2 * stdDev)],
    range_99: [round2(expected - 3 * stdDev), round2(expected + 3 * stdDev)],
  };
}

/**
 * Calculate the textbook PERT estimate for a single task.
 *
 * Mirrors `calculate_task(optimistic, most_likely, pessimistic, tags=None)`,
 * including the validation messages, so client-visible behaviour matches the
 * Python module.
 */
export function calculateTask(
  optimistic: number,
  mostLikely: number,
  pessimistic: number,
): TaskEstimation {
  for (const v of [optimistic, mostLikely, pessimistic]) {
    if (typeof v !== "number" || Number.isNaN(v) || !Number.isFinite(v)) {
      throw new RangeError("All estimates must be finite numbers");
    }
  }
  if (optimistic < 0 || mostLikely < 0 || pessimistic < 0) {
    throw new RangeError("All estimates must be non-negative");
  }
  if (optimistic > mostLikely) {
    throw new RangeError(`Optimistic (${optimistic}) cannot exceed most likely (${mostLikely})`);
  }
  if (mostLikely > pessimistic) {
    throw new RangeError(`Most likely (${mostLikely}) cannot exceed pessimistic (${pessimistic})`);
  }

  return {
    input: {
      optimistic,
      most_likely: mostLikely,
      pessimistic,
    },
    textbook: pertStats(optimistic, mostLikely, pessimistic),
    adjusted: null,
  };
}
