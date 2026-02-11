<script lang="ts">
  interface Props {
    lang: "en" | "ja";
  }

  let { lang }: Props = $props();

  const label = lang === "ja" ? "TCO計算ツール（準備中）" : "TCO Calculator (coming soon)";
</script>

<div class="border rounded p-8 text-center text-gray-400">
  {label}
</div>
