import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api/orders": "http://localhost",
      "/api/inventory": "http://localhost",
      "/api/internal": "http://localhost",
      "/api/telemetry": "http://localhost"
    }
  }
});
