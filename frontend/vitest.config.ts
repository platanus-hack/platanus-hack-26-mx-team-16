import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["e2e/**", "node_modules/**", ".next/**"],
  },
  resolve: {
    tsconfigPaths: true,
    alias: {
      // Belt-and-braces for `@/src/...` imports — tsconfigPaths covers
      // most of it but the explicit alias keeps things deterministic.
      "@": path.resolve(__dirname, "."),
    },
  },
});
