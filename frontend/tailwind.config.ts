import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#0f1117",
          card: "#1a1d28",
          hover: "#252836",
          border: "#2d3140",
        },
        accent: {
          green: "#00c853",
          red: "#ff1744",
          blue: "#2979ff",
          amber: "#ffab00",
          purple: "#7c4dff",
        },
        text: {
          primary: "#e8eaed",
          secondary: "#9aa0a6",
          muted: "#5f6368",
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      backdropBlur: {
        glass: "12px",
      },
      boxShadow: {
        neon: "0 0 10px rgba(0, 200, 83, 0.15)",
        "neon-red": "0 0 10px rgba(255, 23, 68, 0.15)",
      },
    },
  },
  plugins: [],
};

export default config;
