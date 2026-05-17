import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { Check, Download, MessageSquare, Printer, Send, X } from "lucide-react";
import { useState } from "react";

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

export function PedidosPage() {
  const [filtroAccion, setFiltroAccion] = useState<FiltroAccion>("todos");
  const [filtroFecha, setFiltroFecha] = useState<FiltroFecha>("semana");

  const { data, isLoading, error } = useQuery({
    queryKey: ["pedidos", filtroAccion, filtroFecha],
    queryFn: async (): Promise<PedidoListResp> => {
      const params: Record<string, string | number> = {};
      if (filtroAccion !== "todos") params.accion = filtroAccion;
      const dias = FECHA_DIAS[filtroFecha];
      if (dias !== null) params.desde_dias = dias;
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

      {data && data.items.length > 0 && (
        <>
          <p className="mt-4 text-xs text-slate-500">
            {data.total} pedido{data.total === 1 ? "" : "s"}
          </p>
          <div className="mt-2 flex flex-col gap-3">
            {data.items.map((p) => (
              <PedidoCard key={p.evento_id} pedido={p} />
            ))}
          </div>
        </>
      )}
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

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="truncate font-semibold text-slate-800">{pedido.cliente_nombre}</h3>
          <p className="text-xs text-slate-500">{pedido.cliente_telefono}</p>
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

      <div className="mt-3 flex justify-end">
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
