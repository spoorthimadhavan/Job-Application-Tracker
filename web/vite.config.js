import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, send /api calls to the Python server (uvicorn api.index:app --port 8000)
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
});
