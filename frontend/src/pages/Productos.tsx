import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

interface Producto {
  id: string;
  nombre: string;
  descripcion: string | null;
  precio_unitario_default: string | null;
  es_retornable: boolean;
  activo: boolean;
  orden_display: number;
}

export function ProductosPage() {
  const qc = useQueryClient();
  const [openCreate, setOpenCreate] = useState(false);
  const [productoEditar, setProductoEditar] = useState<Producto | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["productos"],
    queryFn: async (): Promise<{ items: Producto[] }> => (await api.get("/api/productos")).data,
  });

  const desactivarMut = useMutation({
    mutationFn: async (id: string) => api.delete(`/api/productos/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["productos"] }),
  });

  return (
    <div>
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold tracking-tight">Productos</h2>
        <Button onClick={() => setOpenCreate(true)}>+ Nuevo producto</Button>
      </div>

      {isLoading && <p className="mt-4 text-slate-500">Cargando…</p>}
      {data && (
        <table className="mt-6 w-full overflow-hidden rounded-md border border-slate-200 bg-white text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Nombre</th>
              <th className="px-4 py-2">Precio</th>
              <th className="px-4 py-2">Retornable</th>
              <th className="px-4 py-2">Estado</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-slate-400">
                  No hay productos todavía.
                </td>
              </tr>
            )}
            {data.items.map((p) => (
              <tr key={p.id} className="border-t border-slate-200">
                <td className="px-4 py-2 font-medium">{p.nombre}</td>
                <td className="px-4 py-2">
                  {p.precio_unitario_default ? `$ ${p.precio_unitario_default}` : "—"}
                </td>
                <td className="px-4 py-2">{p.es_retornable ? "Sí" : "No"}</td>
                <td className="px-4 py-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      p.activo ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {p.activo ? "Activo" : "Inactivo"}
                  </span>
                </td>
                <td className="px-4 py-2 text-right">
                  {p.activo && (
                    <div className="flex justify-end gap-3">
                      <button
                        type="button"
                        className="text-slate-600 hover:text-slate-800"
                        title="Editar"
                        onClick={() => setProductoEditar(p)}
                      >
                        <Pencil size={16} />
                      </button>
                      <button
                        type="button"
                        className="text-rose-600 hover:text-rose-800"
                        title="Desactivar"
                        onClick={() => {
                          if (confirm(`¿Desactivar "${p.nombre}"?`)) {
                            desactivarMut.mutate(p.id);
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
      )}

      <CrearProductoModal open={openCreate} onClose={() => setOpenCreate(false)} />
      <EditarProductoModal producto={productoEditar} onClose={() => setProductoEditar(null)} />
    </div>
  );
}

function EditarProductoModal({
  producto,
  onClose,
}: {
  producto: Producto | null;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [nombre, setNombre] = useState("");
  const [precio, setPrecio] = useState("");
  const [retornable, setRetornable] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (producto) {
      setNombre(producto.nombre);
      setPrecio(producto.precio_unitario_default ?? "");
      setRetornable(producto.es_retornable);
      setError(null);
    }
  }, [producto]);

  const actualizar = useMutation({
    mutationFn: async () => {
      if (!producto) throw new Error("missing producto");
      return api.patch(`/api/productos/${producto.id}`, {
        nombre,
        precio_unitario_default: precio || null,
        es_retornable: retornable,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["productos"] });
      onClose();
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { error?: { message?: string } } } };
      setError(e.response?.data?.error?.message ?? "Error al actualizar producto.");
    },
  });

  return (
    <Modal open={!!producto} onClose={onClose} title="Editar producto">
      <div className="flex flex-col gap-3">
        <Input
          label="Nombre"
          name="nombre"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
        />
        <Input
          label="Precio unitario"
          name="precio"
          value={precio}
          onChange={(e) => setPrecio(e.target.value)}
          inputMode="decimal"
        />
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={retornable}
            onChange={(e) => setRetornable(e.target.checked)}
          />
          Es retornable (requiere envase)
        </label>
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

function CrearProductoModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [nombre, setNombre] = useState("");
  const [precio, setPrecio] = useState("");
  const [retornable, setRetornable] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const crear = useMutation({
    mutationFn: async () =>
      api.post("/api/productos", {
        nombre,
        precio_unitario_default: precio || null,
        es_retornable: retornable,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["productos"] });
      setNombre("");
      setPrecio("");
      setRetornable(false);
      setError(null);
      onClose();
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { error?: { message?: string } } } };
      setError(e.response?.data?.error?.message ?? "Error al crear producto.");
    },
  });

  return (
    <Modal open={open} onClose={onClose} title="Nuevo producto">
      <div className="flex flex-col gap-3">
        <Input
          label="Nombre"
          name="nombre"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Bidón 20L"
        />
        <Input
          label="Precio unitario (opcional)"
          name="precio"
          value={precio}
          onChange={(e) => setPrecio(e.target.value)}
          placeholder="1500.00"
          inputMode="decimal"
        />
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={retornable}
            onChange={(e) => setRetornable(e.target.checked)}
          />
          Es retornable (requiere envase)
        </label>
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
