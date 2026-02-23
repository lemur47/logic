// PERT estimation logic — port of app/pert/core.py (single-task only)

export interface InsightTag {
  name: string;
  description: string;
  minMultiplier: number;
  maxMultiplier: number;
}

export interface TagSelection {
  tag: InsightTag;
  severity: number;
  enabled: boolean;
}

export interface PertStats {
  expected: number;
  stdDev: number;
  variance: number;
  range68: [number, number];
  range95: [number, number];
  range99: [number, number];
}

export interface AdjustedStats extends PertStats {
  adjustedP: number;
  tagsApplied: { name: string; severity: number; multiplier: number }[];
  combinedMultiplier: number;
}

export interface PertResult {
  input: { optimistic: number; mostLikely: number; pessimistic: number };
  textbook: PertStats;
  adjusted: AdjustedStats | null;
}

// Predefined insight tags matching Python core
export const FRAGMENTED_COMMUNICATION: InsightTag = {
  name: "FRAGMENTED_COMMUNICATION",
  description: "Chat/meetings/manual workflows increase overhead",
  minMultiplier: 1.1,
  maxMultiplier: 1.5,
};

export const MULTIPLE_STAKEHOLDERS: InsightTag = {
  name: "MULTIPLE_STAKEHOLDERS",
  description: "Misaligned interests across orgs (strategic, political)",
  minMultiplier: 1.15,
  maxMultiplier: 2.0,
};

export const HIDDEN_DEPENDENCIES: InsightTag = {
  name: "HIDDEN_DEPENDENCIES",
  description: "Undocumented task relationships, upstream blockers",
  minMultiplier: 1.1,
  maxMultiplier: 1.5,
};

export const DEFAULT_TAGS: InsightTag[] = [
  FRAGMENTED_COMMUNICATION,
  MULTIPLE_STAKEHOLDERS,
  HIDDEN_DEPENDENCIES,
];

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

export function pertStats(o: number, m: number, p: number): PertStats {
  const expected = (o + 4 * m + p) / 6;
  const stdDev = (p - o) / 6;
  const variance = stdDev ** 2;
  return {
    expected: round2(expected),
    stdDev: round2(stdDev),
    variance: round2(variance),
    range68: [round2(expected - stdDev), round2(expected + stdDev)],
    range95: [round2(expected - 2 * stdDev), round2(expected + 2 * stdDev)],
    range99: [round2(expected - 3 * stdDev), round2(expected + 3 * stdDev)],
  };
}

export function applyTags(
  pessimistic: number,
  selections: TagSelection[],
): { adjustedP: number; tagsApplied: { name: string; severity: number; multiplier: number }[]; combinedMultiplier: number } {
  const tagsApplied: { name: string; severity: number; multiplier: number }[] = [];
  let combinedMultiplier = 1.0;

  for (const sel of selections) {
    if (!sel.enabled) continue;
    const effective = sel.tag.minMultiplier + sel.severity * (sel.tag.maxMultiplier - sel.tag.minMultiplier);
    combinedMultiplier *= effective;
    tagsApplied.push({
      name: sel.tag.name,
      severity: sel.severity,
      multiplier: round2(effective * 10000) / 10000,
    });
  }

  return {
    adjustedP: pessimistic * combinedMultiplier,
    tagsApplied,
    combinedMultiplier: round2(combinedMultiplier * 10000) / 10000,
  };
}

export function calculatePert(
  o: number,
  m: number,
  p: number,
  tagSelections?: TagSelection[],
): PertResult {
  const textbook = pertStats(o, m, p);

  let adjusted: AdjustedStats | null = null;
  const enabledTags = tagSelections?.filter((s) => s.enabled) ?? [];

  if (enabledTags.length > 0) {
    const { adjustedP, tagsApplied, combinedMultiplier } = applyTags(p, tagSelections!);
    const adjStats = pertStats(o, m, adjustedP);
    adjusted = {
      ...adjStats,
      adjustedP: round2(adjustedP),
      tagsApplied,
      combinedMultiplier,
    };
  }

  return {
    input: { optimistic: o, mostLikely: m, pessimistic: p },
    textbook,
    adjusted,
  };
}

export function createDefaultTagSelections(): TagSelection[] {
  return DEFAULT_TAGS.map((tag) => ({
    tag,
    severity: 0.5,
    enabled: false,
  }));
}

export function effectiveMultiplier(tag: InsightTag, severity: number): number {
  return round2((tag.minMultiplier + severity * (tag.maxMultiplier - tag.minMultiplier)) * 100) / 100;
}
