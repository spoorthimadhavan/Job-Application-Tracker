import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Self-contained demo: one JS file (IIFE), data bundled in, no server needed.
export default defineConfig({
  plugins: [react()],
  define: { "import.meta.env.VITE_DEMO": "true" },
  build: { outDir: "dist-demo", cssCodeSplit: false, modulePreload: false, rollupOptions: { output: { format: "iife", inlineDynamicImports: true, entryFileNames: "demo.js", assetFileNames: "demo.[ext]" } } },
});
