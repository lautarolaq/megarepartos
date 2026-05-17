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
    host: true,
    port: 5173,
    strictPort: true,
  },
});
