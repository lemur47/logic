import { round2 } from "./round";

export interface TcoInput {
  name: string;
  initialPrice: number;
  usefulLifeYears: number;
  residualValue: number;
  annualMaintenance: number;
  annualOperatingCost: number;
  discountRate: number;
}

export interface TcoResult {
  totalCost: number;
  annualCost: number;
  monthlyCost: number;
  costPerDay: number;
  npvTco: number;
  npvAnnual: number;
}


export function calculateTco(input: TcoInput): TcoResult {
  const {
    initialPrice,
    usefulLifeYears,
    residualValue,
    annualMaintenance,
    annualOperatingCost,
    discountRate,
  } = input;

  // Simple TCO (no discounting)
  const totalOperational =
    (annualMaintenance + annualOperatingCost) * usefulLifeYears;
  const totalCost = initialPrice + totalOperational - residualValue;
  const annualCost = totalCost / usefulLifeYears;
  const monthlyCost = annualCost / 12;

  // NPV-adjusted TCO (time value of money)
  let npvOperational = 0;
  for (let year = 1; year <= usefulLifeYears; year++) {
    npvOperational +=
      (annualMaintenance + annualOperatingCost) / (1 + discountRate) ** year;
  }
  const npvResidual = residualValue / (1 + discountRate) ** usefulLifeYears;
  const npvTco = initialPrice + npvOperational - npvResidual;
  const npvAnnual = npvTco / usefulLifeYears;

  return {
    totalCost: round2(totalCost),
    annualCost: round2(annualCost),
    monthlyCost: round2(monthlyCost),
    costPerDay: round2(annualCost / 365),
    npvTco: round2(npvTco),
    npvAnnual: round2(npvAnnual),
  };
}

export function createDefaultInput(index: number, lang: string): TcoInput {
  const defaultNames: Record<string, string[]> = {
    en: ["Option A", "Option B", "Option C", "Option D"],
    ja: ["選択肢A", "選択肢B", "選択肢C", "選択肢D"],
  };
  const names = defaultNames[lang] ?? defaultNames.en;
  return {
    name: names[index] ?? `Option ${index + 1}`,
    initialPrice: 0,
    usefulLifeYears: 1,
    residualValue: 0,
    annualMaintenance: 0,
    annualOperatingCost: 0,
    discountRate: 0.03,
  };
}
