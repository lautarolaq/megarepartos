import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { useMutation } from "@tanstack/react-query";
import { Check, Download, Link2, MessageSquare, Printer, Search, Send, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";

interface ProductoPedido {
  producto_id: string;
  nombre: string;
  cantidad_llenos: number;
  cantidad_vacios: number;
  es_retornable: boolean;
}

interface Pedido {
  evento_id: string;
  cliente_id: string;
  cliente_nombre: string;
  cliente_telefono: string;
  cliente_direccion: string | null;
  cliente_zona_id: string | null;
  cliente_zona_nombre: string | null;
  campana_id: string | null;
  campana_nombre: string | null;
  campana_zona_id: string | null;
  campana_zona_nombre: string | null;
  zona_mismatch: boolean;
  accion: "confirmo" | "rechazo" | string;
  productos: ProductoPedido[];
  observacion: string | null;
  fecha: string;
}

interface PedidoListResp {
  items: Pedido[];
  total: number;
  limit: number;
  offset: number;
}

function formatearFecha(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("es-AR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

type FiltroAccion = "todos" | "confirmo" | "rechazo";
type FiltroFecha = "hoy" | "semana" | "mes" | "todos";

const FECHA_DIAS: Record<FiltroFecha, number | null> = {
  hoy: 1,
  semana: 7,
  mes: 30,
  todos: null,
};

interface ZonaItem {
  id: string;
  nombre: string;
}

export function PedidosPage() {
  const [filtroAccion, setFiltroAccion] = useState<FiltroAccion>("todos");
  const [filtroFecha, setFiltroFecha] = useState<FiltroFecha>("semana");
  const [filtroZona, setFiltroZona] = useState<string>(""); // "" todas, uuid zona específica, "__none__" sin zona
  const [agruparZona, setAgruparZona] = useState(false);
  const [q, setQ] = useState("");
  const [qDebounced, setQDebounced] = useState("");

  const { data: zonasData } = useQuery({
    queryKey: ["zonas"],
    queryFn: async (): Promise<{ items: ZonaItem[] }> => (await api.get("/api/zonas")).data,
  });

  useEffect(() => {
    const t = setTimeout(() => setQDebounced(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);

  const { data, isLoading, error } = useQuery({
    queryKey: ["pedidos", filtroAccion, filtroFecha, qDebounced],
    queryFn: async (): Promise<PedidoListResp> => {
      const params: Record<string, string | number> = {};
      if (filtroAccion !== "todos") params.accion = filtroAccion;
      const dias = FECHA_DIAS[filtroFecha];
      if (dias !== null) params.desde_dias = dias;
      if (qDebounced) params.q = qDebounced;
      return (await api.get("/api/pedidos", { params })).data;
    },
    refetchInterval: 30_000,
  });

  async function exportarCsv() {
    const params: Record<string, string | number> = {};
    if (filtroAccion !== "todos") params.accion = filtroAccion;
    else params.accion = "confirmo";
    const dias = FECHA_DIAS[filtroFecha];
    if (dias !== null) params.desde_dias = dias;
    if (qDebounced) params.q = qDebounced;
    const resp = await api.get<Blob>("/api/pedidos/export.csv", {
      params,
      responseType: "blob",
    });
    const url = URL.createObjectURL(resp.data);
    const a = document.createElement("a");
    a.href = url;
    const fecha = new Date().toISOString().slice(0, 10);
    a.download = `pedidos-${fecha}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Pedidos</h2>
          <p className="mt-1 text-sm text-slate-500">
            Respuestas de los clientes que recibieron tu link por WhatsApp.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => window.print()}
            className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
            title="Imprimir hoja de ruta"
          >
            <Printer size={14} />
            Imprimir
          </button>
          <button
            type="button"
            onClick={exportarCsv}
            className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
            title="Exportar a CSV (para imprimir o pegar en hoja de ruta)"
          >
            <Download size={14} />
            Exportar CSV
          </button>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <SegmentedControl
          value={filtroFecha}
          onChange={setFiltroFecha}
          options={[
            { value: "hoy", label: "Hoy" },
            { value: "semana", label: "7 días" },
            { value: "mes", label: "30 días" },
            { value: "todos", label: "Todos" },
          ]}
        />
        <SegmentedControl
          value={filtroAccion}
          onChange={setFiltroAccion}
          options={[
            { value: "todos", label: "Todos" },
            { value: "confirmo", label: "Confirmaron" },
            { value: "rechazo", label: "Rechazaron" },
          ]}
        />
        <select
          value={filtroZona}
          onChange={(e) => setFiltroZona(e.target.value)}
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
        >
          <option value="">Todas las zonas</option>
          {(zonasData?.items ?? []).map((z) => (
            <option key={z.id} value={z.id}>
              {z.nombre}
            </option>
          ))}
          <option value="__none__">Sin zona asignada</option>
        </select>
        <div className="relative flex-1 min-w-[14rem] max-w-sm">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Buscar cliente…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="w-full rounded-md border border-slate-300 bg-white py-1.5 pl-8 pr-3 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          />
        </div>
        <label className="inline-flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={agruparZona}
            onChange={(e) => setAgruparZona(e.target.checked)}
            className="rounded border-slate-300"
          />
          Agrupar por zona
        </label>
      </div>

      {isLoading && <p className="mt-6 text-slate-500">Cargando…</p>}
      {error && <p className="mt-6 text-rose-600">Error al cargar pedidos.</p>}
      {data && data.items.length === 0 && (
        <div className="mt-8 rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
          <MessageSquare className="mx-auto mb-2 text-slate-400" size={28} />
          <p>Todavía no hay respuestas.</p>
          <p className="mt-1 text-xs text-slate-400">
            Cuando un cliente abra su link y confirme, vas a verlo acá.
          </p>
        </div>
      )}

      {data &&
        data.items.length > 0 &&
        (() => {
          const filtered = filtroZona
            ? data.items.filter((p) => {
                if (filtroZona === "__none__") {
                  return p.cliente_zona_id === null && p.campana_zona_id === null;
                }
                // Match si el cliente es de esa zona O si vino por una campaña
                // de esa zona (caso de mismatch — el pedido pertenece a la
                // ruta del sodero aunque el cliente sea de otra zona).
                return p.cliente_zona_id === filtroZona || p.campana_zona_id === filtroZona;
              })
            : data.items;
          return (
            <>
              <p className="mt-4 text-xs text-slate-500">
                {filtered.length} pedido{filtered.length === 1 ? "" : "s"}
                {filtroZona && filtered.length !== data.items.length && (
                  <span className="text-slate-400"> (filtrados de {data.items.length})</span>
                )}
              </p>
              {agruparZona ? (
                <PedidosPorZona items={filtered} />
              ) : (
                <div className="mt-2 flex flex-col gap-3">
                  {filtered.map((p) => (
                    <PedidoCard key={p.evento_id} pedido={p} />
                  ))}
                </div>
              )}
            </>
          );
        })()}
    </div>
  );
}

function PedidosPorZona({ items }: { items: Pedido[] }) {
  // Agrupar por zona "operativa": si el pedido vino de una campaña con zona,
  // usar la zona de la campaña (porque es la ruta del sodero ese día). Si no,
  // la zona del cliente. Esto hace que los pedidos con mismatch caigan en
  // el grupo correcto para la ruta.
  const grupos = new Map<string, Pedido[]>();
  for (const p of items) {
    const key = p.campana_zona_nombre ?? p.cliente_zona_nombre ?? "Sin zona";
    const arr = grupos.get(key) ?? [];
    arr.push(p);
    grupos.set(key, arr);
  }
  const ordenadas = Array.from(grupos.entries()).sort(([a], [b]) => {
    if (a === "Sin zona") return 1;
    if (b === "Sin zona") return -1;
    return a.localeCompare(b);
  });

  return (
    <div className="mt-2 flex flex-col gap-6">
      {ordenadas.map(([zona, pedidos]) => (
        <section key={zona}>
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-600">
            {zona}
            <span className="ml-2 font-normal text-slate-400">
              ({pedidos.length} pedido{pedidos.length === 1 ? "" : "s"})
            </span>
          </h3>
          <div className="flex flex-col gap-3">
            {pedidos.map((p) => (
              <PedidoCard key={p.evento_id} pedido={p} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

function SegmentedControl<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <div className="inline-flex overflow-hidden rounded-md border border-slate-200 bg-white text-sm">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`px-3 py-1.5 transition-colors ${
            value === opt.value ? "bg-sky-600 text-white" : "text-slate-600 hover:bg-slate-50"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

function PedidoCard({ pedido }: { pedido: Pedido }) {
  const confirmo = pedido.accion === "confirmo";
  const llenos = pedido.productos.filter((p) => p.cantidad_llenos > 0);
  const vacios = pedido.productos.filter((p) => p.es_retornable && p.cantidad_vacios > 0);
  const telDigits = pedido.cliente_telefono.replace(/\D/g, "");
  const waUrl = `https://wa.me/${telDigits}`;

  const reenviar = useMutation({
    mutationFn: async () => {
      const resp = await api.post<{ url: string }>(
        `/api/clientes/${pedido.cliente_id}/generar-link`,
      );
      return resp.data.url;
    },
    onSuccess: (url) => {
      const primer = pedido.cliente_nombre.split(" ")[0];
      const msg = `Hola ${primer}! Volvemos a pasar pronto. Confirmá tu pedido en este link:\n\n${url}`;
      const w = window.open(
        `https://wa.me/${telDigits}?text=${encodeURIComponent(msg)}`,
        "_blank",
        "noopener",
      );
      if (!w) navigator.clipboard?.writeText(url);
    },
  });

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="truncate font-semibold">
            <RouterLink
              to={`/dashboard/clientes/${pedido.cliente_id}`}
              className="text-slate-800 hover:text-sky-600 hover:underline"
            >
              {pedido.cliente_nombre}
            </RouterLink>
          </h3>
          <p className="text-xs text-slate-500">{pedido.cliente_telefono}</p>
          {pedido.cliente_direccion && (
            <p className="mt-0.5 text-xs text-slate-500">{pedido.cliente_direccion}</p>
          )}
          <div className="mt-1 flex flex-wrap items-center gap-1">
            {pedido.zona_mismatch ? (
              <span
                className="inline-flex items-center gap-1 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-900"
                title={`Este cliente es de ${pedido.cliente_zona_nombre ?? "sin zona"}, pero respondió a una campaña de zona ${pedido.campana_zona_nombre ?? "—"}`}
              >
                ⚠ {pedido.campana_zona_nombre ?? "—"} (cliente:{" "}
                {pedido.cliente_zona_nombre ?? "sin zona"})
              </span>
            ) : (
              pedido.cliente_zona_nombre && (
                <span className="inline-block rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                  {pedido.cliente_zona_nombre}
                </span>
              )
            )}
            {pedido.campana_nombre && !pedido.zona_mismatch && (
              <span className="inline-block rounded bg-sky-50 px-1.5 py-0.5 text-xs text-sky-700">
                {pedido.campana_nombre}
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
              confirmo ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"
            }`}
          >
            {confirmo ? <Check size={12} /> : <X size={12} />}
            {confirmo ? "Confirmó" : "Rechazó"}
          </span>
          <span className="text-xs text-slate-400">{formatearFecha(pedido.fecha)}</span>
        </div>
      </header>

      {confirmo && llenos.length > 0 && (
        <div className="mt-3">
          <p className="text-xs uppercase tracking-wider text-slate-500">Lleva</p>
          <ul className="mt-1 text-sm text-slate-700">
            {llenos.map((p) => (
              <li key={p.producto_id}>
                • {p.cantidad_llenos} × {p.nombre}
              </li>
            ))}
          </ul>
        </div>
      )}

      {confirmo && vacios.length > 0 && (
        <div className="mt-2">
          <p className="text-xs uppercase tracking-wider text-slate-500">Devuelve</p>
          <ul className="mt-1 text-sm text-slate-700">
            {vacios.map((p) => (
              <li key={p.producto_id}>
                • {p.cantidad_vacios} × {p.nombre} (vacíos)
              </li>
            ))}
          </ul>
        </div>
      )}

      {pedido.observacion && (
        <p className="mt-3 rounded-md bg-slate-50 p-2 text-sm italic text-slate-600">
          “{pedido.observacion}”
        </p>
      )}

      <div className="mt-3 flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={() => reenviar.mutate()}
          disabled={reenviar.isPending}
          className="inline-flex items-center gap-1 text-xs font-medium text-sky-700 hover:text-sky-800 disabled:opacity-50"
        >
          <Link2 size={12} />
          {reenviar.isPending ? "Generando…" : "Enviar link nuevo"}
        </button>
        <a
          href={waUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 hover:text-emerald-800"
        >
          <Send size={12} />
          Abrir WhatsApp
        </a>
      </div>
    </article>
  );
}
