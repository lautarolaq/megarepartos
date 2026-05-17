import { api } from "@/lib/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function fetchGoogleLoginUrl(): Promise<string> {
  const resp = await api.get<{ url: string }>("/api/auth/google/url");
  return resp.data.url;
}

export function startGoogleLogin(): void {
  // Redirige el browser entero al server, que devolverá la URL de Google.
  // En vez de fetchGoogleLoginUrl + redirect, vamos directo al endpoint que
  // devuelve un objeto con la URL — usamos fetch porque queremos seguir el
  // link en el browser.
  fetchGoogleLoginUrl()
    .then((url) => {
      window.location.href = url;
    })
    .catch(() => {
      alert(
        "No se pudo obtener la URL de login con Google. Verificá que el backend esté corriendo.",
      );
    });
}

export function fullApiUrl(path: string): string {
  return `${API_BASE}${path}`;
}
