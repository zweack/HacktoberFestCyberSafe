import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// dev.sh sets API_PORT so a second checkout on other ports proxies to its own API.
const backend = `http://127.0.0.1:${process.env.API_PORT ?? "8000"}`;

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": backend, "/healthz": backend, "/readyz": backend, "/metrics": backend },
  },
});
