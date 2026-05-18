import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2, Truck } from "lucide-react";
import { useEffect, useState } from "react";

interface Zona {
  id: string;
  nombre: string;
  dia_visita: string | null;
  camioneta_asignada: string | null;
  color_display: string | null;
  broadcast_list_name: string | null;
  activo: boolean;
}

type Dia = "lunes" | "martes" | "miercoles" | "jueves" | "viernes" | "sabado" | "domingo";

const DIAS: Dia[] = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"];

export function ZonasPage() {
  const qc = useQueryClient();
  const [openCreate, setOpenCreate] = useState(false);
  const [zonaEditar, setZonaEditar] = useState<Zona | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["zonas"],
    queryFn: async (): Promise<{ items: Zona[] }> => (await api.get("/api/zonas")).data,
  });

  const desactivarMut = useMutation({
    mutationFn: async (id: string) => api.delete(`/api/zonas/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["zonas"] }),
  });

  return (
    <div>
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold tracking-tight">Zonas</h2>
        <Button onClick={() => setOpenCreate(true)}>+ Nueva zona</Button>
      </div>

      {isLoading && <p className="mt-4 text-slate-500">Cargando…</p>}
      {data && data.items.length === 0 && (
        <EmptyState
          icon={<Truck size={20} />}
          title="Sin zonas todavía"
          body="Las zonas agrupan a tus clientes por barrio o día de visita. Te sirven para mandar campañas a un grupo y para imprimir hojas de ruta."
          cta={<Button onClick={() => setOpenCreate(true)}>+ Crear primera zona</Button>}
        />
      )}
      {data && data.items.length > 0 && (
        <div className="mt-6 -mx-4 sm:mx-0 overflow-x-auto">
          <table className="w-full min-w-[640px] sm:min-w-0 overflow-hidden rounded-md border border-slate-200 bg-white text-sm sm:rounded-md">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2">Nombre</th>
                <th className="px-4 py-2">Día de visita</th>
                <th className="px-4 py-2">Camioneta</th>
                <th className="px-4 py-2">Color</th>
                <th className="px-4 py-2">Estado</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {data.items.map((z) => (
                <tr key={z.id} className="border-t border-slate-200">
                  <td className="px-4 py-2 font-medium">{z.nombre}</td>
                  <td className="px-4 py-2 capitalize">{z.dia_visita ?? "—"}</td>
                  <td className="px-4 py-2">{z.camioneta_asignada ?? "—"}</td>
                  <td className="px-4 py-2">
                    {z.color_display ? (
                      <span
                        className="inline-block h-4 w-4 rounded-full border border-slate-200"
                        style={{ backgroundColor: z.color_display }}
                        title={z.color_display}
                      />
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        z.activo ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {z.activo ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    {z.activo && (
                      <div className="flex justify-end gap-3">
                        <button
                          type="button"
                          className="text-slate-600 hover:text-slate-800"
                          title="Editar"
                          onClick={() => setZonaEditar(z)}
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          type="button"
                          className="text-rose-600 hover:text-rose-800"
                          title="Desactivar"
                          onClick={() => {
                            if (confirm(`¿Desactivar "${z.nombre}"?`)) desactivarMut.mutate(z.id);
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
        </div>
      )}

      <CrearZonaModal open={openCreate} onClose={() => setOpenCreate(false)} />
      <EditarZonaModal zona={zonaEditar} onClose={() => setZonaEditar(null)} />
    </div>
  );
}

function EditarZonaModal({ zona, onClose }: { zona: Zona | null; onClose: () => void }) {
  const qc = useQueryClient();
  const [nombre, setNombre] = useState("");
  const [dia, setDia] = useState<Dia | "">("");
  const [camioneta, setCamioneta] = useState("");
  const [color, setColor] = useState("#0ea5e9");
  const [broadcastListName, setBroadcastListName] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (zona) {
      setNombre(zona.nombre);
      setDia((zona.dia_visita as Dia | null) ?? "");
      setCamioneta(zona.camioneta_asignada ?? "");
      setColor(zona.color_display ?? "#0ea5e9");
      setBroadcastListName(zona.broadcast_list_name ?? "");
      setError(null);
    }
  }, [zona]);

  const actualizar = useMutation({
    mutationFn: async () => {
      if (!zona) throw new Error("missing zona");
      return api.patch(`/api/zonas/${zona.id}`, {
        nombre,
        dia_visita: dia || null,
        camioneta_asignada: camioneta || null,
        color_display: color || null,
        broadcast_list_name: broadcastListName.trim() || null,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["zonas"] });
      onClose();
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { error?: { message?: string } } } };
      setError(e.response?.data?.error?.message ?? "Error al actualizar zona.");
    },
  });

  return (
    <Modal open={!!zona} onClose={onClose} title="Editar zona">
      <div className="flex flex-col gap-3">
        <Input
          label="Nombre"
          name="nombre"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
        />
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Día de visita</span>
          <select
            value={dia}
            onChange={(e) => setDia(e.target.value as Dia | "")}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          >
            <option value="">— sin asignar —</option>
            {DIAS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <Input
          label="Camioneta"
          name="camioneta"
          value={camioneta}
          onChange={(e) => setCamioneta(e.target.value)}
        />
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Color</span>
          <input
            type="color"
            value={color}
            onChange={(e) => setColor(e.target.value)}
            className="h-10 w-20 cursor-pointer rounded-md border border-slate-300"
          />
        </label>
        <Input
          label="Lista de difusión de WhatsApp (opcional)"
          name="broadcast_list_name"
          placeholder='Ej: "Norte Miércoles"'
          value={broadcastListName}
          onChange={(e) => setBroadcastListName(e.target.value)}
        />
        <p className="-mt-2 text-xs text-slate-500">
          Nombre exacto de tu lista en WhatsApp. Lo usamos como hint cuando mandes una campaña
          broadcast a esta zona.
        </p>
        {error && <p className="text-sm text-rose-600">{error}</p>}
        <div className="mt-2 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            onClick={() => actualizar.mutate()}
            disabled={!nombre.trim() || actualizar.isPending}
          >
            {actualizar.isPending ? "Guardando…" : "Guardar"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function CrearZonaModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [nombre, setNombre] = useState("");
  const [dia, setDia] = useState<Dia | "">("");
  const [camioneta, setCamioneta] = useState("");
  const [color, setColor] = useState("#0ea5e9");
  const [broadcastListName, setBroadcastListName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const crear = useMutation({
    mutationFn: async () =>
      api.post("/api/zonas", {
        nombre,
        dia_visita: dia || null,
        camioneta_asignada: camioneta || null,
        color_display: color || null,
        broadcast_list_name: broadcastListName.trim() || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["zonas"] });
      setNombre("");
      setDia("");
      setCamioneta("");
      setColor("#0ea5e9");
      setBroadcastListName("");
      setError(null);
      onClose();
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { error?: { message?: string } } } };
      setError(e.response?.data?.error?.message ?? "Error al crear zona.");
    },
  });

  return (
    <Modal open={open} onClose={onClose} title="Nueva zona">
      <div className="flex flex-col gap-3">
        <Input
          label="Nombre"
          name="nombre"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Nueva Córdoba"
        />
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Día de visita</span>
          <select
            value={dia}
            onChange={(e) => setDia(e.target.value as Dia | "")}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          >
            <option value="">— sin asignar —</option>
            {DIAS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <Input
          label="Camioneta (opcional)"
          name="camioneta"
          value={camioneta}
          onChange={(e) => setCamioneta(e.target.value)}
          placeholder="Verde"
        />
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Color (opcional)</span>
          <input
            type="color"
            value={color}
            onChange={(e) => setColor(e.target.value)}
            className="h-10 w-20 cursor-pointer rounded-md border border-slate-300"
          />
        </label>
        <Input
          label="Lista de difusión de WhatsApp (opcional)"
          name="broadcast_list_name"
          placeholder='Ej: "Norte Miércoles"'
          value={broadcastListName}
          onChange={(e) => setBroadcastListName(e.target.value)}
        />
        {error && <p className="text-sm text-rose-600">{error}</p>}
        <div className="mt-2 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
          <Button onClick={() => crear.mutate()} disabled={!nombre.trim() || crear.isPending}>
            {crear.isPending ? "Creando…" : "Crear"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
