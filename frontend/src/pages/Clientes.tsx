import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link2, Package, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

interface Cliente {
  id: string;
  nombre_completo: string;
  telefono: string;
  email: string | null;
  direccion: string | null;
  modalidad: string;
  condicion_pago: string;
  activo: boolean;
}

interface ClienteListResp {
  items: Cliente[];
  total: number;
  limit: number;
  offset: number;
}

export function ClientesPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [qDebounced, setQDebounced] = useState("");
  const [openCreate, setOpenCreate] = useState(false);
  const [clienteHabituales, setClienteHabituales] = useState<Cliente | null>(null);

  // Debounce simple sin librería: 300ms.
  useEffect(() => {
    const t = setTimeout(() => setQDebounced(q.trim()), 300);
    return () => clearTimeout(t);
  }, [q]);

  const { data, isLoading } = useQuery({
    queryKey: ["clientes", qDebounced],
    queryFn: async (): Promise<ClienteListResp> => {
      const resp = await api.get<ClienteListResp>("/api/clientes", {
        params: qDebounced ? { q: qDebounced, limit: 100 } : { limit: 100 },
      });
      return resp.data;
    },
  });

  const desactivarMut = useMutation({
    mutationFn: async (id: string) => api.delete(`/api/clientes/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["clientes"] }),
  });

  const generarLinkMut = useMutation({
    mutationFn: async (id: string) => api.post<{ url: string }>(`/api/clientes/${id}/generar-link`),
    onSuccess: async (resp) => {
      const url = resp.data.url;
      try {
        await navigator.clipboard.writeText(url);
        alert(`Link copiado al portapapeles:\n\n${url}`);
      } catch {
        alert(`Link generado:\n\n${url}\n\n(no se pudo copiar automático)`);
      }
    },
  });

  return (
    <div>
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold tracking-tight">Clientes</h2>
        <Button onClick={() => setOpenCreate(true)}>+ Nuevo cliente</Button>
      </div>

      <div className="mt-4 max-w-md">
        <Input
          placeholder="Buscar por nombre o teléfono…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>

      {isLoading && <p className="mt-4 text-slate-500">Buscando…</p>}
      {data && (
        <>
          <p className="mt-2 text-xs text-slate-500">
            {data.total} resultado{data.total === 1 ? "" : "s"}
          </p>
          <table className="mt-2 w-full overflow-hidden rounded-md border border-slate-200 bg-white text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2">Nombre</th>
                <th className="px-4 py-2">Teléfono</th>
                <th className="px-4 py-2">Dirección</th>
                <th className="px-4 py-2">Modalidad</th>
                <th className="px-4 py-2">Estado</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {data.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                    {qDebounced ? "Sin resultados." : "No hay clientes todavía."}
                  </td>
                </tr>
              )}
              {data.items.map((c) => (
                <tr key={c.id} className="border-t border-slate-200">
                  <td className="px-4 py-2 font-medium">{c.nombre_completo}</td>
                  <td className="px-4 py-2 text-slate-600">{c.telefono}</td>
                  <td className="px-4 py-2 text-slate-600">{c.direccion ?? "—"}</td>
                  <td className="px-4 py-2 capitalize">{c.modalidad}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        c.activo ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {c.activo ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    {c.activo && (
                      <div className="flex justify-end gap-3">
                        <button
                          type="button"
                          className="text-slate-600 hover:text-slate-800"
                          title="Productos habituales"
                          onClick={() => setClienteHabituales(c)}
                        >
                          <Package size={16} />
                        </button>
                        <button
                          type="button"
                          className="text-sky-600 hover:text-sky-800"
                          title="Generar link público"
                          onClick={() => generarLinkMut.mutate(c.id)}
                        >
                          <Link2 size={16} />
                        </button>
                        <button
                          type="button"
                          className="text-rose-600 hover:text-rose-800"
                          title="Desactivar"
                          onClick={() => {
                            if (confirm(`¿Desactivar a "${c.nombre_completo}"?`)) {
                              desactivarMut.mutate(c.id);
                            }
                          }}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <CrearClienteModal open={openCreate} onClose={() => setOpenCreate(false)} />
      <HabitualesModal
        cliente={clienteHabituales}
        onClose={() => setClienteHabituales(null)}
      />
    </div>
  );
}

interface Producto {
  id: string;
  nombre: string;
  es_retornable: boolean;
  activo: boolean;
}

interface HabitualItem {
  producto_id: string;
  cantidad: number;
  nombre: string;
  es_retornable: boolean;
}

function HabitualesModal({
  cliente,
  onClose,
}: {
  cliente: Cliente | null;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [items, setItems] = useState<HabitualItem[]>([]);
  const [agregarId, setAgregarId] = useState<string>("");

  const { data: habituales, isLoading } = useQuery({
    queryKey: ["habituales", cliente?.id],
    queryFn: async (): Promise<{ items: HabitualItem[] }> =>
      (await api.get(`/api/clientes/${cliente!.id}/productos-habituales`)).data,
    enabled: !!cliente,
  });

  const { data: productos } = useQuery({
    queryKey: ["productos"],
    queryFn: async (): Promise<{ items: Producto[] }> => (await api.get("/api/productos")).data,
    enabled: !!cliente,
  });

  useEffect(() => {
    if (habituales) setItems(habituales.items);
  }, [habituales]);

  const guardar = useMutation({
    mutationFn: async () => {
      const payload = {
        items: items.map((it) => ({ producto_id: it.producto_id, cantidad: it.cantidad })),
      };
      return api.put(`/api/clientes/${cliente!.id}/productos-habituales`, payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["habituales", cliente?.id] });
      onClose();
    },
  });

  function setCantidad(producto_id: string, cantidad: number) {
    setItems((prev) =>
      prev.map((it) =>
        it.producto_id === producto_id ? { ...it, cantidad: Math.max(0, cantidad) } : it
      )
    );
  }

  function quitar(producto_id: string) {
    setItems((prev) => prev.filter((it) => it.producto_id !== producto_id));
  }

  function agregar() {
    if (!agregarId || !productos) return;
    const prod = productos.items.find((p) => p.id === agregarId);
    if (!prod) return;
    if (items.some((it) => it.producto_id === prod.id)) return;
    setItems((prev) => [
      ...prev,
      { producto_id: prod.id, cantidad: 1, nombre: prod.nombre, es_retornable: prod.es_retornable },
    ]);
    setAgregarId("");
  }

  const disponibles =
    productos?.items.filter(
      (p) => p.activo && !items.some((it) => it.producto_id === p.id)
    ) ?? [];

  return (
    <Modal
      open={!!cliente}
      onClose={onClose}
      title={cliente ? `Productos habituales — ${cliente.nombre_completo}` : ""}
    >
      <div className="flex flex-col gap-3">
        {isLoading && <p className="text-sm text-slate-500">Cargando…</p>}

        {!isLoading && items.length === 0 && (
          <p className="rounded-md bg-slate-50 p-3 text-sm text-slate-500">
            Sin productos habituales. Agregá los que el cliente compra siempre — se prefijan en el
            link público.
          </p>
        )}

        {items.length > 0 && (
          <ul className="flex flex-col gap-2">
            {items.map((it) => (
              <li
                key={it.producto_id}
                className="flex items-center justify-between gap-3 rounded-md border border-slate-200 px-3 py-2"
              >
                <span className="flex-1 truncate text-sm font-medium text-slate-700">
                  {it.nombre}
                </span>
                <input
                  type="number"
                  min={0}
                  value={it.cantidad}
                  onChange={(e) => setCantidad(it.producto_id, Number(e.target.value))}
                  className="w-16 rounded-md border border-slate-300 px-2 py-1 text-right text-sm"
                />
                <button
                  type="button"
                  className="text-rose-500 hover:text-rose-700"
                  onClick={() => quitar(it.producto_id)}
                  title="Quitar"
                >
                  <Trash2 size={14} />
                </button>
              </li>
            ))}
          </ul>
        )}

        {disponibles.length > 0 && (
          <div className="mt-2 flex gap-2">
            <select
              value={agregarId}
              onChange={(e) => setAgregarId(e.target.value)}
              className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            >
              <option value="">Agregar producto…</option>
              {disponibles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nombre}
                </option>
              ))}
            </select>
            <Button variant="ghost" onClick={agregar} disabled={!agregarId}>
              + Agregar
            </Button>
          </div>
        )}

        <div className="mt-3 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={() => guardar.mutate()} disabled={guardar.isPending}>
            {guardar.isPending ? "Guardando…" : "Guardar"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function CrearClienteModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [nombre, setNombre] = useState("");
  const [telefono, setTelefono] = useState("");
  const [direccion, setDireccion] = useState("");
  const [modalidad, setModalidad] = useState<"fijo" | "consulta" | "demanda">("consulta");
  const [error, setError] = useState<string | null>(null);

  const crear = useMutation({
    mutationFn: async () =>
      api.post("/api/clientes", {
        nombre_completo: nombre,
        telefono,
        direccion: direccion || null,
        modalidad,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["clientes"] });
      setNombre("");
      setTelefono("");
      setDireccion("");
      setModalidad("consulta");
      setError(null);
      onClose();
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { error?: { message?: string } } } };
      setError(e.response?.data?.error?.message ?? "Error al crear cliente.");
    },
  });

  return (
    <Modal open={open} onClose={onClose} title="Nuevo cliente">
      <div className="flex flex-col gap-3">
        <Input
          label="Nombre completo"
          name="nombre"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Juan García"
        />
        <Input
          label="Teléfono"
          name="telefono"
          value={telefono}
          onChange={(e) => setTelefono(e.target.value)}
          placeholder="351 555 1234"
        />
        <Input
          label="Dirección (opcional)"
          name="direccion"
          value={direccion}
          onChange={(e) => setDireccion(e.target.value)}
          placeholder="Av. Colón 123"
        />
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Modalidad</span>
          <select
            value={modalidad}
            onChange={(e) => setModalidad(e.target.value as "fijo" | "consulta" | "demanda")}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          >
            <option value="consulta">Consulta</option>
            <option value="fijo">Fijo</option>
            <option value="demanda">Demanda</option>
          </select>
        </label>
        {error && <p className="text-sm text-rose-600">{error}</p>}
        <div className="mt-2 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            onClick={() => crear.mutate()}
            disabled={!nombre.trim() || !telefono.trim() || crear.isPending}
          >
            {crear.isPending ? "Creando…" : "Crear"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
