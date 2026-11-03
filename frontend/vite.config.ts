import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: loadEnv(mode, '.', '').MOVI_API_TARGET || "http://127.0.0.1:8000", changeOrigin: false } },
  },
  test: { environment: "jsdom", setupFiles: "./src/test-setup.ts" },
}));
