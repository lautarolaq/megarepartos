import { useAuthStore } from "@/stores/auth-store";
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

/**
 * REQ-FE-002: extrae access_token del hash, lo guarda en Zustand,
 * limpia la URL y redirige a /dashboard.
 */
export function AuthCallbackPage() {
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const navigate = useNavigate();

  useEffect(() => {
    const hash = window.location.hash.startsWith("#")
      ? window.location.hash.substring(1)
      : window.location.hash;
    const params = new URLSearchParams(hash);
    const token = params.get("access_token");
    if (token) {
      setAccessToken(token);
      // Limpiar la URL para que el token no quede visible.
      window.history.replaceState({}, "", "/dashboard");
      navigate("/dashboard", { replace: true });
    } else {
      navigate("/login", { replace: true });
    }
  }, [setAccessToken, navigate]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-600">
      <p>Iniciando sesión…</p>
    </main>
  );
}
