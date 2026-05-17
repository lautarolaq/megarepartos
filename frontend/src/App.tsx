import { AuthCallbackPage } from "@/pages/AuthCallback";
import { ClientesPage } from "@/pages/Clientes";
import { DashboardIndex, DashboardLayout } from "@/pages/Dashboard";
import { EmpresaPage } from "@/pages/Empresa";
import { EnvasesPage } from "@/pages/Envases";
import { LoginPage } from "@/pages/Login";
import { PedidosPage } from "@/pages/Pedidos";
import { PendientesPage } from "@/pages/Pendientes";
import { ProductosPage } from "@/pages/Productos";
import { PublicoLinkPage } from "@/pages/PublicoLink";
import { UsuariosPage } from "@/pages/Usuarios";
import { ZonasPage } from "@/pages/Zonas";
import { useAuthStore } from "@/stores/auth-store";
import { Navigate, Route, Routes } from "react-router-dom";

function RootRedirect() {
  const token = useAuthStore((s) => s.accessToken);
  return <Navigate to={token ? "/dashboard" : "/login"} replace />;
}

function Splash() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-500">
      <p>Cargando…</p>
    </main>
  );
}

export default function App() {
  const bootChecked = useAuthStore((s) => s.bootChecked);
  if (!bootChecked) return <Splash />;

  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route path="/c/:token" element={<PublicoLinkPage />} />
      <Route path="/dashboard" element={<DashboardLayout />}>
        <Route index element={<DashboardIndex />} />
        <Route path="pedidos" element={<PedidosPage />} />
        <Route path="pendientes" element={<PendientesPage />} />
        <Route path="productos" element={<ProductosPage />} />
        <Route path="envases" element={<EnvasesPage />} />
        <Route path="zonas" element={<ZonasPage />} />
        <Route path="clientes" element={<ClientesPage />} />
        <Route path="usuarios" element={<UsuariosPage />} />
        <Route path="empresa" element={<EmpresaPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
