import { api } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Check, Link2, Mail, MapPin, Package, Phone, Send, X } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

interface Cliente {
  id: string;
  nombre_completo: string;
  telefono: string;
  email: string | null;
  direccion: string | null;
  zona_id: string | null;
  modalidad: string;
  frecuencia: string | null;
  observaciones_permanentes: string | null;
  condicion_pago: string;
  activo: boolean;
}

interface Zona {
  id: string;
  nombre: string;
}

interface ProductoHabitual {
  producto_id: string;
  cantidad: number;
  nombre: string;
  es_retornable: boolean;
}

interface ProductoPedido {
  producto_id: string;
  nombre: string;
  cantidad_llenos: number;
  cantidad_vacios: number;
  es_retornable: boolean;
}

interface HistorialEvento {
  evento_id: string;
  accion: "link_generado" | "respondio_link" | string;
  fecha: string;
  detalles: {
    accion?: "confirmo" | "rechazo";
    productos?: ProductoPedido[];
    observacion?: string | null;
  };
}

function formatearFecha(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("es-AR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ClienteDetallePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: cliente, isLoading: loadingCliente } = useQuery({
    queryKey: ["cliente", id],
    queryFn: async (): Promise<Cliente> => (await api.get(`/api/clientes/${id}`)).data,
    enabled: !!id,
  });

  const { data: zonas } = useQuery({
    queryKey: ["zonas"],
    queryFn: async (): Promise<{ items: Zona[] }> => (await api.get("/api/zonas")).data,
  });

  const { data: habituales } = useQuery({
    queryKey: ["habituales", id],
    queryFn: async (): Promise<{ items: ProductoHabitual[] }> =>
      (await api.get(`/api/clientes/${id}/productos-habituales`)).data,
    enabled: !!id,
  });

  const { data: historial } = useQuery({
    queryKey: ["cliente-historial", id],
    queryFn: async (): Promise<{ items: HistorialEvento[] }> =>
      (await api.get(`/api/clientes/${id}/historial?limit=50`)).data,
    enabled: !!id,
  });

  if (loadingCliente) return <p className="text-slate-500">Cargando…</p>;
  if (!cliente) {
    return (
      <div>
        <p className="text-rose-600">Cliente no encontrado.</p>
        <button
          type="button"
          onClick={() => navigate("/dashboard/clientes")}
          className="mt-2 text-sm text-sky-600 hover:text-sky-800"
        >
          ← Volver a clientes
        </button>
      </div>
    );
  }

  const zonaNombre = cliente.zona_id
    ? (zonas?.items.find((z) => z.id === cliente.zona_id)?.nombre ?? "—")
    : "—";
  const telDigits = cliente.telefono.replace(/\D/g, "");
  const waUrl = `https://wa.me/${telDigits}`;

  return (
    <div className="max-w-4xl">
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Link
          to="/dashboard/clientes"
          className="inline-flex items-center gap-1 hover:text-sky-600"
        >
          <ArrowLeft size={14} />
          Clientes
        </Link>
        <span>/</span>
        <span className="text-slate-700">{cliente.nombre_completo}</span>
      </div>

      <div className="mt-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-800">
            {cliente.nombre_completo}
          </h2>
          <div className="mt-1 flex flex-wrap gap-3 text-sm text-slate-600">
            <span className="inline-flex items-center gap-1">
              <Phone size={12} />
              {cliente.telefono}
            </span>
            {cliente.email && (
              <span className="inline-flex items-center gap-1">
                <Mail size={12} />
                {cliente.email}
              </span>
            )}
            {cliente.direccion && (
              <span className="inline-flex items-center gap-1">
                <MapPin size={12} />
                {cliente.direccion}
              </span>
            )}
          </div>
        </div>
        <a
          href={waUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700"
        >
          <Send size={14} />
          WhatsApp
        </a>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="text-xs font-medium uppercase tracking-wider text-slate-500">Datos</h3>
          <dl className="mt-2 space-y-1 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">Zona</dt>
              <dd className="font-medium text-slate-700">{zonaNombre}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Modalidad</dt>
              <dd className="font-medium capitalize text-slate-700">{cliente.modalidad}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Frecuencia</dt>
              <dd className="font-medium capitalize text-slate-700">{cliente.frecuencia ?? "—"}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Pago</dt>
              <dd className="font-medium text-slate-700">
                {cliente.condicion_pago === "contado" ? "Contado" : "Cta. corriente"}
              </dd>
            </div>
          </dl>
          {cliente.observaciones_permanentes && (
            <p className="mt-3 rounded-md bg-slate-50 p-2 text-xs italic text-slate-600">
              “{cliente.observaciones_permanentes}”
            </p>
          )}
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:col-span-2">
          <h3 className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-slate-500">
            <Package size={12} />
            Productos habituales
          </h3>
          {habituales && habituales.items.length === 0 && (
            <p className="mt-2 text-sm text-slate-400">
              Sin productos asignados. Configurálos desde la tabla de clientes.
            </p>
          )}
          {habituales && habituales.items.length > 0 && (
            <ul className="mt-2 grid gap-1 sm:grid-cols-2">
              {habituales.items.map((h) => (
                <li key={h.producto_id} className="text-sm text-slate-700">
                  • {h.cantidad} × {h.nombre}
                  {h.es_retornable && (
                    <span className="ml-1 text-xs text-slate-400">(retornable)</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-medium text-slate-700">Historial</h3>
        {historial && historial.items.length === 0 && (
          <div className="mt-2 rounded-xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-500">
            Sin interacciones todavía. Cuando le mandes el link y responda, vas a ver el historial
            acá.
          </div>
        )}
        {historial && historial.items.length > 0 && (
          <ol className="mt-2 space-y-2">
            {historial.items.map((ev) => (
              <HistorialItem key={ev.evento_id} ev={ev} />
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}

function HistorialItem({ ev }: { ev: HistorialEvento }) {
  if (ev.accion === "link_generado") {
    return (
      <li className="flex items-center gap-3 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm">
        <Link2 size={14} className="text-sky-600" />
        <span className="flex-1 text-slate-600">Link enviado</span>
        <span className="text-xs text-slate-400">{formatearFecha(ev.fecha)}</span>
      </li>
    );
  }

  if (ev.accion === "respondio_link") {
    const accion = ev.detalles.accion;
    const confirmo = accion === "confirmo";
    const productos = ev.detalles.productos ?? [];
    const llenos = productos.filter((p) => p.cantidad_llenos > 0);
    const vacios = productos.filter((p) => p.es_retornable && p.cantidad_vacios > 0);
    return (
      <li
        className={`rounded-md border px-3 py-2 text-sm ${
          confirmo ? "border-emerald-200 bg-emerald-50" : "border-slate-200 bg-slate-50"
        }`}
      >
        <div className="flex items-center gap-2">
          {confirmo ? (
            <Check size={14} className="text-emerald-600" />
          ) : (
            <X size={14} className="text-slate-500" />
          )}
          <span className="flex-1 font-medium text-slate-700">
            {confirmo ? "Confirmó" : "Rechazó"}
          </span>
          <span className="text-xs text-slate-400">{formatearFecha(ev.fecha)}</span>
        </div>
        {llenos.length > 0 && (
          <ul className="mt-2 pl-6 text-xs text-slate-600">
            {llenos.map((p) => (
              <li key={p.producto_id}>
                {p.cantidad_llenos} × {p.nombre}
              </li>
            ))}
          </ul>
        )}
        {vacios.length > 0 && (
          <ul className="mt-1 pl-6 text-xs text-slate-500">
            {vacios.map((p) => (
              <li key={p.producto_id}>
                Devuelve {p.cantidad_vacios} × {p.nombre}
              </li>
            ))}
          </ul>
        )}
        {ev.detalles.observacion && (
          <p className="mt-1 pl-6 text-xs italic text-slate-600">“{ev.detalles.observacion}”</p>
        )}
      </li>
    );
  }

  return null;
}
