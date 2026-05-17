import { useAuthStore } from "@/stores/auth-store";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

/**
 * REQ-FE-002: extrae access_token del hash, lo guarda en Zustand,
 * y redirige a /dashboard.
 *
 * Lee el hash con `useState(() => ...)` para que el valor quede congelado
 * desde el primer render, evitando que StrictMode (dev double-effect) o un
 * navigate previo lo pierda. Sin esto, el segundo run del efecto leía un
 * hash vacío y mandaba al usuario a /login después de un login exitoso.
 */
export function AuthCallbackPage() {
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const navigate = useNavigate();

  const [hashToken] = useState<string | null>(() => {
    const rawHash = window.location.hash.startsWith("#")
      ? window.location.hash.substring(1)
      : window.location.hash;
    const params = new URLSearchParams(rawHash);
    return params.get("access_token");
  });

  useEffect(() => {
    if (hashToken) {
      setAccessToken(hashToken);
      navigate("/dashboard", { replace: true });
    } else {
      navigate("/login", { replace: true });
    }
  }, [hashToken, setAccessToken, navigate]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-600">
      <p>Iniciando sesión…</p>
    </main>
  );
}
