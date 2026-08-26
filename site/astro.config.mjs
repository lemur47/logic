import { defineConfig } from "astro/config";
import svelte from "@astrojs/svelte";
import sitemap from "@astrojs/sitemap";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  site: "https://pmo.run",
  output: "static",
  i18n: {
    locales: ["en", "ja"],
    defaultLocale: "en",
    routing: {
      prefixDefaultLocale: true,
      redirectToDefaultLocale: true,
    },
  },
  integrations: [
    svelte(),
    // The sitemap is not decoration. robots.txt names
    // https://pmo.run/sitemap-index.xml as the one entry point we give a
    // crawler, and until this integration existed that URL returned 404 — so
    // every one of the 51 EN/JA routes was reachable only by link-following.
    // `i18n` makes the emitted entries carry hreflang alternates, which is what
    // tells a crawler /en/blog/x and /ja/blog/x are one document in two
    // languages rather than duplicates of unclear precedence.
    sitemap({
      // `/` is a 302 stub to `/en/` (see public/_redirects), not a document.
      // Listing a redirect in a sitemap is a soft error, and here it also
      // emitted a second hreflang="en" alternate pointing at a different URL
      // from the real English home page.
      filter: (page) => page !== "https://pmo.run/",
      i18n: {
        defaultLocale: "en",
        locales: { en: "en", ja: "ja" },
      },
    }),
  ],
  vite: {
    plugins: [tailwindcss()],
  },
});
