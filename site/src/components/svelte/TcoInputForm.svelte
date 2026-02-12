<script lang="ts">
  import type { TcoInput } from "../../lib/tco";
  import { ui, type Lang } from "../../i18n/ui";

  interface Props {
    lang: Lang;
    input: TcoInput;
    index: number;
    showRemove: boolean;
    onremove: () => void;
    onchange: (input: TcoInput) => void;
  }

  let { lang, input, index, showRemove, onremove, onchange }: Props = $props();

  function t(key: string): string {
    return (ui[lang] as Record<string, string>)[key] ?? (ui.en as Record<string, string>)[key] ?? key;
  }

  let errors: Record<string, string> = $state({});

  function validate(field: string, value: number): boolean {
    if (field === "usefulLifeYears") {
      if (value <= 0) {
        errors[field] = t("tco.calc.validation.positive");
        return false;
      }
    } else if (field === "discountRate") {
      // discount rate can be 0
      if (value < 0) {
        errors[field] = t("tco.calc.validation.nonNegative");
        return false;
      }
    } else {
      if (value < 0) {
        errors[field] = t("tco.calc.validation.nonNegative");
        return false;
      }
    }
    delete errors[field];
    errors = errors; // trigger reactivity
    return true;
  }

  function handleFieldChange(field: keyof TcoInput, raw: string) {
    if (field === "name") {
      onchange({ ...input, name: raw });
      return;
    }

    const num = raw === "" ? 0 : parseFloat(raw);
    if (isNaN(num)) return;

    const value = field === "discountRate" ? num / 100 : num;
    validate(field, value);
    onchange({ ...input, [field]: value });
  }

  function displayValue(field: keyof TcoInput): string {
    const v = input[field] as number;
    if (field === "discountRate") return String(Math.round(v * 10000) / 100);
    return v === 0 ? "" : String(v);
  }

  const currency = $derived(t("tco.calc.currency"));

  const monetaryFields: (keyof TcoInput)[] = [
    "initialPrice",
    "residualValue",
    "annualMaintenance",
    "annualOperatingCost",
  ];

  interface FieldDef {
    key: keyof TcoInput;
    label: string;
    prefix: string;
    suffix: string;
  }

  const fields: FieldDef[] = $derived([
    { key: "initialPrice", label: t("tco.calc.initialPrice"), prefix: currency, suffix: "" },
    { key: "usefulLifeYears", label: t("tco.calc.usefulLife"), prefix: "", suffix: "" },
    { key: "residualValue", label: t("tco.calc.residualValue"), prefix: currency, suffix: "" },
    { key: "annualMaintenance", label: t("tco.calc.annualMaintenance"), prefix: currency, suffix: "" },
    { key: "annualOperatingCost", label: t("tco.calc.annualOperating"), prefix: currency, suffix: "" },
    { key: "discountRate", label: t("tco.calc.discountRate"), prefix: "", suffix: "" },
  ]);
</script>

<div class="rounded-lg border border-gray-200 bg-white p-5">
  <div class="flex items-center justify-between mb-4">
    <input
      type="text"
      value={input.name}
      oninput={(e) => handleFieldChange("name", (e.target as HTMLInputElement).value)}
      class="text-lg font-semibold bg-transparent border-b border-transparent hover:border-gray-300 focus:border-accent focus:outline-none px-1 py-0.5 w-full max-w-[200px]"
    />
    {#if showRemove}
      <button
        type="button"
        onclick={onremove}
        class="text-sm text-gray-400 hover:text-red-500 transition-colors ml-2"
      >
        {t("tco.calc.remove")}
      </button>
    {/if}
  </div>

  <div class="grid grid-cols-2 gap-3">
    {#each fields as field}
      <div>
        <label class="block text-xs text-gray-500 mb-1">{field.label}</label>
        <div class="relative">
          {#if field.prefix}
            <span class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm pointer-events-none">
              {field.prefix}
            </span>
          {/if}
          <input
            type="number"
            value={displayValue(field.key)}
            oninput={(e) => handleFieldChange(field.key, (e.target as HTMLInputElement).value)}
            step="any"
            min="0"
            class="w-full border rounded-md py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent {errors[field.key] ? 'border-red-400' : 'border-gray-300'} {field.prefix ? 'pl-7' : 'pl-2.5'} pr-2.5"
          />
        </div>
        {#if errors[field.key]}
          <p class="text-xs text-red-500 mt-0.5">{errors[field.key]}</p>
        {/if}
      </div>
    {/each}
  </div>
</div>
