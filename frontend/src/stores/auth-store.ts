import { create } from "zustand";

/**
 * Auth store: access_token solo en memoria. El refresh token vive en cookie
 * HTTP-only del backend.
 *
 * `bootChecked` indica si ya intentamos recuperar la sesión vía
 * `bootRecoverSession`. Mientras es false mostramos splash en vez de
 * redirigir a /login (evita el flash de login si el user tiene cookie válida).
 */
interface AuthState {
  accessToken: string | null;
  bootChecked: boolean;
  setAccessToken: (token: string | null) => void;
  setBootChecked: (v: boolean) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  bootChecked: false,
  setAccessToken: (token) => set({ accessToken: token }),
  setBootChecked: (v) => set({ bootChecked: v }),
  clear: () => set({ accessToken: null }),
}));
