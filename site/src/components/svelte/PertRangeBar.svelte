<script lang="ts">
  import type { PertStats } from "../../lib/pert";
  import { ui, type Lang } from "../../i18n/ui";

  interface Props {
    lang: Lang;
    textbook: PertStats;
    adjusted: PertStats | null;
  }

  let { lang, textbook, adjusted }: Props = $props();

  function t(key: string): string {
    return (ui[lang] as Record<string, string>)[key] ?? (ui.en as Record<string, string>)[key] ?? key;
  }

  // Shared scale based on widest range (99.7%)
  const scale = $derived.by(() => {
    const min = Math.min(
      textbook.range99[0],
      adjusted?.range99[0] ?? textbook.range99[0],
    );
    const max = Math.max(
      textbook.range99[1],
      adjusted?.range99[1] ?? textbook.range99[1],
    );
    // Add 5% padding
    const pad = (max - min) * 0.05;
    return { min: min - pad, max: max + pad };
  });

  function toPercent(value: number): number {
    const range = scale.max - scale.min;
    if (range === 0) return 50;
    return ((value - scale.min) / range) * 100;
  }
</script>

<div class="rounded-lg border border-gray-200 bg-white p-5">
  <h3 class="text-sm font-semibold text-gray-700 mb-4">{t("pert.calc.rangeComparison")}</h3>

  <div class="space-y-4">
    <!-- Textbook bar -->
    <div>
      <div class="text-xs text-gray-500 mb-1">{t("pert.calc.textbook")}</div>
      <div class="relative h-6 bg-gray-100 rounded-full overflow-hidden">
        <!-- 99.7% range -->
        <div
          class="absolute top-0 h-full bg-blue-100 rounded-full"
          style="left: {toPercent(textbook.range99[0])}%; width: {toPercent(textbook.range99[1]) - toPercent(textbook.range99[0])}%;"
        ></div>
        <!-- 95% range -->
        <div
          class="absolute top-0.5 h-5 bg-blue-200 rounded-full"
          style="left: {toPercent(textbook.range95[0])}%; width: {toPercent(textbook.range95[1]) - toPercent(textbook.range95[0])}%;"
        ></div>
        <!-- 68% range -->
        <div
          class="absolute top-1 h-4 bg-blue-400 rounded-full"
          style="left: {toPercent(textbook.range68[0])}%; width: {toPercent(textbook.range68[1]) - toPercent(textbook.range68[0])}%;"
        ></div>
        <!-- Expected marker -->
        <div
          class="absolute top-0 h-full w-0.5 bg-blue-700"
          style="left: {toPercent(textbook.expected)}%;"
        ></div>
      </div>
    </div>

    <!-- Adjusted bar (only shown when adjusted exists) -->
    {#if adjusted}
      <div>
        <div class="text-xs text-gray-500 mb-1">{t("pert.calc.adjusted")}</div>
        <div class="relative h-6 bg-gray-100 rounded-full overflow-hidden">
          <!-- 99.7% range -->
          <div
            class="absolute top-0 h-full bg-amber-100 rounded-full"
            style="left: {toPercent(adjusted.range99[0])}%; width: {toPercent(adjusted.range99[1]) - toPercent(adjusted.range99[0])}%;"
          ></div>
          <!-- 95% range -->
          <div
            class="absolute top-0.5 h-5 bg-amber-200 rounded-full"
            style="left: {toPercent(adjusted.range95[0])}%; width: {toPercent(adjusted.range95[1]) - toPercent(adjusted.range95[0])}%;"
          ></div>
          <!-- 68% range -->
          <div
            class="absolute top-1 h-4 bg-amber-400 rounded-full"
            style="left: {toPercent(adjusted.range68[0])}%; width: {toPercent(adjusted.range68[1]) - toPercent(adjusted.range68[0])}%;"
          ></div>
          <!-- Expected marker -->
          <div
            class="absolute top-0 h-full w-0.5 bg-amber-700"
            style="left: {toPercent(adjusted.expected)}%;"
          ></div>
        </div>
      </div>
    {/if}
  </div>
</div>
