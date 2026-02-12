<script lang="ts">
  import type { TcoResult } from "../../lib/tco";
  import { formatCurrency } from "../../lib/format";
  import { ui, type Lang } from "../../i18n/ui";

  interface Props {
    lang: Lang;
    result: TcoResult;
    name: string;
    isBest: boolean;
  }

  let { lang, result, name, isBest }: Props = $props();

  function t(key: string): string {
    return (ui[lang] as Record<string, string>)[key] ?? (ui.en as Record<string, string>)[key] ?? key;
  }

  function fmt(value: number): string {
    return formatCurrency(value, lang);
  }
</script>

<div class="rounded-lg border-2 p-5 {isBest ? 'border-accent bg-blue-50/50' : 'border-gray-200 bg-white'}">
  <div class="flex items-center justify-between mb-4">
    <h3 class="font-semibold text-lg">{name}</h3>
    {#if isBest}
      <span class="text-xs font-medium text-accent bg-blue-100 px-2 py-0.5 rounded-full">
        {t("tco.calc.bestValue")}
      </span>
    {/if}
  </div>

  <div class="mb-4">
    <h4 class="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">
      {t("tco.calc.simpleTco")}
    </h4>
    <dl class="space-y-1.5">
      <div class="flex justify-between">
        <dt class="text-sm text-gray-600">{t("tco.calc.totalCost")}</dt>
        <dd class="text-sm font-medium">{fmt(result.totalCost)}</dd>
      </div>
      <div class="flex justify-between">
        <dt class="text-sm text-gray-600">{t("tco.calc.annualCost")}</dt>
        <dd class="text-sm font-medium">{fmt(result.annualCost)}</dd>
      </div>
      <div class="flex justify-between">
        <dt class="text-sm text-gray-600">{t("tco.calc.monthlyCost")}</dt>
        <dd class="text-sm font-medium">{fmt(result.monthlyCost)}</dd>
      </div>
      <div class="flex justify-between">
        <dt class="text-sm text-gray-600">{t("tco.calc.costPerDay")}</dt>
        <dd class="text-sm font-medium">{fmt(result.costPerDay)}</dd>
      </div>
    </dl>
  </div>

  <div>
    <h4 class="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">
      {t("tco.calc.npvAdjusted")}
    </h4>
    <dl class="space-y-1.5">
      <div class="flex justify-between">
        <dt class="text-sm text-gray-600">{t("tco.calc.npvTco")}</dt>
        <dd class="text-sm font-medium">{fmt(result.npvTco)}</dd>
      </div>
      <div class="flex justify-between">
        <dt class="text-sm text-gray-600">{t("tco.calc.npvAnnual")}</dt>
        <dd class="text-sm font-medium">{fmt(result.npvAnnual)}</dd>
      </div>
    </dl>
  </div>
</div>
