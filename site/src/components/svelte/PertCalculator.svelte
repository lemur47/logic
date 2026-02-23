<script lang="ts">
  import {
    calculatePert,
    createDefaultTagSelections,
    type TagSelection,
    type PertResult,
  } from "../../lib/pert";
  import { ui, type Lang } from "../../i18n/ui";
  import PertInputForm from "./PertInputForm.svelte";
  import PertInsightTags from "./PertInsightTags.svelte";
  import PertResultsCard from "./PertResultsCard.svelte";
  import PertRangeBar from "./PertRangeBar.svelte";

  interface Props {
    lang: Lang;
  }

  let { lang }: Props = $props();

  function t(key: string): string {
    return (ui[lang] as Record<string, string>)[key] ?? (ui.en as Record<string, string>)[key] ?? key;
  }

  let optimistic = $state(0);
  let mostLikely = $state(0);
  let pessimistic = $state(0);
  let tagSelections: TagSelection[] = $state(createDefaultTagSelections());
  let result: PertResult | null = $state(null);

  function handleInputChange(o: number, m: number, p: number) {
    optimistic = o;
    mostLikely = m;
    pessimistic = p;
    // Don't auto-recalculate on input change — requires explicit Calculate click
  }

  function handleTagChange(selections: TagSelection[]) {
    tagSelections = selections;
    // Auto-update results when tags change (if already calculated)
    if (result) {
      recalculate();
    }
  }

  function isValid(): boolean {
    return optimistic >= 0 && mostLikely >= 0 && pessimistic >= 0
      && optimistic <= mostLikely && mostLikely <= pessimistic
      && (optimistic > 0 || mostLikely > 0 || pessimistic > 0);
  }

  function recalculate() {
    if (!isValid()) return;
    result = calculatePert(optimistic, mostLikely, pessimistic, tagSelections);
  }

  function calculate() {
    if (!isValid()) return;
    result = calculatePert(optimistic, mostLikely, pessimistic, tagSelections);
  }

  function reset() {
    optimistic = 0;
    mostLikely = 0;
    pessimistic = 0;
    tagSelections = createDefaultTagSelections();
    result = null;
  }
</script>

<div>
  <!-- Input row: form + tags side by side on desktop -->
  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <PertInputForm
      {lang}
      {optimistic}
      {mostLikely}
      {pessimistic}
      onchange={handleInputChange}
    />
    <PertInsightTags
      {lang}
      selections={tagSelections}
      onchange={handleTagChange}
    />
  </div>

  <!-- Actions -->
  <div class="flex items-center gap-3 mt-6">
    <button
      type="button"
      onclick={calculate}
      class="px-6 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors"
    >
      {t("pert.calc.calculate")}
    </button>
    <button
      type="button"
      onclick={reset}
      class="px-4 py-2 text-sm text-gray-400 hover:text-gray-600 transition-colors"
    >
      {t("pert.calc.reset")}
    </button>
  </div>

  <!-- Results -->
  {#if result}
    <div class="mt-8">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <PertResultsCard
          {lang}
          stats={result.textbook}
          variant="textbook"
        />
        {#if result.adjusted}
          <PertResultsCard
            {lang}
            stats={result.adjusted}
            variant="adjusted"
            textbookExpected={result.textbook.expected}
          />
        {/if}
      </div>

      <!-- Range comparison bar -->
      <div class="mt-4">
        <PertRangeBar
          {lang}
          textbook={result.textbook}
          adjusted={result.adjusted}
        />
      </div>
    </div>
  {/if}
</div>
