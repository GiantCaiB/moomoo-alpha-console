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
          DEFAULT: "#080b12",
          card: "#111620",
          elevated: "#151b26",
          hover: "#1a2230",
          border: "#ffffff14",
          borderStrong: "#ffffff24",
        },
        accent: {
          green: "#34d399",
          red: "#f87171",
          blue: "#60a5fa",
          amber: "#fbbf24",
          purple: "#a78bfa",
          cyan: "#22d3ee",
        },
        text: {
          primary: "#e5e7eb",
          secondary: "#9ca3af",
          muted: "#6b7280",
          disabled: "#4b5563",
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
        glass: "0 12px 40px rgba(0, 0, 0, 0.28)",
        glow: "0 0 0 1px rgba(52, 211, 153, 0.18), 0 0 20px rgba(52, 211, 153, 0.08)",
        "glow-red": "0 0 0 1px rgba(248, 113, 113, 0.18), 0 0 20px rgba(248, 113, 113, 0.08)",
        "glow-amber": "0 0 0 1px rgba(251, 191, 36, 0.18), 0 0 20px rgba(251, 191, 36, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
