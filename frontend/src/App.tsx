import { AuthCallbackPage } from "@/pages/AuthCallback";
import { ClientesPage } from "@/pages/Clientes";
import { DashboardIndex, DashboardLayout } from "@/pages/Dashboard";
import { EnvasesPage } from "@/pages/Envases";
import { LoginPage } from "@/pages/Login";
import { ProductosPage } from "@/pages/Productos";
import { UsuariosPage } from "@/pages/Usuarios";
import { ZonasPage } from "@/pages/Zonas";
import { useAuthStore } from "@/stores/auth-store";
import { Navigate, Route, Routes } from "react-router-dom";

function RootRedirect() {
  const token = useAuthStore((s) => s.accessToken);
  return <Navigate to={token ? "/dashboard" : "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route path="/dashboard" element={<DashboardLayout />}>
        <Route index element={<DashboardIndex />} />
        <Route path="productos" element={<ProductosPage />} />
        <Route path="envases" element={<EnvasesPage />} />
        <Route path="zonas" element={<ZonasPage />} />
        <Route path="clientes" element={<ClientesPage />} />
        <Route path="usuarios" element={<UsuariosPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
