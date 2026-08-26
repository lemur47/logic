/**
 * Rounding that matches Python's, for the calculator ported from `app/pert/core.py`.
 *
 * Python's built-in `round()` uses **round-half-to-even** (banker's rounding);
 * JavaScript's `Math.round` rounds half **away from zero**. They disagree
 * whenever a value lands exactly on a halfway point:
 *
 *     0.625 -> Python 0.62,  Math.round(62.5)/100 = 0.63
 *    -7.195 -> Python -7.2,  Math.round(-719.5)/100 = -7.19
 *
 * That is a genuine output difference on a surface someone estimates from, not
 * a rounding nicety — so the port has to match the mode, not just the decimal
 * places.
 *
 * This file is a copy of `site/src/lib/round.ts`, which is where the
 * implementation was first got right. Keep the two in step: the parity fixtures
 * check each copy against the Python core, not against each other.
 */

/**
 * Round `value` to `dp` decimal places using round-half-to-even.
 *
 * Works from the double's exact decimal expansion rather than by scaling.
 * Scaling first (`value * 100`) manufactures ties that the original value does
 * not have, and Python does not round those to even:
 *
 *     51.585 * 100 === 5158.5 exactly       -> looks like a tie
 *     (51.585).toFixed(20) = "51.58500000000000085265"
 *                                           -> actually ABOVE the midpoint
 *     Python round(51.585, 2) = 51.59       -> rounds up, no tie involved
 *
 * whereas 0.625 is exactly representable, so it IS a tie and Python gives 0.62.
 * Expanding to `dp + 20` digits exposes the difference; a double carries about
 * 17 significant digits, so anything beyond that is fully determined.
 */
export function roundHalfEven(value: number, dp: number): number {
  if (!Number.isFinite(value)) return value;

  const negative = value < 0;
  const digits = Math.abs(value).toFixed(Math.min(dp + 20, 100));
  const [intPart, frac = ""] = digits.split(".");

  const kept = frac.slice(0, dp).padEnd(dp, "0");
  const rest = frac.slice(dp);

  // BigInt keeps the integer part exact for large values.
  let scaled = BigInt(intPart + kept);

  // charAt rather than rest[0]: it yields "" for an empty remainder, which
  // compares below "5", so the "nothing left to round" case needs no separate
  // guard and the expression typechecks under noUncheckedIndexedAccess.
  const isTie = /^50*$/.test(rest);
  const roundUp = isTie ? scaled % 2n !== 0n : rest.charAt(0) >= "5";
  if (roundUp) scaled += 1n;

  const result = Number(scaled) / 10 ** dp;
  return negative ? -result : result;
}

/** Round to 2 dp — the presentation precision used across the calculators. */
export function round2(value: number): number {
  return roundHalfEven(value, 2);
}

/** Round to 4 dp — the precision `app/pert/core.py` uses for multipliers. */
export function round4(value: number): number {
  return roundHalfEven(value, 4);
}
