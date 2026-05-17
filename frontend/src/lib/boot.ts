import { useAuthStore } from "@/stores/auth-store";
import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/**
 * Intenta recuperar sesión silenciosamente al boot de la app vía cookie de
 * refresh. Si tiene éxito, deja un access_token nuevo en Zustand.
 *
 * Se llama una sola vez desde main.tsx. Si la cookie no existe o está
 * expirada, el endpoint devuelve 401 y dejamos el state sin token (el user
 * verá /login).
 */
export async function bootRecoverSession(): Promise<void> {
  try {
    const resp = await axios.post(`${BASE_URL}/api/auth/refresh`, {}, { withCredentials: true });
    const token = resp.data?.access_token as string | undefined;
    if (token) {
      useAuthStore.getState().setAccessToken(token);
    }
  } catch {
    // 401 / network error: no hay sesión recuperable, queda como anonymous.
  } finally {
    useAuthStore.getState().setBootChecked(true);
  }
}
