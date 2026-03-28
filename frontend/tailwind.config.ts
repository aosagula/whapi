import type { Config } from "tailwindcss"

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      // Paleta del prototipo Whapi
      colors: {
        cream: "#fdf6ee",
        brand: {
          DEFAULT: "#e85d04",
          light: "#fb923c",
          pale: "#fff0e6",
        },
        brown: {
          DEFAULT: "#1c1208",
          mid: "#6b3f1a",
          muted: "#9c7c6b",
        },
        border: "#e8d5c4",
      },
      fontFamily: {
        serif: ["DM Serif Display", "Georgia", "serif"],
        sans: ["DM Sans", "system-ui", "sans-serif"],
      },
      backgroundImage: {
        "hero-warm": "linear-gradient(160deg, #fff8f0 0%, #ffe8d2 100%)",
      },
    },
  },
  plugins: [],
}

export default config
