import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api and /health to the FastAPI backend during development so the
// frontend can call them on the same origin (no CORS juggling in the browser).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
