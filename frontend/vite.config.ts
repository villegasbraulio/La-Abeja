import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
  },
  test: {
    environment: "jsdom",
    setupFiles: "./tests/setup.ts",
    globals: true,
    include: ["tests/unit/**/*.test.ts", "tests/integration/**/*.test.tsx"],
    exclude: ["tests/e2e/**"],
  },
});
