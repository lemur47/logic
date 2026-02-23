<script lang="ts">
  import { type TagSelection, effectiveMultiplier } from "../../lib/pert";
  import { ui, type Lang } from "../../i18n/ui";

  interface Props {
    lang: Lang;
    selections: TagSelection[];
    onchange: (selections: TagSelection[]) => void;
  }

  let { lang, selections, onchange }: Props = $props();

  function t(key: string): string {
    return (ui[lang] as Record<string, string>)[key] ?? (ui.en as Record<string, string>)[key] ?? key;
  }

  const tagI18n: Record<string, { name: string; desc: string }> = $derived({
    FRAGMENTED_COMMUNICATION: {
      name: t("pert.calc.tag.fragmented"),
      desc: t("pert.calc.tag.fragmented.desc"),
    },
    MULTIPLE_STAKEHOLDERS: {
      name: t("pert.calc.tag.stakeholders"),
      desc: t("pert.calc.tag.stakeholders.desc"),
    },
    HIDDEN_DEPENDENCIES: {
      name: t("pert.calc.tag.dependencies"),
      desc: t("pert.calc.tag.dependencies.desc"),
    },
  });

  function toggleTag(index: number) {
    const updated = selections.map((s, i) =>
      i === index ? { ...s, enabled: !s.enabled } : s,
    );
    onchange(updated);
  }

  function updateSeverity(index: number, value: number) {
    const updated = selections.map((s, i) =>
      i === index ? { ...s, severity: value } : s,
    );
    onchange(updated);
  }

  const combinedMultiplier = $derived.by(() => {
    let combined = 1.0;
    for (const sel of selections) {
      if (sel.enabled) {
        combined *= effectiveMultiplier(sel.tag, sel.severity);
      }
    }
    return Math.round(combined * 100) / 100;
  });

  const enabledCount = $derived(selections.filter((s) => s.enabled).length);
</script>

<div class="rounded-lg border border-gray-200 bg-white p-5">
  <h3 class="text-sm font-semibold text-gray-700 mb-1">{t("pert.calc.insightTags")}</h3>
  <p class="text-xs text-gray-400 mb-4">{t("pert.calc.insightTags.desc")}</p>

  <div class="space-y-3">
    {#each selections as sel, i}
      {@const info = tagI18n[sel.tag.name]}
      {@const mult = effectiveMultiplier(sel.tag, sel.severity)}
      <div
        class="rounded-lg border p-3 transition-colors {sel.enabled ? 'border-accent bg-blue-50/30' : 'border-gray-200 bg-gray-50/50'}"
      >
        <div class="flex items-center justify-between">
          <button
            type="button"
            onclick={() => toggleTag(i)}
            class="flex items-center gap-2 text-sm font-medium {sel.enabled ? 'text-gray-900' : 'text-gray-400'}"
          >
            <span
              class="inline-flex items-center justify-center w-4 h-4 rounded border text-[10px] {sel.enabled ? 'border-accent bg-accent text-white' : 'border-gray-300 bg-white'}"
            >
              {#if sel.enabled}&#10003;{/if}
            </span>
            {info?.name ?? sel.tag.name}
          </button>
          {#if sel.enabled}
            <span class="text-xs font-mono font-medium text-accent">{mult.toFixed(2)}x</span>
          {/if}
        </div>

        <p class="text-xs text-gray-400 mt-1 ml-6">{info?.desc ?? sel.tag.description}</p>

        {#if sel.enabled}
          <div class="mt-3 ml-6">
            <div class="flex items-center gap-2">
              <span class="text-[10px] text-gray-400 w-8">{t("pert.calc.severity.mild")}</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={sel.severity}
                oninput={(e) => updateSeverity(i, parseFloat((e.target as HTMLInputElement).value))}
                class="flex-1 h-1.5 accent-accent"
              />
              <span class="text-[10px] text-gray-400 w-8 text-right">{t("pert.calc.severity.severe")}</span>
            </div>
          </div>
        {/if}
      </div>
    {/each}
  </div>

  {#if enabledCount >= 2}
    <div class="mt-3 pt-3 border-t border-gray-200 flex justify-between items-center">
      <span class="text-xs text-gray-500">{t("pert.calc.combinedMultiplier")}</span>
      <span class="text-sm font-mono font-semibold text-accent">{combinedMultiplier.toFixed(2)}x</span>
    </div>
  {/if}
</div>
