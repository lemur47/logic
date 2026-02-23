<script lang="ts">
  import { ui, type Lang } from "../../i18n/ui";

  interface Props {
    lang: Lang;
    optimistic: number;
    mostLikely: number;
    pessimistic: number;
    onchange: (o: number, m: number, p: number) => void;
  }

  let { lang, optimistic, mostLikely, pessimistic, onchange }: Props = $props();

  function t(key: string): string {
    return (ui[lang] as Record<string, string>)[key] ?? (ui.en as Record<string, string>)[key] ?? key;
  }

  let errors: Record<string, string> = $state({});

  function validate(o: number, m: number, p: number): boolean {
    let valid = true;
    const newErrors: Record<string, string> = {};

    if (o < 0) { newErrors.optimistic = t("pert.calc.validation.nonNegative"); valid = false; }
    if (m < 0) { newErrors.mostLikely = t("pert.calc.validation.nonNegative"); valid = false; }
    if (p < 0) { newErrors.pessimistic = t("pert.calc.validation.nonNegative"); valid = false; }

    if (valid && (o > m || m > p)) {
      newErrors.order = t("pert.calc.validation.order");
      valid = false;
    }

    errors = newErrors;
    return valid;
  }

  function handleChange(field: "optimistic" | "mostLikely" | "pessimistic", raw: string) {
    const num = raw === "" ? 0 : parseFloat(raw);
    if (isNaN(num)) return;

    const o = field === "optimistic" ? num : optimistic;
    const m = field === "mostLikely" ? num : mostLikely;
    const p = field === "pessimistic" ? num : pessimistic;

    validate(o, m, p);
    onchange(o, m, p);
  }

  function displayValue(v: number): string {
    return v === 0 ? "" : String(v);
  }

  const unit = $derived(t("pert.calc.unit"));

  const fields = $derived([
    { key: "optimistic" as const, label: t("pert.calc.optimistic"), value: optimistic },
    { key: "mostLikely" as const, label: t("pert.calc.mostLikely"), value: mostLikely },
    { key: "pessimistic" as const, label: t("pert.calc.pessimistic"), value: pessimistic },
  ]);
</script>

<div class="rounded-lg border border-gray-200 bg-white p-5">
  <div class="space-y-3">
    {#each fields as field}
      <div>
        <label class="block text-xs text-gray-500 mb-1">{field.label}</label>
        <div class="relative">
          <input
            type="number"
            value={displayValue(field.value)}
            oninput={(e) => handleChange(field.key, (e.target as HTMLInputElement).value)}
            step="any"
            min="0"
            class="w-full border rounded-md py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent pl-2.5 pr-12 {errors[field.key] ? 'border-red-400' : 'border-gray-300'}"
          />
          <span class="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm pointer-events-none">
            {unit}
          </span>
        </div>
        {#if errors[field.key]}
          <p class="text-xs text-red-500 mt-0.5">{errors[field.key]}</p>
        {/if}
      </div>
    {/each}
    {#if errors.order}
      <p class="text-xs text-red-500">{errors.order}</p>
    {/if}
  </div>
</div>
