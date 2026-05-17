import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { api } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2, Warehouse } from "lucide-react";
import { useEffect, useState } from "react";

interface Envase {
  id: string;
  nombre: string;
  valor_referencial: string | null;
  activo: boolean;
}

export function EnvasesPage() {
  const qc = useQueryClient();
  const [openCreate, setOpenCreate] = useState(false);
  const [envaseEditar, setEnvaseEditar] = useState<Envase | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["envases"],
    queryFn: async (): Promise<{ items: Envase[] }> => (await api.get("/api/envases")).data,
  });

  const desactivarMut = useMutation({
    mutationFn: async (id: string) => api.delete(`/api/envases/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["envases"] }),
  });

  return (
    <div>
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold tracking-tight">Envases</h2>
        <Button onClick={() => setOpenCreate(true)}>+ Nuevo envase</Button>
      </div>

      {isLoading && <p className="mt-4 text-slate-500">Cargando…</p>}
      {data && data.items.length === 0 && (
        <EmptyState
          icon={<Warehouse size={20} />}
          title="Sin envases todavía"
          body="Los envases representan retornables: bidones vacíos que el cliente devuelve. Si vendés productos no-retornables, podés saltearte esta sección."
          cta={<Button onClick={() => setOpenCreate(true)}>+ Crear primer envase</Button>}
        />
      )}
      {data && data.items.length > 0 && (
        <table className="mt-6 w-full overflow-hidden rounded-md border border-slate-200 bg-white text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Nombre</th>
              <th className="px-4 py-2">Valor referencial</th>
              <th className="px-4 py-2">Estado</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {data.items.map((e) => (
              <tr key={e.id} className="border-t border-slate-200">
                <td className="px-4 py-2 font-medium">{e.nombre}</td>
                <td className="px-4 py-2">
                  {e.valor_referencial ? `$ ${e.valor_referencial}` : "—"}
                </td>
                <td className="px-4 py-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      e.activo ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {e.activo ? "Activo" : "Inactivo"}
                  </span>
                </td>
                <td className="px-4 py-2 text-right">
                  {e.activo && (
                    <div className="flex justify-end gap-3">
                      <button
                        type="button"
                        className="text-slate-600 hover:text-slate-800"
                        title="Editar"
                        onClick={() => setEnvaseEditar(e)}
                      >
                        <Pencil size={16} />
                      </button>
                      <button
                        type="button"
                        className="text-rose-600 hover:text-rose-800"
                        title="Desactivar"
                        onClick={() => {
                          if (confirm(`¿Desactivar "${e.nombre}"?`)) desactivarMut.mutate(e.id);
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

      <CrearEnvaseModal open={openCreate} onClose={() => setOpenCreate(false)} />
      <EditarEnvaseModal envase={envaseEditar} onClose={() => setEnvaseEditar(null)} />
    </div>
  );
}

function EditarEnvaseModal({ envase, onClose }: { envase: Envase | null; onClose: () => void }) {
  const qc = useQueryClient();
  const [nombre, setNombre] = useState("");
  const [valor, setValor] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (envase) {
      setNombre(envase.nombre);
      setValor(envase.valor_referencial ?? "");
      setError(null);
    }
  }, [envase]);

  const actualizar = useMutation({
    mutationFn: async () => {
      if (!envase) throw new Error("missing envase");
      return api.patch(`/api/envases/${envase.id}`, {
        nombre,
        valor_referencial: valor || null,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["envases"] });
      onClose();
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { error?: { message?: string } } } };
      setError(e.response?.data?.error?.message ?? "Error al actualizar envase.");
    },
  });

  return (
    <Modal open={!!envase} onClose={onClose} title="Editar envase">
      <div className="flex flex-col gap-3">
        <Input
          label="Nombre"
          name="nombre"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
        />
        <Input
          label="Valor referencial"
          name="valor"
          value={valor}
          onChange={(e) => setValor(e.target.value)}
          inputMode="decimal"
        />
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

function CrearEnvaseModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [nombre, setNombre] = useState("");
  const [valor, setValor] = useState("");
  const [error, setError] = useState<string | null>(null);

  const crear = useMutation({
    mutationFn: async () => api.post("/api/envases", { nombre, valor_referencial: valor || null }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["envases"] });
      setNombre("");
      setValor("");
      setError(null);
      onClose();
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { error?: { message?: string } } } };
      setError(e.response?.data?.error?.message ?? "Error al crear envase.");
    },
  });

  return (
    <Modal open={open} onClose={onClose} title="Nuevo envase">
      <div className="flex flex-col gap-3">
        <Input
          label="Nombre"
          name="nombre"
          value={nombre}
          onChange={(ev) => setNombre(ev.target.value)}
          placeholder="Botellón 20L"
        />
        <Input
          label="Valor referencial (opcional)"
          name="valor"
          value={valor}
          onChange={(ev) => setValor(ev.target.value)}
          placeholder="8000.00"
          inputMode="decimal"
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
