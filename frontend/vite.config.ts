import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    // Vite resuelve `/src` desde la raíz del proyecto frontend, sin necesidad de
    // `path.resolve` ni `@types/node`.
    alias: {
      "@": "/src",
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    // Proxy /api/* al backend en :8000 — así una sola URL (la del túnel)
    // sirve tanto la página pública como las llamadas a la API.
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
    // Aceptar cualquier host — necesario para túneles (cloudflared, ngrok)
    // que generan subdominios efímeros. Solo aplica al dev server.
    allowedHosts: true,
  },
});
