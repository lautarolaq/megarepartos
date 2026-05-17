import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { Check, MessageSquare, X } from "lucide-react";

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

export function PedidosPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["pedidos"],
    queryFn: async (): Promise<PedidoListResp> => (await api.get("/api/pedidos")).data,
    refetchInterval: 30_000,
  });

  return (
    <div>
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Pedidos</h2>
        <p className="mt-1 text-sm text-slate-500">
          Respuestas de los clientes que recibieron tu link por WhatsApp.
        </p>
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

function PedidoCard({ pedido }: { pedido: Pedido }) {
  const confirmo = pedido.accion === "confirmo";
  const llenos = pedido.productos.filter((p) => p.cantidad_llenos > 0);
  const vacios = pedido.productos.filter((p) => p.es_retornable && p.cantidad_vacios > 0);

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <header className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-slate-800">{pedido.cliente_nombre}</h3>
          <p className="text-xs text-slate-500">{pedido.cliente_telefono}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
              confirmo
                ? "bg-emerald-100 text-emerald-700"
                : "bg-slate-100 text-slate-600"
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
    </article>
  );
}
