import { useMutation, useQuery } from "@tanstack/react-query";
import axios from "axios";
import { useState } from "react";
import { useParams } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

interface LinkPublico {
  empresa: { nombre: string };
  cliente: { nombre_completo: string; telefono: string };
}

type Estado = "pregunta" | "confirmado" | "rechazado";

/**
 * Página pública (sin auth) que ve el cliente al abrir un link de WhatsApp.
 * Mobile-first: viewport 375px base, botones grandes (>=60x60px), sin nav.
 */
export function PublicoLinkPage() {
  const { token } = useParams<{ token: string }>();
  const [estado, setEstado] = useState<Estado>("pregunta");

  const { data, isLoading, error } = useQuery({
    queryKey: ["publico", token],
    queryFn: async (): Promise<LinkPublico> => {
      const resp = await axios.get<LinkPublico>(`${API_BASE}/api/publico/c/${token}`);
      return resp.data;
    },
    enabled: !!token,
    retry: false,
  });

  const responder = useMutation({
    mutationFn: async (accion: "confirmo" | "rechazo") =>
      axios.post(`${API_BASE}/api/publico/c/${token}/respuesta`, { accion, datos: {} }),
    onSuccess: (_resp, accion) => {
      setEstado(accion === "confirmo" ? "confirmado" : "rechazado");
    },
  });

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-sky-50 px-4 text-slate-600">
        <p>Cargando…</p>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-rose-50 px-4 text-rose-800">
        <div className="text-center">
          <h1 className="text-xl font-semibold">Link no válido</h1>
          <p className="mt-2 text-sm text-rose-600">
            Este link expiró o no es correcto. Pedile uno nuevo a tu sodería.
          </p>
        </div>
      </main>
    );
  }

  const primerNombre = data.cliente.nombre_completo.split(" ")[0];

  if (estado === "confirmado") {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-emerald-50 px-4 py-8 text-emerald-900">
        <div className="max-w-md text-center">
          <div className="mb-4 text-5xl">✓</div>
          <h1 className="text-2xl font-semibold">¡Listo, {primerNombre}!</h1>
          <p className="mt-3 text-base text-emerald-700">Mañana pasamos con tu pedido.</p>
          <p className="mt-8 text-sm text-emerald-600">{data.empresa.nombre}</p>
        </div>
      </main>
    );
  }

  if (estado === "rechazado") {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-slate-100 px-4 py-8 text-slate-700">
        <div className="max-w-md text-center">
          <div className="mb-4 text-5xl">👍</div>
          <h1 className="text-2xl font-semibold">Entendido, {primerNombre}.</h1>
          <p className="mt-3 text-base text-slate-600">
            No pasamos esta semana. Te avisamos la próxima.
          </p>
          <p className="mt-8 text-sm text-slate-500">{data.empresa.nombre}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-sky-50 px-4 py-8 text-slate-800">
      <div className="w-full max-w-md">
        <p className="text-sm uppercase tracking-wider text-sky-700">{data.empresa.nombre}</p>
        <h1 className="mt-2 text-3xl font-semibold leading-tight">¡Hola, {primerNombre}!</h1>
        <p className="mt-4 text-base text-slate-600">
          Mañana pasamos por tu zona. ¿Te llevamos tu pedido?
        </p>

        <div className="mt-8 flex flex-col gap-3">
          <button
            type="button"
            disabled={responder.isPending}
            onClick={() => responder.mutate("confirmo")}
            className="rounded-xl bg-emerald-600 px-6 py-5 text-lg font-semibold text-white shadow-md transition-colors hover:bg-emerald-700 active:bg-emerald-800 disabled:opacity-60"
          >
            ✓ Sí, pasen mañana
          </button>
          <button
            type="button"
            disabled={responder.isPending}
            onClick={() => responder.mutate("rechazo")}
            className="rounded-xl border-2 border-slate-300 bg-white px-6 py-5 text-lg font-semibold text-slate-700 shadow-sm transition-colors hover:bg-slate-50 active:bg-slate-100 disabled:opacity-60"
          >
            ✗ Esta semana no
          </button>
        </div>

        <p className="mt-12 text-xs text-slate-400">{data.cliente.telefono}</p>
      </div>
    </main>
  );
}
