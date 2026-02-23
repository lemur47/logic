<script lang="ts">
  import type { PertStats } from "../../lib/pert";
  import { ui, type Lang } from "../../i18n/ui";

  interface Props {
    lang: Lang;
    stats: PertStats;
    variant: "textbook" | "adjusted";
    textbookExpected?: number;
  }

  let { lang, stats, variant, textbookExpected }: Props = $props();

  function t(key: string): string {
    return (ui[lang] as Record<string, string>)[key] ?? (ui.en as Record<string, string>)[key] ?? key;
  }

  function fmt(n: number): string {
    return n.toFixed(2);
  }

  function fmtRange(range: [number, number]): string {
    return `[${fmt(range[0])}, ${fmt(range[1])}]`;
  }

  const delta = $derived(
    variant === "adjusted" && textbookExpected != null
      ? stats.expected - textbookExpected
      : null,
  );

  const title = $derived(
    variant === "textbook" ? t("pert.calc.textbook") : t("pert.calc.adjusted"),
  );

  const unit = $derived(t("pert.calc.unit"));
</script>

<div
  class="rounded-lg border-2 p-5 {variant === 'adjusted' ? 'border-amber-300 bg-amber-50/50' : 'border-gray-200 bg-white'}"
>
  <div class="flex items-center justify-between mb-4">
    <h3 class="font-semibold text-lg">{title}</h3>
    {#if delta != null}
      <span class="text-xs font-medium text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
        +{fmt(delta)} {unit}
      </span>
    {/if}
  </div>

  <dl class="space-y-1.5">
    <div class="flex justify-between">
      <dt class="text-sm text-gray-600">{t("pert.calc.expected")}</dt>
      <dd class="text-sm font-medium">{fmt(stats.expected)} {unit}</dd>
    </div>
    <div class="flex justify-between">
      <dt class="text-sm text-gray-600">{t("pert.calc.stdDev")}</dt>
      <dd class="text-sm font-medium">{fmt(stats.stdDev)} {unit}</dd>
    </div>
    <div class="flex justify-between">
      <dt class="text-sm text-gray-600">{t("pert.calc.range68")}</dt>
      <dd class="text-sm font-medium">{fmtRange(stats.range68)}</dd>
    </div>
    <div class="flex justify-between">
      <dt class="text-sm text-gray-600">{t("pert.calc.range95")}</dt>
      <dd class="text-sm font-medium">{fmtRange(stats.range95)}</dd>
    </div>
    <div class="flex justify-between">
      <dt class="text-sm text-gray-600">{t("pert.calc.range99")}</dt>
      <dd class="text-sm font-medium">{fmtRange(stats.range99)}</dd>
    </div>
  </dl>
</div>
