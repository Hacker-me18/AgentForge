/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Warm-organic neutrals: unbleached paper -> sand -> clay. No cool greys.
        canvas: "rgb(245 240 235 / <alpha-value>)", // page background (paper)
        panel: "rgb(250 247 241 / <alpha-value>)", // cards / top bar / drawer (warm white)
        raised: "rgb(239 231 220 / <alpha-value>)", // hover fills / chip wells (light sand)
        edge: "rgb(222 204 181 / <alpha-value>)", // clay hairline
        edgehi: "rgb(201 180 154 / <alpha-value>)", // stronger clay lines
        ink: "rgb(45 42 36 / <alpha-value>)", // deep warm brown (#2D2A24)
        fg: "rgb(74 67 58 / <alpha-value>)", // primary body text
        sub: "rgb(110 100 87 / <alpha-value>)", // secondary text
        faint: "rgb(148 137 121 / <alpha-value>)", // tertiary meta text
        // The only two accents: terracotta (CTA / attention) + olive (calm / tags).
        brand: "rgb(200 106 74 / <alpha-value>)", // terracotta
        brandhi: "rgb(172 84 55 / <alpha-value>)", // terracotta hover / pressed
        brandtint: "rgb(243 229 220 / <alpha-value>)", // terracotta tint well
        olive: "rgb(122 139 94 / <alpha-value>)",
        olivehi: "rgb(100 117 74 / <alpha-value>)",
        rust: "rgb(150 58 38 / <alpha-value>)", // failure / destructive (deep terracotta)
        clay: "rgb(212 191 165 / <alpha-value>)",
        sand: "rgb(232 222 209 / <alpha-value>)",
      },
      fontFamily: {
        sans: ['"Instrument Sans Variable"', "system-ui", "Segoe UI", "sans-serif"],
        serif: ['"Fraunces Variable"', "Georgia", "ui-serif", "serif"],
        mono: ['"JetBrains Mono Variable"', "ui-monospace", "SFMono-Regular", "Consolas", "monospace"],
      },
      boxShadow: {
        // Warm shadows (brown-tinted, never cool grey or black).
        panel: "0 1px 2px rgb(45 42 36 / 0.05)",
        card: "0 4px 20px -4px rgb(45 42 36 / 0.10)",
        lifted: "0 8px 30px -6px rgb(45 42 36 / 0.12)",
      },
    },
  },
  plugins: [],
};
