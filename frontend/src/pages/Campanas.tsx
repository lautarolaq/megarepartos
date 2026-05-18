// Listado de campañas + detalle.
//
// Una campaña agrupa todas las respuestas de un envío en lote (broadcast o
// bulk individual). Permite al sodero filtrar "confirmados de la difusión
// zona norte miércoles" como bloque coherente, separado de otras campañas.

import { EmptyState } from "@/components/ui/EmptyState";
import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { Megaphone, Send } from "lucide-react";
import { Link as RouterLink, useParams } from "react-router-dom";

interface CampanaResumen {
  id: string;
  nombre: string;
  tipo_envio: string;
  zona_id: string | null;
  zona_nombre: string | null;
  mensaje: string;
  fecha_creacion: string;
  n_confirmados: number;
  n_rechazados: number;
}

interface CampanaListResp {
  items: CampanaResumen[];
}

interface RespuestaCampana {
  cliente_id: string;
  cliente_nombre: string;
  cliente_telefono: string;
  accion: "confirmo" | "rechazo" | string;
  fecha: string;
  productos: Array<{
    producto_id: string;
    nombre: string;
    cantidad_llenos: number;
    cantidad_vacios: number;
    es_retornable: boolean;
  }>;
}

interface CampanaDetalle extends CampanaResumen {
  respuestas: RespuestaCampana[];
}

function formatFecha(iso: string): string {
  try {
    return new Date(iso).toLocaleString("es-AR", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function CampanasPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["campanas"],
    queryFn: async (): Promise<CampanaListResp> => (await api.get("/api/campanas")).data,
  });

  return (
    <div>
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold tracking-tight">Campañas</h2>
      </div>
      <p className="mt-1 text-xs text-slate-500">
        Cada campaña agrupa las respuestas de un envío. Las creás desde Clientes → Campaña.
      </p>

      {isLoading && <p className="mt-4 text-slate-500">Cargando…</p>}

      {data && data.items.length === 0 && (
        <EmptyState
          icon={<Megaphone size={20} />}
          title="Todavía no enviaste ninguna campaña."
          body="Andá a Clientes → Campaña, generá un envío y vas a ver acá las confirmaciones."
        />
      )}

      {data && data.items.length > 0 && (
        <ul className="mt-4 flex flex-col gap-2">
          {data.items.map((c) => (
            <li
              key={c.id}
              className="rounded-md border border-slate-200 bg-white px-4 py-3 shadow-sm"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <RouterLink
                    to={`/dashboard/campanas/${c.id}`}
                    className="text-base font-medium text-slate-800 hover:text-sky-600 hover:underline"
                  >
                    {c.nombre}
                  </RouterLink>
                  <p className="text-xs text-slate-500">
                    {formatFecha(c.fecha_creacion)} ·{" "}
                    {c.tipo_envio === "broadcast" ? "Broadcast" : "Individual"}
                    {c.zona_nombre && <> · {c.zona_nombre}</>}
                  </p>
                </div>
                <div className="flex items-baseline gap-3 text-sm">
                  <span className="rounded bg-emerald-50 px-2 py-0.5 font-medium text-emerald-700">
                    ✓ {c.n_confirmados}
                  </span>
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-slate-600">
                    ✗ {c.n_rechazados}
                  </span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function CampanaDetallePage() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading } = useQuery({
    queryKey: ["campana", id],
    queryFn: async (): Promise<CampanaDetalle> => (await api.get(`/api/campanas/${id}`)).data,
    enabled: !!id,
  });

  if (isLoading) {
    return <p className="text-slate-500">Cargando…</p>;
  }
  if (!data) {
    return <p className="text-slate-500">Campaña no encontrada.</p>;
  }

  const confirmados = data.respuestas.filter((r) => r.accion === "confirmo");
  const rechazados = data.respuestas.filter((r) => r.accion === "rechazo");

  return (
    <div>
      <RouterLink
        to="/dashboard/campanas"
        className="text-xs text-slate-500 hover:text-sky-600 hover:underline"
      >
        ← Volver a campañas
      </RouterLink>
      <div className="mt-2 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">{data.nombre}</h2>
          <p className="mt-1 text-xs text-slate-500">
            {formatFecha(data.fecha_creacion)} ·{" "}
            {data.tipo_envio === "broadcast" ? "Broadcast" : "Individual"}
            {data.zona_nombre && <> · {data.zona_nombre}</>}
          </p>
        </div>
        <div className="flex items-baseline gap-3 text-sm">
          <span className="rounded bg-emerald-50 px-2 py-0.5 font-medium text-emerald-700">
            ✓ {confirmados.length}
          </span>
          <span className="rounded bg-slate-100 px-2 py-0.5 text-slate-600">
            ✗ {rechazados.length}
          </span>
        </div>
      </div>

      {data.mensaje && (
        <div className="mt-4 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
          <p className="text-xs font-medium text-slate-500">Mensaje enviado:</p>
          <pre className="mt-1 whitespace-pre-wrap break-words text-xs text-slate-800">
            {data.mensaje}
          </pre>
        </div>
      )}

      <h3 className="mt-6 text-base font-semibold">Confirmaciones ({confirmados.length})</h3>
      {confirmados.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500">Todavía nadie confirmó esta campaña.</p>
      ) : (
        <ul className="mt-2 flex flex-col gap-2">
          {confirmados.map((r) => (
            <li
              key={`${r.cliente_id}-${r.fecha}`}
              className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-slate-800">{r.cliente_nombre}</p>
                  <p className="text-xs text-slate-500">
                    {r.cliente_telefono} · {formatFecha(r.fecha)}
                  </p>
                </div>
                <a
                  href={`https://wa.me/${r.cliente_telefono.replace(/\D/g, "")}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-emerald-700 hover:underline"
                >
                  <Send size={12} className="inline" /> chat
                </a>
              </div>
              {r.productos.length > 0 && (
                <ul className="mt-2 ml-1 text-xs text-slate-700">
                  {r.productos.map((p) => (
                    <li key={p.producto_id}>
                      • {p.cantidad_llenos} × {p.nombre}
                      {p.es_retornable && p.cantidad_vacios > 0 && (
                        <> (devuelve {p.cantidad_vacios} vacíos)</>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )}

      {rechazados.length > 0 && (
        <>
          <h3 className="mt-6 text-base font-semibold">Rechazos ({rechazados.length})</h3>
          <ul className="mt-2 flex flex-col gap-2">
            {rechazados.map((r) => (
              <li
                key={`${r.cliente_id}-${r.fecha}`}
                className="rounded-md border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600"
              >
                {r.cliente_nombre} · {r.cliente_telefono} · {formatFecha(r.fecha)}
              </li>
            ))}
          </ul>
        </>
      )}

      <div className="mt-8">
        <RouterLink to="/dashboard/campanas" className="text-sm text-sky-600 hover:underline">
          ← Volver a campañas
        </RouterLink>
      </div>
    </div>
  );
}
