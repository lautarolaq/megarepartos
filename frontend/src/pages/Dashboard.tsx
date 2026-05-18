import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import { useQuery } from "@tanstack/react-query";
import {
  Building2,
  Check,
  Circle,
  Clock,
  Inbox,
  LogOut,
  Megaphone,
  Menu,
  Package,
  Truck,
  User,
  Users,
  X as XIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";

interface MeResponse {
  usuario: { id: string; email: string; nombre: string; rol: string };
  empresa: { id: string; nombre: string; tipo_negocio: string; estado_suscripcion: string };
}

export function DashboardLayout() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const clear = useAuthStore((s) => s.clear);
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Cerrar el drawer al navegar (en mobile).
  // biome-ignore lint/correctness/useExhaustiveDependencies: el efecto debe dispararse cuando cambia la ruta.
  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

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

  const sidebar = (
    <>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight">Megarepartos</h1>
        <button
          type="button"
          onClick={() => setSidebarOpen(false)}
          className="lg:hidden -mr-2 inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100"
          aria-label="Cerrar menú"
        >
          <XIcon size={20} />
        </button>
      </div>
      {me && (
        <p className="mt-1 truncate text-xs text-slate-500" title={me.empresa.nombre}>
          {me.empresa.nombre}
        </p>
      )}
      <nav className="mt-6 flex flex-col gap-1">
        <NavItem to="/dashboard/pedidos" icon={<Inbox size={16} />}>
          Pedidos
        </NavItem>
        <NavItem to="/dashboard/pendientes" icon={<Clock size={16} />}>
          Pendientes
        </NavItem>
        <NavItem to="/dashboard/productos" icon={<Package size={16} />}>
          Productos
        </NavItem>
        <NavItem to="/dashboard/zonas" icon={<Truck size={16} />}>
          Zonas
        </NavItem>
        <NavItem to="/dashboard/clientes" icon={<Users size={16} />}>
          Clientes
        </NavItem>
        <NavItem to="/dashboard/campanas" icon={<Megaphone size={16} />}>
          Campañas
        </NavItem>
        <NavItem to="/dashboard/usuarios" icon={<User size={16} />}>
          Usuarios
        </NavItem>
        <NavItem to="/dashboard/empresa" icon={<Building2 size={16} />}>
          Empresa
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
    </>
  );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 lg:flex">
      {/* Header mobile con hamburger */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
        <button
          type="button"
          onClick={() => setSidebarOpen(true)}
          className="-ml-2 inline-flex h-10 w-10 items-center justify-center rounded-md text-slate-700 hover:bg-slate-100"
          aria-label="Abrir menú"
        >
          <Menu size={22} />
        </button>
        <h1 className="text-lg font-semibold tracking-tight">Megarepartos</h1>
        <div className="w-10" />
      </header>

      {/* Sidebar desktop */}
      <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-white p-4 lg:block">
        {sidebar}
      </aside>

      {/* Drawer mobile */}
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Cerrar menú"
          className="fixed inset-0 z-40 bg-slate-900/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-72 max-w-[85vw] border-r border-slate-200 bg-white p-4 shadow-xl transition-transform lg:hidden ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {sidebar}
      </aside>

      <main className="flex-1 overflow-auto p-4 sm:p-6 lg:p-8">
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

interface PedidoStats {
  pedidos_hoy: number;
  confirmados_hoy: number;
  pedidos_semana: number;
  clientes_activos: number;
}

interface ListResp<T> {
  items: T[];
  total?: number;
}

export function DashboardIndex() {
  const { data: stats } = useQuery({
    queryKey: ["pedidos-stats"],
    queryFn: async (): Promise<PedidoStats> => (await api.get("/api/pedidos/stats")).data,
    refetchInterval: 60_000,
  });

  const { data: productos } = useQuery({
    queryKey: ["productos"],
    queryFn: async (): Promise<ListResp<unknown>> => (await api.get("/api/productos")).data,
  });

  const { data: clientes } = useQuery({
    queryKey: ["clientes-count"],
    queryFn: async (): Promise<ListResp<unknown>> => (await api.get("/api/clientes?limit=1")).data,
  });

  const productosCount = productos?.items.length ?? 0;
  const clientesTotal = clientes?.total ?? clientes?.items.length ?? 0;
  const pedidosSemana = stats?.pedidos_semana ?? 0;

  const onboardingCompleto = productosCount > 0 && clientesTotal > 0 && pedidosSemana > 0;

  return (
    <div>
      <h2 className="text-2xl font-semibold tracking-tight">Resumen</h2>

      {stats && (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Pedidos hoy"
            value={stats.pedidos_hoy}
            hint={`${stats.confirmados_hoy} confirmado${stats.confirmados_hoy === 1 ? "" : "s"}`}
            tone="sky"
          />
          <StatCard
            label="Últimos 7 días"
            value={stats.pedidos_semana}
            hint="respuestas recibidas"
            tone="emerald"
          />
          <StatCard
            label="Clientes activos"
            value={stats.clientes_activos}
            hint="en tu base"
            tone="slate"
          />
          <StatCard
            label="Tasa hoy"
            value={
              stats.pedidos_hoy === 0
                ? "—"
                : `${Math.round((stats.confirmados_hoy / stats.pedidos_hoy) * 100)}%`
            }
            hint="confirmaron del total"
            tone="amber"
          />
        </div>
      )}

      {!onboardingCompleto && (
        <Onboarding
          tieneProductos={productosCount > 0}
          tieneClientes={clientesTotal > 0}
          tienePedidos={pedidosSemana > 0}
        />
      )}

      {onboardingCompleto && (
        <p className="mt-8 text-sm text-slate-500">
          Mandá links a tus clientes desde <strong>Clientes</strong>, las respuestas aparecen en{" "}
          <strong>Pedidos</strong>.
        </p>
      )}
    </div>
  );
}

function Onboarding({
  tieneProductos,
  tieneClientes,
  tienePedidos,
}: {
  tieneProductos: boolean;
  tieneClientes: boolean;
  tienePedidos: boolean;
}) {
  const steps = [
    {
      done: tieneProductos,
      label: "Cargá los productos que vendés",
      hint: "Bidón 20L, Soda 1.5L, etc. — los que el cliente puede pedir.",
      cta: "Ir a Productos",
      to: "/dashboard/productos",
    },
    {
      done: tieneClientes,
      label: "Cargá tus clientes",
      hint: "Nombre, teléfono y zona. Podés asignar productos habituales.",
      cta: "Ir a Clientes",
      to: "/dashboard/clientes",
    },
    {
      done: tienePedidos,
      label: "Mandá tu primer link",
      hint: "Desde el listado de clientes, ícono de link → abre WhatsApp con el mensaje listo.",
      cta: "Ir a Clientes",
      to: "/dashboard/clientes",
    },
  ];

  return (
    <div className="mt-8 rounded-xl border border-sky-200 bg-sky-50 p-5">
      <h3 className="font-semibold text-sky-900">Para empezar</h3>
      <p className="mt-1 text-sm text-sky-700">
        Una vez que tengas estas tres cosas, esta caja desaparece y el dashboard pasa a modo
        operativo.
      </p>
      <ol className="mt-4 flex flex-col gap-3">
        {steps.map((step, i) => (
          <li
            key={step.label}
            className={`flex items-start gap-3 rounded-lg border bg-white p-3 ${
              step.done ? "border-emerald-200" : "border-slate-200"
            }`}
          >
            <span
              className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
                step.done ? "bg-emerald-500 text-white" : "bg-slate-100 text-slate-500"
              }`}
            >
              {step.done ? <Check size={14} /> : <Circle size={10} fill="currentColor" />}
            </span>
            <div className="flex-1">
              <p
                className={`text-sm font-medium ${
                  step.done ? "text-slate-500 line-through" : "text-slate-800"
                }`}
              >
                {i + 1}. {step.label}
              </p>
              <p className="mt-0.5 text-xs text-slate-500">{step.hint}</p>
            </div>
            {!step.done && (
              <Link
                to={step.to}
                className="rounded-md bg-sky-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-700"
              >
                {step.cta}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

function StatCard({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: number | string;
  hint: string;
  tone: "sky" | "emerald" | "slate" | "amber";
}) {
  const toneClasses: Record<typeof tone, string> = {
    sky: "border-sky-200 bg-sky-50 text-sky-700",
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-700",
    slate: "border-slate-200 bg-white text-slate-700",
    amber: "border-amber-200 bg-amber-50 text-amber-700",
  };
  return (
    <div className={`rounded-xl border p-4 shadow-sm ${toneClasses[tone]}`}>
      <p className="text-xs uppercase tracking-wider opacity-80">{label}</p>
      <p className="mt-1 text-3xl font-semibold">{value}</p>
      <p className="mt-1 text-xs opacity-70">{hint}</p>
    </div>
  );
}
