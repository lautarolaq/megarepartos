import { AuthCallbackPage } from "@/pages/AuthCallback";
import { ClientesPage } from "@/pages/Clientes";
import { DashboardIndex, DashboardLayout } from "@/pages/Dashboard";
import { LoginPage } from "@/pages/Login";
import { ProductosPage } from "@/pages/Productos";
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
        <Route path="clientes" element={<ClientesPage />} />
        <Route path="envases" element={<TodoSection name="Envases" />} />
        <Route path="zonas" element={<TodoSection name="Zonas" />} />
        <Route path="usuarios" element={<TodoSection name="Usuarios" />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function TodoSection({ name }: { name: string }) {
  return (
    <div>
      <h2 className="text-2xl font-semibold tracking-tight">{name}</h2>
      <p className="mt-2 text-sm text-slate-500">
        Página en construcción. La API ya funciona en{" "}
        <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">/api/{name.toLowerCase()}</code>{" "}
        (probable desde Swagger en{" "}
        <a href="http://localhost:8000/docs" className="text-sky-600 underline">
          /docs
        </a>
        ).
      </p>
    </div>
  );
}
