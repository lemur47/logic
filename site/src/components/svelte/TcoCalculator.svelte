<script lang="ts">
  import { calculateTco, createDefaultInput, type TcoInput, type TcoResult } from "../../lib/tco";
  import { ui, type Lang } from "../../i18n/ui";
  import TcoInputForm from "./TcoInputForm.svelte";
  import TcoResultsCard from "./TcoResultsCard.svelte";

  interface Props {
    lang: Lang;
  }

  let { lang }: Props = $props();

  function t(key: string): string {
    return (ui[lang] as Record<string, string>)[key] ?? (ui.en as Record<string, string>)[key] ?? key;
  }

  type Mode = "single" | "compare";

  let mode: Mode = $state("single");
  let inputs: TcoInput[] = $state([createDefaultInput(0, lang)]);
  let results: TcoResult[] | null = $state(null);

  function setMode(newMode: Mode) {
    mode = newMode;
    results = null;
    if (newMode === "compare" && inputs.length < 2) {
      inputs = [...inputs, createDefaultInput(1, lang)];
    } else if (newMode === "single") {
      inputs = [inputs[0]];
    }
  }

  function addOption() {
    if (inputs.length >= 4) return;
    inputs = [...inputs, createDefaultInput(inputs.length, lang)];
    results = null;
  }

  function removeOption(index: number) {
    if (inputs.length <= 2) return;
    inputs = inputs.filter((_, i) => i !== index);
    results = null;
  }

  function updateInput(index: number, updated: TcoInput) {
    inputs = inputs.map((inp, i) => (i === index ? updated : inp));
    results = null;
  }

  function calculate() {
    const valid = inputs.every(
      (inp) => inp.usefulLifeYears > 0 && inp.initialPrice >= 0
    );
    if (!valid) return;
    results = inputs.map((inp) => calculateTco(inp));
  }

  function reset() {
    inputs = mode === "single"
      ? [createDefaultInput(0, lang)]
      : [createDefaultInput(0, lang), createDefaultInput(1, lang)];
    results = null;
  }

  const bestIndex = $derived.by(() => {
    if (!results || results.length < 2) return -1;
    let minIdx = 0;
    for (let i = 1; i < results.length; i++) {
      if (results[i].annualCost < results[minIdx].annualCost) minIdx = i;
    }
    return minIdx;
  });
</script>

<div>
  <!-- Mode toggle -->
  <div class="flex items-center gap-1 bg-gray-100 rounded-lg p-1 w-fit mb-6">
    <button
      type="button"
      onclick={() => setMode("single")}
      class="px-4 py-1.5 text-sm font-medium rounded-md transition-colors {mode === 'single' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}"
    >
      {t("tco.calc.mode.single")}
    </button>
    <button
      type="button"
      onclick={() => setMode("compare")}
      class="px-4 py-1.5 text-sm font-medium rounded-md transition-colors {mode === 'compare' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}"
    >
      {t("tco.calc.mode.compare")}
    </button>
  </div>

  <!-- Input forms -->
  <div class={mode === "single" ? "max-w-xl" : "grid grid-cols-1 md:grid-cols-2 gap-4"}>
    {#each inputs as input, i}
      <TcoInputForm
        {lang}
        {input}
        index={i}
        showRemove={mode === "compare" && inputs.length > 2}
        onremove={() => removeOption(i)}
        onchange={(updated) => updateInput(i, updated)}
      />
    {/each}
  </div>

  <!-- Actions -->
  <div class="flex items-center gap-3 mt-6">
    <button
      type="button"
      onclick={calculate}
      class="px-6 py-2 bg-accent text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
    >
      {t("tco.calc.calculate")}
    </button>

    {#if mode === "compare" && inputs.length < 4}
      <button
        type="button"
        onclick={addOption}
        class="px-4 py-2 border border-gray-300 text-sm font-medium rounded-lg text-gray-600 hover:bg-gray-50 transition-colors"
      >
        {t("tco.calc.addOption")}
      </button>
    {/if}

    <button
      type="button"
      onclick={reset}
      class="px-4 py-2 text-sm text-gray-400 hover:text-gray-600 transition-colors"
    >
      {t("tco.calc.reset")}
    </button>
  </div>

  <!-- Results -->
  {#if results}
    <div class="mt-8">
      <div class={mode === "single" ? "max-w-xl" : "grid grid-cols-1 md:grid-cols-2 gap-4"}>
        {#each results as result, i}
          <TcoResultsCard
            {lang}
            {result}
            name={inputs[i].name}
            isBest={mode === "compare" && i === bestIndex}
          />
        {/each}
      </div>
    </div>
  {/if}
</div>
