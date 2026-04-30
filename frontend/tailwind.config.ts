import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        burgundy: {
          50: "#fdf2f3",
          100: "#fce7e9",
          200: "#f8c9cd",
          300: "#f4a0a7",
          400: "#ec6a76",
          500: "#e04553",
          600: "#cc2a39",
          700: "#ab1f2d",
          800: "#8f1e2a",
          900: "#722F37",
          950: "#420d15"
        },
        gold: {
          300: "#e8d5a3",
          400: "#d9c07a",
          500: "#C8A96E",
          600: "#b08a4a",
          700: "#8f6e35"
        },
        cream: {
          50: "#FAF7F2",
          100: "#f5efe4",
          200: "#ead9c4"
        },
        charcoal: {
          900: "#1f1b18"
        }
      },
      fontFamily: {
        serif: ["Playfair Display", "Georgia", "serif"],
        sans: ["Manrope", "system-ui", "sans-serif"]
      },
      boxShadow: {
        velvet: "0 24px 80px rgba(66, 13, 21, 0.16)"
      },
      backgroundImage: {
        "hero-radial":
          "radial-gradient(circle at top left, rgba(200, 169, 110, 0.24), transparent 40%), radial-gradient(circle at bottom right, rgba(114, 47, 55, 0.22), transparent 48%)"
      }
    }
  },
  plugins: []
} satisfies Config;
