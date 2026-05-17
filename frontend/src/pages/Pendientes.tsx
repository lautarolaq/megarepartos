import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { Clock, Send } from "lucide-react";
import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";

interface Pendiente {
  cliente_id: string;
  cliente_nombre: string;
  cliente_telefono: string;
  fecha_link: string;
}

interface PendientesResp {
  items: Pendiente[];
  total: number;
}

type FiltroDias = "1" | "3" | "7" | "30";

function formatearFecha(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("es-AR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function PendientesPage() {
  const [dias, setDias] = useState<FiltroDias>("7");

  const { data, isLoading, error } = useQuery({
    queryKey: ["pendientes", dias],
    queryFn: async (): Promise<PendientesResp> =>
      (await api.get(`/api/pedidos/pendientes?desde_dias=${dias}`)).data,
    refetchInterval: 60_000,
  });

  return (
    <div>
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Pendientes</h2>
        <p className="mt-1 text-sm text-slate-500">
          Clientes que recibieron el link y todavía no respondieron.
        </p>
      </div>

      <div className="mt-4 inline-flex overflow-hidden rounded-md border border-slate-200 bg-white text-sm">
        {(["1", "3", "7", "30"] as FiltroDias[]).map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => setDias(v)}
            className={`px-3 py-1.5 transition-colors ${
              dias === v ? "bg-sky-600 text-white" : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            {v === "1" ? "Hoy" : `${v} días`}
          </button>
        ))}
      </div>

      {isLoading && <p className="mt-6 text-slate-500">Cargando…</p>}
      {error && <p className="mt-6 text-rose-600">Error al cargar pendientes.</p>}

      {data && data.items.length === 0 && (
        <div className="mt-8 rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
          <Clock className="mx-auto mb-2 text-slate-400" size={28} />
          <p>Sin pendientes en este rango.</p>
          <p className="mt-1 text-xs text-slate-400">
            Todos los clientes a los que mandaste link ya respondieron.
          </p>
        </div>
      )}

      {data && data.items.length > 0 && (
        <>
          <p className="mt-4 text-xs text-slate-500">
            {data.total} pendiente{data.total === 1 ? "" : "s"}
          </p>
          <ul className="mt-2 flex flex-col gap-2">
            {data.items.map((p) => {
              const telDigits = p.cliente_telefono.replace(/\D/g, "");
              const waUrl = `https://wa.me/${telDigits}`;
              return (
                <li
                  key={p.cliente_id}
                  className="flex items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 shadow-sm"
                >
                  <div className="min-w-0">
                    <RouterLink
                      to={`/dashboard/clientes/${p.cliente_id}`}
                      className="truncate font-semibold text-slate-800 hover:text-sky-600 hover:underline"
                    >
                      {p.cliente_nombre}
                    </RouterLink>
                    <p className="text-xs text-slate-500">{p.cliente_telefono}</p>
                    <p className="mt-1 text-xs text-amber-700">
                      Link enviado: {formatearFecha(p.fecha_link)}
                    </p>
                  </div>
                  <a
                    href={waUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700"
                  >
                    <Send size={12} />
                    WhatsApp
                  </a>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}
