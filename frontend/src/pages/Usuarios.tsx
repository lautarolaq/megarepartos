import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";

interface Usuario {
  id: string;
  email: string;
  nombre: string;
  rol: string;
  activo: boolean;
  ultima_sesion: string | null;
}

export function UsuariosPage() {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["usuarios"],
    queryFn: async (): Promise<{ items: Usuario[] }> => (await api.get("/api/usuarios")).data,
  });

  const cambiarRolMut = useMutation({
    mutationFn: async (args: { id: string; rol: "admin" | "operador" }) =>
      api.patch(`/api/usuarios/${args.id}`, { rol: args.rol }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["usuarios"] }),
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { error?: { message?: string } } } };
      alert(e.response?.data?.error?.message ?? "Error al cambiar rol.");
    },
  });

  const desactivarMut = useMutation({
    mutationFn: async (id: string) => api.delete(`/api/usuarios/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["usuarios"] }),
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { error?: { message?: string } } } };
      alert(e.response?.data?.error?.message ?? "Error al desactivar.");
    },
  });

  return (
    <div>
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold tracking-tight">Usuarios</h2>
        <p className="text-xs text-slate-400">
          La creación de usuarios pasa por login con Google. Acá solo gestionás los existentes.
        </p>
      </div>

      {isLoading && <p className="mt-4 text-slate-500">Cargando…</p>}
      {data && (
        <table className="mt-6 w-full overflow-hidden rounded-md border border-slate-200 bg-white text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Nombre</th>
              <th className="px-4 py-2">Email</th>
              <th className="px-4 py-2">Rol</th>
              <th className="px-4 py-2">Última sesión</th>
              <th className="px-4 py-2">Estado</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                  No hay usuarios todavía.
                </td>
              </tr>
            )}
            {data.items.map((u) => (
              <tr key={u.id} className="border-t border-slate-200">
                <td className="px-4 py-2 font-medium">{u.nombre}</td>
                <td className="px-4 py-2 text-slate-600">{u.email}</td>
                <td className="px-4 py-2">
                  <select
                    value={u.rol}
                    onChange={(e) =>
                      cambiarRolMut.mutate({
                        id: u.id,
                        rol: e.target.value as "admin" | "operador",
                      })
                    }
                    disabled={!u.activo}
                    className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs disabled:bg-slate-50"
                  >
                    <option value="admin">admin</option>
                    <option value="operador">operador</option>
                  </select>
                </td>
                <td className="px-4 py-2 text-slate-600">
                  {u.ultima_sesion ? new Date(u.ultima_sesion).toLocaleString("es-AR") : "—"}
                </td>
                <td className="px-4 py-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      u.activo ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {u.activo ? "Activo" : "Inactivo"}
                  </span>
                </td>
                <td className="px-4 py-2 text-right">
                  {u.activo && (
                    <Button
                      variant="ghost"
                      onClick={() => {
                        if (confirm(`¿Desactivar a ${u.nombre}?`)) desactivarMut.mutate(u.id);
                      }}
                    >
                      <Trash2 size={14} />
                    </Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
