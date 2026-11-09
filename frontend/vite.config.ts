/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://localhost:8000" } },
  build: { target: "es2020", sourcemap: false, chunkSizeWarningLimit: 200 },
  test: { environment: "jsdom", setupFiles: ["./src/test-setup.ts"], globals: true, css: false },
});
