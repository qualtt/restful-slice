import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#14290a",
        panel: "#0f1f08",
        accent: "#a3ff12"
      },
      boxShadow: {
        panel: "0 10px 30px rgba(2, 6, 23, 0.5)"
      }
    }
  },
  darkMode: "class",
  plugins: []
} satisfies Config;
