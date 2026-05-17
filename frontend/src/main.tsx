import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { bootRecoverSession } from "./lib/boot";
import "./index.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("No se encontró el elemento #root en index.html");
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

// Intentar recuperar sesión vía cookie de refresh al boot. No bloqueante:
// la app renderiza un splash hasta que bootChecked=true.
void bootRecoverSession();

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
