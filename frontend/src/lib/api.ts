import { useAuthStore } from "@/stores/auth-store";
import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  withCredentials: true, // necesario para que el browser mande la cookie mr_refresh
});

// REQ-FE-003: inyecta Authorization: Bearer en cada request si hay token.
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// REQ-FE-004: si 401 AUTH_INVALID, intenta refresh y reintenta una vez.
let refreshInFlight: Promise<string | null> | null = null;

async function tryRefresh(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    try {
      const resp = await axios.post(`${BASE_URL}/api/auth/refresh`, {}, { withCredentials: true });
      const token = resp.data?.access_token as string | undefined;
      if (token) {
        useAuthStore.getState().setAccessToken(token);
        return token;
      }
      return null;
    } catch {
      return null;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

api.interceptors.response.use(
  (resp) => resp,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & {
      _retried?: boolean;
    };
    const status = error.response?.status;
    const code = (error.response?.data as { error?: { code?: string } })?.error?.code;
    if (status === 401 && !original?._retried) {
      const newToken = await tryRefresh();
      if (newToken) {
        original._retried = true;
        original.headers.Authorization = `Bearer ${newToken}`;
        return api.request(original);
      }
      // Refresh falló → logout local. El caller redirige.
      useAuthStore.getState().clear();
      if (code === "AUTH_INVALID" || code === "AUTH_REQUIRED") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);
