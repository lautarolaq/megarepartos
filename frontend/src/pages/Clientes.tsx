import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
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
                      <button
                        type="button"
                        className="text-rose-600 hover:text-rose-800"
                        onClick={() => {
                          if (confirm(`¿Desactivar a "${c.nombre_completo}"?`)) {
                            desactivarMut.mutate(c.id);
                          }
                        }}
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <CrearClienteModal open={openCreate} onClose={() => setOpenCreate(false)} />
    </div>
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
