import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";

export default defineConfig([
  ...nextVitals,
  globalIgnores([
    ".next/**",
    ".next-*/**",
    "node_modules/**",
    "playwright-report/**",
    "test-results/**",
  ]),
]);
