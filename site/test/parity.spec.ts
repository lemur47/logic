/**
 * Parity net: the site's calculators against the Python core.
 *
 * `site/src/lib/pert.ts` and `tco.ts` reimplement maths that `app/*​/core.py`
 * owns. A visitor makes a decision on their output, so this is a product
 * surface — its maths is checked, not trusted.
 *
 * Fixtures are GENERATED from the Python core:
 *
 *     uv run python site/scripts/generate_parity_fixtures.py
 *
 * Never hand-edit `test/fixtures/parity.json`. A hand-written expectation
 * records what the TypeScript currently does, which is the thing under test.
 * If a case here fails, the default assumption is that the TypeScript has
 * drifted — regenerating to make it pass would silence the net.
 *
 * Imports from "vitest" explicitly rather than relying on globals, so no
 * tsconfig `types` entry is needed and `astro check` (which typechecks this
 * file during `npm run build`) resolves it without extra configuration.
 */

import { describe, expect, it } from "vitest";

import fixtures from "./fixtures/parity.json";
import {
  DEFAULT_TAGS,
  applyTags,
  calculatePert,
  combinedMultiplier,
  effectiveMultiplier,
  pertStats,
} from "../src/lib/pert";
import { roundHalfEven } from "../src/lib/round";
import { calculateTco } from "../src/lib/tco";

const TOL = fixtures.tolerance;

/** Compare a 2-dp value under the shared tolerance convention. */
function near(actual: number, expected: number, label: string) {
  expect(Math.abs(actual - expected), `${label}: got ${actual}, want ${expected}`).toBeLessThanOrEqual(
    TOL,
  );
}

function checkStats(actual: ReturnType<typeof pertStats>, expected: any, label: string) {
  near(actual.expected, expected.expected, `${label}.expected`);
  near(actual.stdDev, expected.std_dev, `${label}.std_dev`);
  near(actual.variance, expected.variance, `${label}.variance`);
  near(actual.range68[0], expected.range_68[0], `${label}.range_68[0]`);
  near(actual.range68[1], expected.range_68[1], `${label}.range_68[1]`);
  near(actual.range95[0], expected.range_95[0], `${label}.range_95[0]`);
  near(actual.range95[1], expected.range_95[1], `${label}.range_95[1]`);
  near(actual.range99[0], expected.range_99[0], `${label}.range_99[0]`);
  near(actual.range99[1], expected.range_99[1], `${label}.range_99[1]`);
}

describe("roundHalfEven — matches Python's round()", () => {
  /**
   * Checked directly, not only through the calculators. The site diverged here
   * on two counts: JS `Math.round` is half-away-from-zero where Python is
   * half-to-even, and scaling before rounding invents ties the double does not
   * have. Both produced wrong figures on a public calculator.
   */
  for (const c of fixtures.rounding as any[]) {
    it(`round(${c.value}, ${c.dp}) === ${c.expected}`, () => {
      expect(roundHalfEven(c.value, c.dp)).toBe(c.expected);
    });
  }
});

describe("tag catalogue", () => {
  /**
   * The highest-drift-risk duplication in the file. These multiplier ranges are
   * calibration judgement — the product's actual value — so a silent change
   * here alters what the site tells a visitor while every other test passes.
   */
  it("matches the Python catalogue exactly", () => {
    const actual = [...DEFAULT_TAGS]
      .map((t) => ({
        name: t.name,
        description: t.description,
        min_multiplier: t.minMultiplier,
        max_multiplier: t.maxMultiplier,
      }))
      .sort((a, b) => a.name.localeCompare(b.name));

    expect(actual).toEqual(fixtures.tag_catalogue);
  });

  it("defines every tag the core defines, and no extras", () => {
    const tsNames = DEFAULT_TAGS.map((t) => t.name).sort();
    const pyNames = fixtures.tag_catalogue.map((t: any) => t.name).sort();
    expect(tsNames).toEqual(pyNames);
  });
});

describe("pertStats — untagged", () => {
  for (const [i, c] of fixtures.pert.entries()) {
    const { optimistic, most_likely, pessimistic } = c.args as any;
    it(`case ${i}: (${optimistic}, ${most_likely}, ${pessimistic})`, () => {
      checkStats(pertStats(optimistic, most_likely, pessimistic), c.expected.textbook, "textbook");
    });
  }
});

describe("calculatePert with tags — adjusted stats and multipliers", () => {
  for (const [i, c] of fixtures.pert_tagged.entries()) {
    const args = c.args as any;
    it(`case ${i}: (${args.optimistic}, ${args.most_likely}, ${args.pessimistic})`, () => {
      const selections = args.tags.map((t: any) => {
        const tag = DEFAULT_TAGS.find((d) => d.name === t.name);
        if (!tag) throw new Error(`fixture references unknown tag ${t.name}`);
        return { tag, severity: t.severity, enabled: true };
      });

      const result = calculatePert(
        args.optimistic,
        args.most_likely,
        args.pessimistic,
        selections,
      );
      const expected = (c.expected as any).adjusted;

      expect(result.adjusted, "adjusted must be present when tags are applied").not.toBeNull();
      checkStats(result.adjusted as any, expected, "adjusted");
      // Same value, different name: Python calls it `pessimistic`, the TS port
      // calls it `adjustedP`. A naming difference, not a divergence — but the
      // net has to map it explicitly or it silently checks nothing.
      near(result.adjusted!.adjustedP, expected.pessimistic, "adjusted.pessimistic/adjustedP");

      // The multiplier fields are the ones that actually diverged: the core
      // rounds to 4 dp, and the TS helper rounded to 6.
      const applied = applyTags(args.pessimistic, selections);
      near(
        applied.combinedMultiplier,
        expected.combined_multiplier,
        "combined_multiplier",
      );
      expect(applied.tagsApplied.length).toBe(expected.tags_applied.length);
      applied.tagsApplied.forEach((t, j) => {
        expect(t.name).toBe(expected.tags_applied[j].name);
        near(t.multiplier, expected.tags_applied[j].multiplier, `tags_applied[${j}].multiplier`);
      });
    });
  }

  it("rounds multipliers to 4 dp, matching the core", () => {
    // Guards the specific defect: round2(x * 10000) / 10000 is 6 dp, because
    // round2 already multiplies by 100. An unrounded interpolation here would
    // carry full float precision.
    const tag = DEFAULT_TAGS.find((t) => t.name === "HIDDEN_DEPENDENCIES")!;
    const { tagsApplied, combinedMultiplier } = applyTags(10, [
      { tag, severity: 0.123, enabled: true },
    ]);

    const dp = (n: number) => (String(n).split(".")[1] ?? "").length;
    expect(dp(tagsApplied[0].multiplier)).toBeLessThanOrEqual(4);
    expect(dp(combinedMultiplier)).toBeLessThanOrEqual(4);
  });
});

describe("calculateTco", () => {
  for (const [i, c] of fixtures.tco.entries()) {
    const a = c.args as any;
    it(`case ${i}: initial=${a.initial_price} life=${a.useful_life_years}y`, () => {
      const actual = calculateTco({
        name: `case-${i}`,
        initialPrice: a.initial_price,
        usefulLifeYears: a.useful_life_years,
        residualValue: a.residual_value,
        annualMaintenance: a.annual_maintenance,
        annualOperatingCost: a.annual_operating_cost,
        discountRate: a.discount_rate,
      });
      const e = c.expected as any;

      near(actual.totalCost, e.total_cost, "total_cost");
      near(actual.annualCost, e.annual_cost, "annual_cost");
      near(actual.monthlyCost, e.monthly_cost, "monthly_cost");
      near(actual.costPerDay, e.cost_per_day, "cost_per_day");
      near(actual.npvTco, e.npv_tco, "npv_tco");
      near(actual.npvAnnual, e.npv_annual, "npv_annual");
    });
  }
});

describe("tag panel display — the numbers a visitor actually reads", () => {
  /**
   * The panel is a separate consumer of the same maths, and for a while it was
   * a separate IMPLEMENTATION of it: its own interpolation, its own rounding,
   * and a second rounding of the product. Every test above could pass while the
   * chip on the page showed a different figure from the one the core computes,
   * because nothing checked the chip.
   *
   * Exact equality, not the 2-dp tolerance: these are the displayed values, and
   * "within half a penny" is not a property a displayed multiplier has.
   */
  const tagByName = (name: string) => {
    const tag = DEFAULT_TAGS.find((t) => t.name === name);
    if (!tag) throw new Error(`fixture references unknown tag ${name}`);
    return tag;
  };

  it("shows each tag's multiplier at the core's own precision", () => {
    for (const c of fixtures.pert_display.multipliers) {
      expect(
        effectiveMultiplier(tagByName(c.tag), c.severity),
        `${c.tag} @ ${c.severity}`,
      ).toBe(c.expected);
    }
  });

  it("shows the combined multiplier the core computes", () => {
    for (const c of fixtures.pert_display.combined) {
      const selections = c.tags.map((t) => ({
        tag: tagByName(t.name),
        severity: t.severity,
        enabled: true,
      }));
      const label = c.tags.map((t) => `${t.name}@${t.severity}`).join(" + ");
      expect(combinedMultiplier(selections), label).toBe(c.expected);
    }
  });

  it("ignores tags the visitor has switched off", () => {
    const selections = [
      { tag: tagByName("MULTIPLE_STAKEHOLDERS"), severity: 0.5, enabled: true },
      { tag: tagByName("HIDDEN_DEPENDENCIES"), severity: 0.75, enabled: true },
      { tag: tagByName("FRAGMENTED_COMMUNICATION"), severity: 1.0, enabled: false },
    ];
    expect(combinedMultiplier(selections)).toBe(2.205);
  });
});

describe("fixture integrity", () => {
  it("covers every calculator the site exposes", () => {
    expect(fixtures.pert.length).toBeGreaterThan(0);
    expect(fixtures.pert_tagged.length).toBeGreaterThan(0);
    expect(fixtures.tco.length).toBeGreaterThan(0);
    expect(fixtures.tag_catalogue.length).toBeGreaterThan(0);
  });
});
