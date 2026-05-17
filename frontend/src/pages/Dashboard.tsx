import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { useQuery } from "@tanstack/react-query";
import { Inbox, LogOut, Package, Truck, User, Users, Warehouse } from "lucide-react";
import { NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";

interface MeResponse {
  usuario: { id: string; email: string; nombre: string; rol: string };
  empresa: { id: string; nombre: string; tipo_negocio: string; estado_suscripcion: string };
}

export function DashboardLayout() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const clear = useAuthStore((s) => s.clear);
  const navigate = useNavigate();

  const { data: me, isLoading } = useQuery({
    queryKey: ["me"],
    queryFn: async (): Promise<MeResponse> => (await api.get("/api/auth/me")).data,
    enabled: !!accessToken,
    retry: false,
  });

  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }

  async function handleLogout() {
    try {
      await api.post("/api/auth/logout");
    } catch {
      // Igual limpiamos local.
    }
    clear();
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-800">
      <aside className="w-64 border-r border-slate-200 bg-white p-4">
        <h1 className="text-xl font-semibold tracking-tight">Megarepartos</h1>
        {me && (
          <p className="mt-1 truncate text-xs text-slate-500" title={me.empresa.nombre}>
            {me.empresa.nombre}
          </p>
        )}
        <nav className="mt-6 flex flex-col gap-1">
          <NavItem to="/dashboard/pedidos" icon={<Inbox size={16} />}>
            Pedidos
          </NavItem>
          <NavItem to="/dashboard/productos" icon={<Package size={16} />}>
            Productos
          </NavItem>
          <NavItem to="/dashboard/envases" icon={<Warehouse size={16} />}>
            Envases
          </NavItem>
          <NavItem to="/dashboard/zonas" icon={<Truck size={16} />}>
            Zonas
          </NavItem>
          <NavItem to="/dashboard/clientes" icon={<Users size={16} />}>
            Clientes
          </NavItem>
          <NavItem to="/dashboard/usuarios" icon={<User size={16} />}>
            Usuarios
          </NavItem>
        </nav>
        <div className="mt-8 border-t border-slate-200 pt-4">
          {me && (
            <p className="mb-2 text-xs text-slate-500">
              {me.usuario.nombre}
              <br />
              <span className="text-slate-400">{me.usuario.rol}</span>
            </p>
          )}
          <Button variant="ghost" onClick={handleLogout} className="w-full">
            <LogOut size={14} />
            Cerrar sesión
          </Button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-8">
        {isLoading ? <p className="text-slate-500">Cargando…</p> : <Outlet />}
      </main>
    </div>
  );
}

function NavItem({
  to,
  icon,
  children,
}: {
  to: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
          isActive ? "bg-sky-50 text-sky-700 font-medium" : "text-slate-600 hover:bg-slate-100"
        }`
      }
    >
      {icon}
      {children}
    </NavLink>
  );
}

export function DashboardIndex() {
  return (
    <div>
      <h2 className="text-2xl font-semibold tracking-tight">Bienvenido</h2>
      <p className="mt-2 text-sm text-slate-500">
        Elegí una sección en el menú lateral. Productos y Clientes ya funcionan con listado y
        creación; los demás vienen pronto.
      </p>
    </div>
  );
}
