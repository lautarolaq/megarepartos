import { create } from "zustand";

/**
 * Auth store: solo guarda el access_token en memoria.
 * El refresh token está en cookie HTTP-only (no accesible desde JS).
 */
interface AuthState {
  accessToken: string | null;
  setAccessToken: (token: string | null) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  setAccessToken: (token) => set({ accessToken: token }),
  clear: () => set({ accessToken: null }),
}));
