import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

interface Empresa {
  id: string;
  nombre: string;
  tipo_negocio: string;
  estado_suscripcion: string;
  direccion_deposito: string | null;
  timezone: string;
}

type TipoNegocio = "soderia" | "garrafas" | "verduras" | "viandas" | "distribuidora" | "otro";

const TIPOS: { value: TipoNegocio; label: string }[] = [
  { value: "soderia", label: "Sodería" },
  { value: "garrafas", label: "Garrafas" },
  { value: "verduras", label: "Verdulería" },
  { value: "viandas", label: "Viandas" },
  { value: "distribuidora", label: "Distribuidora" },
  { value: "otro", label: "Otro" },
];

export function EmpresaPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["empresa-me"],
    queryFn: async (): Promise<Empresa> => (await api.get("/api/empresa/me")).data,
  });

  const [nombre, setNombre] = useState("");
  const [tipoNegocio, setTipoNegocio] = useState<TipoNegocio>("soderia");
  const [direccion, setDireccion] = useState("");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (data) {
      setNombre(data.nombre);
      setTipoNegocio((data.tipo_negocio as TipoNegocio) ?? "otro");
      setDireccion(data.direccion_deposito ?? "");
    }
  }, [data]);

  const guardar = useMutation({
    mutationFn: async () =>
      api.patch("/api/empresa/me", {
        nombre,
        tipo_negocio: tipoNegocio,
        direccion_deposito: direccion || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["empresa-me"] });
      qc.invalidateQueries({ queryKey: ["me"] });
      setSaved(true);
      setError(null);
      setTimeout(() => setSaved(false), 2500);
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { error?: { message?: string } } } };
      setError(e.response?.data?.error?.message ?? "Error al guardar.");
    },
  });

  if (isLoading) return <p className="text-slate-500">Cargando…</p>;

  return (
    <div className="max-w-xl">
      <h2 className="text-2xl font-semibold tracking-tight">Empresa</h2>
      <p className="mt-1 text-sm text-slate-500">
        Estos datos aparecen en el link que reciben tus clientes.
      </p>

      <div className="mt-6 flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <Input
          label="Nombre"
          name="nombre"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
        />
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Tipo de negocio</span>
          <select
            value={tipoNegocio}
            onChange={(e) => setTipoNegocio(e.target.value as TipoNegocio)}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          >
            {TIPOS.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
        <Input
          label="Dirección del depósito (opcional)"
          name="direccion"
          value={direccion}
          onChange={(e) => setDireccion(e.target.value)}
          placeholder="Av. Colón 123"
        />

        {data && (
          <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500">
            <span>
              <strong>Suscripción:</strong> {data.estado_suscripcion}
            </span>
            <span>
              <strong>Zona horaria:</strong> {data.timezone}
            </span>
          </div>
        )}

        {error && <p className="text-sm text-rose-600">{error}</p>}
        {saved && <p className="text-sm text-emerald-700">Cambios guardados.</p>}

        <div className="mt-2 flex justify-end">
          <Button onClick={() => guardar.mutate()} disabled={!nombre.trim() || guardar.isPending}>
            {guardar.isPending ? "Guardando…" : "Guardar"}
          </Button>
        </div>
      </div>
    </div>
  );
}
