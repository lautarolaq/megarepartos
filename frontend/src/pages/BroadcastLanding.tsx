// Landing genérica para un broadcast de WhatsApp.
//
// Flujo: el sodero manda UN solo link a una Broadcast List ("/b/{token}").
// El cliente cae acá, tipea su teléfono, el backend lo identifica contra el
// padrón y devuelve un token personal de corta duración. Redirigimos al flujo
// existente "/c/{cliente_token}" para reusar PublicoLink.tsx.
//
// Optimización UX: si el teléfono fue confirmado antes, lo guardamos en
// localStorage y la próxima vez auto-completamos (y auto-enviamos si la
// página se abre desde el mismo broadcast).

import { useMutation } from "@tanstack/react-query";
import axios, { type AxiosError } from "axios";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const STORAGE_KEY = "mr_broadcast_phone";

interface IdentificarOut {
  cliente_token: string;
  info: {
    cliente: { nombre_completo: string };
  };
}

export function BroadcastLandingPage() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const [telefono, setTelefono] = useState(() => localStorage.getItem(STORAGE_KEY) ?? "");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const identificar = useMutation({
    mutationFn: async (phone: string) => {
      const resp = await axios.post<IdentificarOut>(
        `${API_BASE}/api/publico/b/${token}/identificar`,
        { telefono: phone },
      );
      return resp.data;
    },
    onSuccess: (data, phone) => {
      localStorage.setItem(STORAGE_KEY, phone);
      navigate(`/c/${data.cliente_token}`, { replace: true });
    },
    onError: (err) => {
      const ax = err as AxiosError<{ error?: { message?: string } }>;
      const apiMsg = ax.response?.data?.error?.message;
      setErrorMsg(apiMsg ?? "No pudimos identificar tu número. Probá de nuevo.");
    },
  });

  // Auto-intentar si tenemos teléfono guardado de antes (solo una vez por mount).
  const triedAutoRef = useRef(false);
  useEffect(() => {
    if (triedAutoRef.current) return;
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      triedAutoRef.current = true;
      identificar.mutate(saved);
    }
  }, [identificar]);

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrorMsg(null);
    const trimmed = telefono.trim();
    if (!trimmed) {
      setErrorMsg("Ingresá tu teléfono.");
      return;
    }
    identificar.mutate(trimmed);
  }

  if (!token) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-rose-50 px-4 text-rose-800">
        <p>Link inválido.</p>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center bg-sky-50 px-4 py-10 text-slate-800">
      <div className="w-full max-w-md">
        <h1 className="text-2xl font-semibold leading-tight">¡Hola!</h1>
        <p className="mt-3 text-base text-slate-600">
          Para confirmar tu pedido, ingresá el teléfono que tenés registrado con la sodería.
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="telefono" className="block text-sm font-medium text-slate-700">
              Tu teléfono
            </label>
            <input
              id="telefono"
              type="tel"
              autoComplete="tel"
              inputMode="tel"
              value={telefono}
              onChange={(e) => {
                setTelefono(e.target.value);
                setErrorMsg(null);
              }}
              placeholder="351 770 7209"
              disabled={identificar.isPending}
              className="mt-1 w-full rounded-md border border-slate-300 bg-white px-4 py-3 text-base focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            />
            <p className="mt-1 text-xs text-slate-500">
              Con o sin código de área, con o sin "15", como te quede cómodo.
            </p>
          </div>

          {errorMsg && (
            <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {errorMsg}
            </div>
          )}

          <button
            type="submit"
            disabled={identificar.isPending}
            className="w-full rounded-xl bg-emerald-600 px-6 py-4 text-lg font-semibold text-white shadow-md transition-colors hover:bg-emerald-700 active:bg-emerald-800 disabled:opacity-60"
          >
            {identificar.isPending ? "Buscando…" : "Continuar"}
          </button>
        </form>

        <p className="mt-8 text-xs text-slate-400">
          Si no encontramos tu número, escribíle a la sodería para que te dé de alta.
        </p>
      </div>
    </main>
  );
}
